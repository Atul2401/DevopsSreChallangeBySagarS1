#!/bin/bash

EMAIL="abcdedhfhh.ijk@example-email.com"
DEBUG=0

log(){ echo "$(date '+%F %T') $*"; }
dbg(){ [ "$DEBUG" -eq 1 ] && log "DEBUG: $*"; }

disk(){ log "Disk Usage"; df -h; }
mem(){ log "Memory Usage"; free -h; }
cpu(){ log "CPU Usage"; top -bn1 | head -20; }
svc(){ log "Running Services"; systemctl list-units --type=service --state=running --no-pager | head -20; }

report(){
  echo "Health Report - $(date)"
  disk; mem; cpu; svc
}

send_report(){
  report | mail -s "System Health Report" "$EMAIL"
  log "Report sent to $EMAIL"
}

start_reporter(){
  while true; do send_report; sleep 14400; done &
  echo $!
  log "Reporter started PID $!"
}

stop_reporter(){
  pkill -f "mail -s System Health Report"
  log "Reporter stopped"
}

menu(){
cat <<EOF
1) Disk
2) Memory
3) CPU
4) Services
5) Send report now
6) Start 4h reporter
7) Stop reporter
0) Exit
EOF
}

while true; do
  menu
  read -p "Choice: " c
  case $c in
    1) disk;;
    2) mem;;
    3) cpu;;
    4) svc;;
    5) send_report;;
    6) start_reporter;;
    7) stop_reporter;;
    0) exit;;
    *) echo "Invalid";;
  esac
done
