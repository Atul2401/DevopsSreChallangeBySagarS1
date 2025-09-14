#!/usr/bin/env python3
"""Compact S3 bucket audit -> single report.txt"""
import argparse, json, re
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# thresholds
TH_LARGE = 80
TH_UNUSED_90 = 90
CLEANUP_GB = 50
DEL_SIZE_GB = 100
DEL_UNUSED_DAYS = 20
RATE_PER_GB = 0.023

# optional date parser (dateutil if available)
try:
    from dateutil import parser as _dp
    def parse_date(s):
        return None if s in (None, "") else _dp.parse(s)
except Exception:
    def parse_date(s):
        if not s: return None
        try:
            return datetime.fromisoformat(s)
        except Exception:
            try: return datetime.utcfromtimestamp(int(s))
            except Exception: return None

def days_since(dt, now): return None if dt is None else (now - dt).days

def numify_size(v):
    if v is None: return 0.0
    if isinstance(v, (int, float)): return float(v)
    s = str(v).replace(",", "")
    m = re.search(r"-?\d+(\.\d+)?", s)
    return float(m.group(0)) if m else 0.0

def normalize(o):
    name = o.get("name") or o.get("bucket_name") or o.get("id") or "<unknown>"
    region = o.get("region") or "unknown"
    size = numify_size(o.get("size_gb") or o.get("size") or 0)
    versioning = bool(o.get("versioning") or o.get("version_enabled") or False)
    last_raw = o.get("last_accessed") or o.get("last_modified") or o.get("last_access")
    last = parse_date(last_raw)
    dept = o.get("department") or o.get("team") or "unknown"
    cost = o.get("monthly_cost")
    return {"name":name, "region":region, "size_gb":size, "versioning":versioning,
            "last":last, "last_raw": last_raw or "", "dept":dept, "monthly_cost":cost}

def write_report(path, now, results):
    with open(path,"w") as f:
        f.write(f"Comprehensive S3 Bucket Audit - {now.isoformat()}\n")
        f.write("="*80+"\n\n")
        f.write("SUMMARY (name | region | size(GB) | versioning | dept | last_accessed)\n")
        for s in results["summary"]:
            f.write(f"{s['name']} | {s['region']} | {s['size_gb']} GB | {s['versioning']} | {s['department']} | {s['last_accessed']}\n")
        f.write("\nBUCKETS > %dGB AND UNUSED >= %d days\n" % (TH_LARGE, TH_UNUSED_90))
        if results["large_unused_90plus"]:
            for r in results["large_unused_90plus"]:
                f.write(f"{r['name']} | {r['region']} | {r['size_gb']} GB | last={r['last_accessed']} | unused_days={r['unused_days']}\n")
        else:
            f.write("None\n")
        f.write("\nCOST BY REGION\n")
        for r in results["cost_by_region"]:
            f.write(f"{r['region']} : ${r['total_monthly_cost_usd']}\n")
        f.write("\nCOST BY REGION+DEPARTMENT\n")
        for r in results["cost_by_region_department"]:
            f.write(f"{r['region']}/{r['department']} : ${r['total_monthly_cost_usd']}\n")
        f.write("\nCLEANUP RECOMMENDATIONS (size>%d GB)\n" % CLEANUP_GB)
        for r in results["cleanup_recommendations"]:
            f.write(f"{r['name']} | {r['region']} | {r['size_gb']} GB | reason: {r['reason']}\n")
        f.write("\nDELETION QUEUE (size>%d & unused>=%d days)\n" % (DEL_SIZE_GB, DEL_UNUSED_DAYS))
        for r in results["deletion_queue"]:
            f.write(f"{r['name']} | {r['region']} | {r['size_gb']} GB | unused_days={r['unused_days']} | monthly_cost=${r['monthly_cost']}\n")
        f.write("\nARCHIVAL SUGGESTIONS (Move to Glacier)\n")
        for r in results["archival_suggestions"]:
            f.write(f"{r['name']} | {r['region']} | {r['size_gb']} GB | {r['suggestion']}\n")
        f.write("\nFINAL DELETION LIST\n")
        for r in results["final_deletion_list"]:
            f.write(f"{r['name']} | {r['region']} | {r['size_gb']} GB\n")

def process(buckets, rate=RATE_PER_GB, now=None):
    now = now or datetime.utcnow()
    norm = [normalize(b) for b in buckets]
    for n in norm:
        if n["monthly_cost"] is None:
            n["monthly_cost"] = round(n["size_gb"] * rate, 4)

    summary = [{"name":n["name"], "region":n["region"], "size_gb":n["size_gb"],
                "versioning":n["versioning"], "last_accessed":n["last_raw"], "department":n["dept"]} for n in norm]

    large_unused = []
    for n in norm:
        d = days_since(n["last"], now)
        if n["size_gb"]>TH_LARGE and (d is None or d>=TH_UNUSED_90):
            large_unused.append({"name":n["name"], "region":n["region"], "size_gb":n["size_gb"], "last_accessed":n["last_raw"], "unused_days": "" if d is None else d})

    cost_region = defaultdict(float); cost_region_dept = defaultdict(float)
    for n in norm:
        cost_region[n["region"]] += n["monthly_cost"]
        cost_region_dept[(n["region"], n["dept"])] += n["monthly_cost"]
    cost_rows = [{"region":r, "total_monthly_cost_usd":round(c,4)} for r,c in cost_region.items()]
    cost_rows_rd = [{"region":r, "department":d, "total_monthly_cost_usd":round(c,4)} for (r,d),c in cost_region_dept.items()]

    cleanup=[]; deletion=[]; archival=[]
    for n in norm:
        d = days_since(n["last"], now)
        if n["size_gb"]>CLEANUP_GB:
            cleanup.append({"name":n["name"], "region":n["region"], "size_gb":n["size_gb"], "reason":f"size>{CLEANUP_GB}"})
        if n["size_gb"]>DEL_SIZE_GB and (d is None or d>=DEL_UNUSED_DAYS):
            deletion.append({"name":n["name"], "region":n["region"], "size_gb":n["size_gb"], "unused_days":"" if d is None else d, "monthly_cost":n["monthly_cost"]})
        if n["size_gb"]>CLEANUP_GB and (d is None or d>=TH_UNUSED_90) and n["name"] not in [x["name"] for x in deletion]:
            archival.append({"name":n["name"], "region":n["region"], "size_gb":n["size_gb"], "suggestion":"Move to Glacier"})

    results = {
        "summary": summary,
        "large_unused_90plus": large_unused,
        "cost_by_region": cost_rows,
        "cost_by_region_department": cost_rows_rd,
        "cleanup_recommendations": cleanup,
        "deletion_queue": deletion,
        "archival_suggestions": archival,
        "final_deletion_list": deletion.copy()
    }
    write_report("report.txt", now, results)
    return results

def main():
    parser = argparse.ArgumentParser(description="Compact S3 audit")
    # accepts --file / -f
    parser.add_argument("--file","-f", required=True, help="buckets JSON file")
    parser.add_argument("--rate","-r", type=float, default=RATE_PER_GB, help="USD per GB-month")
    args = parser.parse_args()
    p = Path(args.file)
    if not p.exists():
        print("File not found:", args.file); return
    data = json.load(p.open())
    if isinstance(data, dict) and "buckets" in data: data = data["buckets"]
    results = process(data, rate=args.rate, now=datetime.utcnow())
    print("Processed:", len(results["summary"]))
    print("Large & unused(90d):", len(results["large_unused_90plus"]))
    print("Deletion queue:", len(results["deletion_queue"]))
    print("Report -> report.txt")

if __name__=="__main__":
    main()
