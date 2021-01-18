#!/bin/bash
PYTHON=/usr/bin/python3
TELEGRAM=/home/pi/Software/IMBOT/imbot/telegramnote.py

cd /home/pi/Software/IMBOT/imbot

echo "CHECKING LOGFILES"
thefirstinfo=$(grep -rnw '/home/pi/IMBOT/' -e 'SUCCESSFULLY' | awk -F: '{print $1}' | awk -F/ '{print $NF}' | grep '2018')
echo "logfile contains " $thefirstinfo
if [ -z "$thefirstinfo" ]
then
      VAL="FAILED"
else
      VAL="SUCCESS"
fi
$PYTHON $TELEGRAM -t /etc/martas/telegram.cfg -l imbotlogfile -p /var/log/magpy/imbot_status1.log -n $VAL

thesecondinfo=$(grep -rnw '/home/pi/IMBOT/' -e 'SUCCESSFULLY' | awk -F: '{print $1}' | awk -F/ '{print $NF}' | grep '2019')
if [ -z "$thesecondinfo" ]
then
      SVAL="FAILED"
else
      SVAL="SUCCESS"
fi
echo "logfile contains " $thesecondinfo
$PYTHON $TELEGRAM -t /etc/martas/telegram.cfg -l imbot2019logfile -p /var/log/magpy/imbot_status2.log -n $SVAL
