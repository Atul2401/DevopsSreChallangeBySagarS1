#Requirements:
---------------------------------------------
Service Setup: 

Install and run Grafana and Jenkins locally or via Docker.

Nginx Reverse Proxy:

Configure Nginx to route requests:

https://grafana.local → Grafana
https://jenkins.local → Jenkins (with Basic Authentication).
Enable SSL:

Generate and configure a self-signed SSL certificate for HTTPS access.

Redirect all HTTP traffic to HTTPS.

Secure Jenkins:

Restrict Jenkins/Grafana access with Basic Authentication.

Validate Configuration: 

Access both services via the configured domains securely using HTTPS.



Why This Matters:
Reverse proxies are a cornerstone of cloud-native architectures, enabling secure service exposure, load balancing, and high availability. This challenge prepares you to handle real-world scenarios where Nginx is critical.



Submission Guidelines:
1. GitHub Repository: Upload your Nginx configuration, Grafana and Jenkins setup steps, and screenshots of task completion.

2. Documentation: Include a README.md explaining your approach, challenges faced, and key learnings.

3. Share Your Progress: Post your experience with hashtags: #getfitwithsagar, #SRELife, #DevOpsForAll



Bonus Tasks:

Restrict Access to Jenkins by IP:

Use Nginx’s allow and deny directives to restrict access to Jenkins from a specific IP range (e.g., your office/home IP).
Only allow access from your designated IP range and deny others.
Implement Rate Limiting in Nginx:
Set up Nginx rate limiting to prevent abuse by restricting the number of requests per second from each IP address.
Ensure that rate limits are applied for access to Jenkins.
Configure Subdomains:
Configure Nginx to use subdomains (grafana.local and jenkins.local) instead of path-based routing.
Automate Setup with  Shell Scripts:
Write a shell script that automates the entire process:
Install and configure Grafana and Jenkins.
Set up Nginx reverse proxy.
Create and install SSL certificates.
Configure Basic Authentication for Jenkins.
The script should handle all the steps required to set up the environment from scratch.
---------------------------------------

install nginx 
breinstall nginx
-----------------
run jenkins container  -p 8080
----------
run garfana conatiner  -p 3000
---------------
access locally -p 3000 was accesible 
userid :admin
pass:admin
---------------
unable to access jenkins on 8080 , contaier was stopped , tried running in -d mode , still not able access , so i strated from docker ui -
----------------------------
run docker exec -it jenkins cat /var/jenkins_home/secrets/initialAdminPassword 
to get initial password , installed few plungin and jenkis ui was accesible
--------------------------
now i had to start nginx , but systemctl command doesn,t work on mac (sad) , so i found launchctl , but it also did help much , then i came to know that i have installed nginx from brew so i used brew command and started nginx servuce,\

systemctl (Linux)	brew equivalent (easy)	 launchd / lower-level (macOS)
systemctl status svc	`brew services list 	grep svc`
systemctl start svc	brew services start svc 	launchctl bootstrap ...
systemctl stop svc	brew services stop svc	       launchctl bootout ...
systemctl restart svc	brew services restart svc	launchctl kickstart -k <label>
systemctl enable svc	brew services start svc (registers plist)\	use bootstrap to register
systemctl disable svc	brew services stop svc (and remove plist)\	bootout to unload
-----------------------------------
but again nginx was not starting 
i did  brew services start nginx

and then
brew services list
and it was showing statas in error , so after a bit of troubleshooting ( lsof -nP -iTCP:8080 -sTCP:LISTEN
COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
com.docke 48265 attu  162u  IPv6 0x73bf889105b7f2c0      0t0  TCP *:8080 (LISTEN))  
i came to use i can not access it on port 8080 right , because that is already being used by jenkisn, so i modified a file using "nano /opt/homebrew/etc/nginx/nginx.conf" and under server{....} i modified port to 8081
--------------------------