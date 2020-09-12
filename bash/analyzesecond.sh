#!/bin/bash

# DESCRIPTION
# -----------
# Basic bash script to mount Ftp directories locally, perform analysis and unmount afterwards.
# This bash script call the python application 'onesceondanalysis.py' using python3.
# If you are running this job as user please make sure to create the directories
# minute, second and to assign the user as owner
# GIN connection details are stored in a separate file called ginsource.sh (see below).
# Please change the rights on ginsource for some minimal protection: chmod 600 ginsource.sh
#
# PARAMETER and PREREQUISITES
# ---------------------------
# A basic prerequisite is python3 and the magpy package (>=0.9.7). Further recommended packages are 
# telegram_send (for notifications), ...
# You need to specify the following parameters
#  TMPDIR:      a local folder with at least 4 GB memory
#  DESTINATION: a local/remote folder to save the results to; within this folder, a subdir 'level' will be created.
#               Within the directory 'level', subdirectories for each Observatory will be established.
#               A large disk space is required here, suggested is > 1TB.
#  MEMORY:      a full path to a local file, which contains the memory of all performed analyses. Please make sure,
#              that this file is secure and accessible. Dont use a temporary folder.
# 
#  Please make sure that all directories are existing and that the projected user has access
#  Add something like the following to systemwide /etc/crontab:
#  15 0   *  *  *  root bash /home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/analyzesecond2018.sh > /home/user/last_sec_analysis2018.log 
#  15 12  *  *  *  root bash /home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/analyzesecond2018.sh > /home/user/last_sec_analysis2018.log 
#  15 4   *  *  *  root bash /home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/analyzesecond2019.sh > /home/user/last_sec_analysis2019.log 
#  15 16  *  *  *  root bash /home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/analyzesecond2019.sh > /home/user/last_sec_analysis2019.log 
#
# 
# APPLICATION
# -----------
# Use a separate analysis script for each year. The analysis script should be scheduled to be run at least 
# once every day. The analysis of a single new one-second submission might need approximately one hour.
# Therefore, an execution of this script more often than every three hours is not advisable, if institutes upload 
# several data sets of multiple observatories at once. 
#
# MONITORING
# -----------
# The script makes use of a small python application which allows for sending telegram notifications based on
# MARTAS () logging method, i.e. whenever a state is changing. You can also pipe the output of the script into a log 
# file and use other monitoring methods like Nagios etc for checking the run time state of the bash script.
#
# ginsource.sh:
# GINIP=194.254.225.100
# GINMIN='ftp-user:ftp-passwd'
# GINSEC='ftp-user:ftp-passwd'

YEAR=2019

#QUIETDAYLIST='2016-01-25,2016-01-29,2016-02-22,2016-03-13,2016-04-01,2016-08-28,2016-10-21,2016-11-05,2016-11-17,2016-11-19,2016-11-30,2016-12-01,2016-12-03,2016-12-04'
#QUIETDAYLIST='2017-01-16,2017-02-14,2017-02-26,2017-03-19,2017-03-20,2017-07-31,2017-10-30,2017-11-06,2017-12-03,2017-12-21,2017-12-22'
#QUIETDAYLIST='2018-01-03,2018-01-06,2018-01-07,2018-01-11,2018-01-18,2018-02-11,2018-02-14,2018-04-16,2018-05-21,2018-09-20,2018-10-17,2018-10-18,2018-10-19,2018-10-20,2018-10-29,2018-11-17,2018-11-18,2018-11-22,2018-11-26,2018-11-28,2018-12-13,2018-12-14,2018-12-15,2018-12-16,2018-12-22,2018-12-23'
QUIETDAYLIST='2019-01-02,2019-01-12,2019-01-13,2019-01-28,2019-01-29,2019-01-30,2019-02-19,2019-03-11,2019-03-22,2019-03-23,2019-03-24,2019-06-11,2019-10-13,2019-10-23,2019-11-02,2019-11-18,2019-11-19,2019-11-20,2019-11-26,2019-12-02,2019-12-03,2019-12-05,2019-12-07,2019-12-08,2019-12-14,2019-12-24,2019-12-27,2019-12-28,2019-12-29'

PYTHON=/usr/bin/python3
APP=/home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/secondanalysis.py
NOTE=/home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/telegramnote.py

source /home/leon/ginsource.sh

MOUNTMIN=/mnt/minute
MOUNTSEC=/mnt/second

DESTINATION="/media/leon/Images/DataCheck/IMBOT/${YEAR}"
TMPDIR="/media/leon/Images/DataCheck/tmp/${YEAR}"
MEMORY="/media/leon/Images/DataCheck/analysis${year}.json"
SOURCEDIR="${MOUNTSEC}/${YEAR}_step1"
MINDIR="${MOUNTMIN}/Mag${YEAR}"

mkdir -p $MOUNTMIN
mkdir -p $MOUNTSEC

# MOUNT ONE SECOND DATA (# eventually add ,allow_others)
curlftpfs -o user=$GINSEC $GINIP $MOUNTSEC
# MOUNT ONE MINUTE DATA
curlftpfs -o user=$GINMIN $GINIP $MOUNTMIN


if grep -qs "$MOUNTSEC" /proc/mounts; then
  MSG="GIN directories mounted."
  echo $MSG
  # Please uncomment using # if you are not using Telegram notifications
  $PYTHON $NOTE -t /etc/martas/telegram.cfg -n "${MSG}" -l "IMBOTmaster"
  # ANALYSE
  $PYTHON $APP -s $SOURCEDIR -d $DESTINATION -t $TMPDIR -i $MINDIR -m $MEMORY -n /etc/martas/telegram.cfg -q $QUIETDAYLIST
  echo "Analysis performed"
  # UMOUNT DIRECTORIES
  umount $MOUNTMIN
  umount $MOUNTSEC
  echo "GIN unmounted"
else
  MSG="GIN directories could not be mounted."
  echo $MSG
  # Please uncomment using # if you are not using Telegram notifications
  $PYTHON $NOTE -t /etc/martas/telegram.cfg -n "${MSG}" -l "IMBOTmaster"
fi


