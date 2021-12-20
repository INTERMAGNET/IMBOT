#!/bin/bash

# DESCRIPTION
# -----------
# Basic bash script to mount Ftp directories locally, perform analysis and unmount afterwards.
# This bash script call the python application 'minuteanalysis.py' using python3.
# If you are running this job as user please make sure to create the directories
# minute and to assign the user as owner
# GIN connection details are stored in a separate file called ginsource.sh (see below).
# Please change the rights on ginsource for some minimal protection: chmod 600 ginsource.sh
#
# PARAMETER and PREREQUISITES
# ---------------------------
# A basic prerequisite is python3 and the magpy package (>=0.9.7). Further recommended packages are 
# telegram_send (for notifications), ...
# You need to specify the following parameters
#  TMPDIR:      a local folder with at least 200MB memory
#  DESTINATION: a local/remote folder to save the results to; within this folder, a subdir 'minute' will be created.
#  MEMORY:      a full path to a local file, which contains the memory of all performed analyses. Please make sure,
#              that this file is secure and accessible. Dont use a temporary folder.
#
# APPLICATION
# -----------
# Use a separate analysis script for each year. The analysis script should be scheduled to be run at least 
# once every day. The analysis (particularly the checking of all mounted directories currently needs up to two hours (TODO).
# Therefore, an execution of this script more often than every three hours is not advisable, if institutes upload 
# several data sets of multiple observatories at once.
#
# MONITORING
# -----------
# The script makes use of a small python application which allows for sending telegram notifications based on
# MARTAS (https://github.com/geomagpy/martas.git) logging method, i.e. whenever a state is changing. You can also pipe the output of the script into a log 
# file and use other monitoring methods like Nagios etc for checking the run time state of the bash script.
#
# ginsource.sh:
# GINIP=xxx.xxx.xxx.xxx
# GINMINSTEP1='ftp-user:ftp-passwd'
# GINMINSTEP2='ftp-user:ftp-passwd'
# GINSECSTEP1='ftp-user:ftp-passwd'


## ##########################################
##   Basic  configuration
## ##########################################

YEAR=2021

## OBSTESTLIST: If provided then full reporting is limited to these
##              observatories. For all other observatories reports
##              will be send to IMBOT manager only.
##              Enter "None" for productive runs i.e. if you don't want to use it.
OBSTESTLIST="WIC"

## CHECK1MINVERSION: current check1min.exe version.
CHECK1MINVERSION="171"

## OBSLIST: IF only specific OBS shoud be analyzed then provide them here.
##          If REFEREE is contained, then all observatories listed in
##          refereelist_minute.cfg are used.
##          (plus the ones provided here along with REFEREE)
OBSLIST='REFEREE,WIC'


## ##########################################
##   Path definitions
## ##########################################

source /home/cobs/IMANALYSIS/Runtime/ginsource.sh

RSYNC=/usr/bin/rsync
PYTHON=/usr/bin/python3
WINE=/home/cobs/.wine/drive_c/
TELEGRAMCFG=/etc/martas/telegram.cfg
TELEGRAMLOG=/var/log/magpy/imbotmin${YEAR}.log
APP=/home/cobs/Software/IMBOT/imbot/minuteanalysis.py
NOTE=/home/cobs/Software/IMBOT/imbot/telegramnote.py

MOUNTMINSTEP1=/mnt/minute/step1
MOUNTMINSTEP2=/mnt/minute/step2
MOUNTMINSTEP3=/mnt/minute/step3
MOUNTMINDEF="${MOUNTMINSTEP3}/intermagnet/minute/definitive/IAF/${YEAR}"
MINSTEP3="/srv/imbot/minute/step3/mag${YEAR}"
MINSTEP2="${MOUNTMINSTEP2}/mag${YEAR}"
MINSTEP1="${MOUNTMINSTEP1}/Mag${YEAR}"

DESTINATION="/home/cobs/IMANALYSIS/Datacheck/minute"
TMPDIR="${DESTINATION}/tmp/${YEAR}"
MEMORY="${DESTINATION}/min_analysis${YEAR}.json"

CFGDIR="/home/cobs/IMANALYSIS/Config"

mkdir -p $MOUNTMINSTEP1
mkdir -p $MOUNTMINSTEP2
mkdir -p $MOUNTMINSTEP3
mkdir -p $MINSTEP3
mkdir -p $DESTINATION
mkdir -p $TMPDIR

## ##########################################
##   Mounting the directory structure
## ##########################################

# MOUNT ONE MINUTE DATA
curlftpfs -o user=$GINMINSTEP1,allow_other $GINIP $MOUNTMINSTEP1
curlftpfs -o user=$GINMINSTEP2,allow_other $GINADDRESS $MOUNTMINSTEP2
curlftpfs -o user=$NRCANUSER,allow_other $NRCAN $MOUNTMINSTEP3

if grep -qs "$MOUNTMINSTEP1" /proc/mounts; then
  MSG="GIN STEP1 directory mounted."
  echo $MSG
  # Please uncomment using # if you are not using Telegram notifications
  $PYTHON $NOTE -t $TELEGRAMCFG -n "${MSG}" -l "IMBOTminute${YEAR}" -p $TELEGRAMLOG
  # ANALYSE
  export TERM=linux
  $PYTHON $APP -s $MINSTEP1 -i $MINSTEP2 -j $MINSTEP3 -k $MOUNTMINDEF -d $DESTINATION -t $TMPDIR -m $MEMORY -n $TELEGRAMCFG -e $CFGDIR -o $OBSLIST -w $WINE -p $OBSTESTLIST
  echo "Analysis performed"
else
  MSG="GIN directories could not be mounted (or problem with analysis)"
  echo $MSG
  # Please uncomment using # if you are not using Telegram notifications
  $PYTHON $NOTE -t $TELEGRAMCFG -n "${MSG}" -l "IMBOTminute${YEAR}" -p $TELEGRAMLOG
fi

# UMOUNT DIRECTORIES
umount $MOUNTMINSTEP1
umount $MOUNTMINSTEP2
umount $MOUNTMINSTEP3
echo "GIN unmounted - if mounting was successful"

