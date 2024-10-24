#!/usr/bin/bash
# Some basic monitoring functionality; Tested on Amazon Linux 2023.
#

TOKEN=`curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600"`
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
MEMORYUSAGE=$(free -m | awk 'NR==2{printf "%.2f%%", $3*100/$2 }')
PROCESSES=$(expr $(ps -A | grep -c .) - 1)
UPTIME=$(uptime -p)
DISK_USAGE=$(df -P -h -x tmpfs | awk 'NR>1 {print "Filesystem:", $1, "| Used:", $3, "| Usage:", $5}')
HTTP_CONNECTIONS=$(expr $(netstat -a | grep -c 'http.*ESTABLISHED'))
HTTPD_PROCESSES=$(ps -A | grep -c httpd)

echo "Instance ID: $INSTANCE_ID"
echo "--------"
echo "Memory utilisation: $MEMORYUSAGE"
echo "--------"
echo "No of processes: $PROCESSES"
echo "--------"
echo "Server uptime: $UPTIME"
echo "--------"
echo "Disk usage:"
echo "$DISK_USAGE"
echo "--------"
if [ "$HTTP_CONNECTIONS" -ge 1 ]
then
    echo "Active HTTP connections: $HTTP_CONNECTIONS"
else
    echo "No active HTTP connections"
fi
echo "--------"
if [ "$HTTPD_PROCESSES" -ge 1 ]
then
    echo "Web server is running"
else
    echo "Web server is NOT running"
fi
