#!/bin/bash
PYTHON=/usr/bin/python3
TELEGRAM=/home/pi/Software/IMBOT/imbot/telegramnote.py

cd /home/pi/Software/IMBOT/imbot

echo "Testing disk size"
theinfo=$(df /dev/sda2 | grep sda2 | tr -s ' '| cut -d ' ' -f 5)
echo "used space of sda2:" $theinfo
$PYTHON $TELEGRAM -t /etc/martas/telegram.cfg -n $theinfo -l imbotdiskusage -p /var/log/magpy/imbot_status3.log

theotherinfo=$(df / | grep root | tr -s ' '| cut -d ' ' -f 5)
echo "used space of root:" $theotherinfo
$PYTHON $TELEGRAM -t /etc/martas/telegram.cfg -n $theotherinfo -l imbotrootusage -p /var/log/magpy/imbot_status4.log
