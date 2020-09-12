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

YEAR=2018
PYTHON=/usr/bin/python3
APP=/home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/secondanalysis.py
NOTE=/home/leon/Cloud/Software/MagPyAnalysis/OneSecondAnalysis/telegramnote.py

source /home/leon/ginsource.sh

MOUNTMIN=/mnt/minute
MOUNTSEC=/mnt/second

DESTINATION="/media/leon/Images/DataCheck/IMBOT/${YEAR}"
TMPDIR="/media/leon/Images/DataCheck/tmp/${YEAR}"
MEMORY="/media/leon/Images/DataCheck/analysis${YEAR}.json"
SOURCEDIR="${MOUNTSEC}/${YEAR}_step1"
MINDIR="${MOUNTMIN}/Mag${YEAR}"

mkdir -p $MOUNTMIN
mkdir -p $MOUNTSEC

# MOUNT ONE SECOND DATA (# eventually add -o allow_others)
curlftpfs -o user=$GINSEC $GINIP $MOUNTSEC
# MOUNT ONE MINUTE DATA
curlftpfs -o user=$GINMIN $GINIP $MOUNTMIN


if grep -qs "$MOUNTSEC" /proc/mounts; then
  MSG="GIN directories mounted."
  echo $MSG
  # Please uncomment using # if you are not using Telegram notifications
  $PYTHON $NOTE -t /etc/martas/telegram.cfg -n "${MSG}" -l "IMBOTmaster"
  # ANALYSE
  $PYTHON $APP -s $SOURCEDIR -d $DESTINATION -t $TMPDIR -i $MINDIR -m $MEMORY -n /etc/martas/telegram.cfg
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


