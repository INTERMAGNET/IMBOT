#!/bin/bash
PYTHON=/usr/bin/python3
TELEGRAM=/home/leon/Software/IMBOT/imbot/telegramnote.py

cd /home/leon/Software/IMBOT/imbot

echo "CHECKING LOGFILES"
theinfo=$(grep -rnw '/home/leon/IMBOT/' -e 'SUCCESSFULLY' | awk -F: '{print $1}' | awk -F/ '{print $NF}' | grep 'last')
echo "logfile contains " $theinfo
$PYTHON $TELEGRAM -t /etc/martas/telegram.cfg -n $theinfo -l IMBOTlogfile -p /var/log/magpy/imbot_status1.log
