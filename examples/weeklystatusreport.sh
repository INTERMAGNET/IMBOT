#!/bin/bash
PYTHON=/usr/bin/python3
TELEGRAM=/home/leon/Software/IMBOT/imbot/telegramnote.py

cd /home/leon/Software/IMBOT/imbot

echo "Testing disk size"
theinfo=$(df /dev/sda1 | grep sda1 | tr -s ' '| cut -d ' ' -f 5)
echo "used space of sda1:" $theinfo
$PYTHON $TELEGRAM -t /etc/martas/telegram.cfg -n $theinfo -l imbotdiskusage -p /var/log/magpy/imbot_status2.log
