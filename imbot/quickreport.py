#!/usr/bin/env python3
# coding=utf-8

"""
IMBOT - automatic analysis of one minute data

PREREQUISITES:

  sudo pip3 install geomagpy>=1.0.1
  sudo pip3 install telegram_send
  sudo apt-get install curlftpfs
  sudo apt install p7zip-full p7zip-rar

  To transfer the JOB:
   - cp IMBOT dictionary
   - create DataCheck paths
   - update analysis.sh
   - cp mail and telegram.cfg (check/update contents)
   - get ginsource file
   - get analysis20xx.json
   - add credentials
   - test
   - update crontab

APPLICATION:

  $PYTHON $APP -s $MINDIR -d $DESTINATION -t $TMPDIR -m $MEMORY -n /etc/martas/telegram.cfg -e $CFGDIR -q $QUIETDAYLIST -p $OBSTESTLIST -o $OBSLIST

"""

# Local reference for development purposes
# ------------------------------------------------------------
local = False
if local:
    import sys
    sys.path.insert(1,'/home/leon/Software/magpy/')

from magpy.stream import *

from martas import martaslog as ml
from martas import sendmail as sm

import telegram_send

import os
import glob
import getopt
import pwd
import re

from imbotcore import *


def markdown_table(head,body):

    #body = sort(body)
    table = " | ".join(head)
    table += "\n"
    table += " | ".join(['-----' for el in head])
    table += "\n"
    for line in body:
        line = [str(el) for el in line]
        table += " | ".join(line)
        table += "\n"
    
    return table
    
def get_logdict(obscode, path=''):
    """
    DESCRIPTION
        logdict contains basic analysis results like level and issues
    """
    logfile = os.path.join(path,obscode.upper(),'logdict.json')
    if os.path.exists(logfile):
        logdict = ReadMemory(logfile)
        print (logdict)
        
    else:
        # scan for level2_underreview.txt
        logname = ''
        logfile = os.path.join(path,obscode.upper(),'level*.txt')
        for name in glob.glob(logfile):
            logname = name
        logdict = {}
        lev = re.findall(r'\d+', logname)
        if len(lev) > 0:
            logdict['Level'] = int(re.findall(r'\d+', logname)[-1])
        else:
            logdict['Level'] = ""

    return logdict

def create_result_table(memory, tformat='markdown',style='simple', logpath=''):
    table = ''
    
    if style == 'simple':
        head = ['IAGA code', 'date', 'level']
    elif style == 'simple':
        head = ['IAGA code', 'date', 'submitted', 'level']
    
    memdict = ReadMemory(memory)
    body = []
    for sub in memdict:
        valuedict = memdict.get(sub)
        obscode = valuedict.get('obscode')
        logdict = get_logdict(obscode,path=logpath)
        datetimestamp = valuedict.get('lastmodified')
        date = datetime.utcfromtimestamp(float(datetimestamp))
        stype = valuedict.get('type')
        if style == 'simple':
            body.append([obscode,date.date(),logdict.get('Level')])

    table = markdown_table(head,body)
    

    return table 

def create_runtime_table(tformat='markdown',style='simple', logpath='',debug=False):
    """
    DESCRIPTION
        scan last log files for each year and whether they are successful
    """
    table = ''
    
    if style == 'simple':
        head = ['year', 'resolution', 'lastrun', 'success']

    body = []
    logfile = os.path.join(logpath,'last*analysis*')
    for name in glob.glob(logfile):
        logdict = {}
        yearl = re.findall(r'\d+', name)
        if len(yearl) > 0:
            year = int(yearl[-1])
        # get creation data
        if 'min' in name:
            res = 'min'
        else:
            res = 'sec'
        stat=os.stat(name)
        mtime=stat.st_mtime
        ctime=stat.st_ctime
        mdate = datetime.utcfromtimestamp(float(mtime))
        stmdate = datetime.strftime(mdate,"%Y-%m-%dT%H:%M")
        # find SUCCESS in file
        succ = 'No'
        with open(name) as f:
            if 'ANALYSIS SUCCESSFULLY FINISHED' in f.read():
                succ = 'Yes'
        body.append([year,res,stmdate,succ])

    table = markdown_table(head,body)
    return table

def main(argv):
    quickreportversion = '1.0.0'
    tele = ''
    obslogpath = '/tmp/datacheck'
    logpath = '/var/log/magpy'
    mailcfg = '/etc/martas'
    memory='/tmp/secondanalysis_memory.json'
    telegramconf = "/etc/martas/telegram.cfg"
    job = 'obssummary'

    debug=False

    try:
        opts, args = getopt.getopt(argv,"hm:l:j:t:D",["memory=","logpath=","job=","telegramconf=","debug=",])
    except getopt.GetoptError:
        print ('quickreport.py -m <memory> -l <logpath> -j <job> -j <telegramconf>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- quickreport.py will create a table with IMBOT analyzed data')
            print ('-----------------------------------------------------------------')
            print ('quickreport is a python3 program to automatically')
            print ('evaluate one second data submissions to INTERMAGNET.')
            print ('')
            print ('')
            print ('quickreport requires magpy >= 1.0.0.')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python3 secondanalysis.py -s <source> -d <destination> -t <temporary>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-m            : a json file with full path for "memory"')
            print ('-j            : obssummary, runtime')
            print ('-l            : logpath with analysis data for obs')
            print ('              : i.e. if /srv/datacheck/2020/TAM/logdict.json')
            print ('              :      then logpath is /srv/datacheck/2020')
            print ('-t            : telegram configuration path')
            print ('-------------------------------------')
            print ('Example of memory:')
            print ('-------------------------------------')
            print ('Application:')
            print ('-------------------------------------')
            print ('python3 /home/leon/Software/IMBOT/imbot/quickreport.py -m ~/analysis2020.json -l ~/Cloud/Test/IMBOTsecond/IMoutput/level')
            print ('python3 /home/leon/Software/IMBOT/imbot/quickreport.py -m ~/analysis2020.json -l ~/Cloud/Test/IMBOTsecond/IMoutput/level')
            sys.exit()
        elif opt in ("-m", "--memory"):
            memory = os.path.abspath(arg)
        elif opt in ("-l", "--logpath"):
            obslogpath = os.path.abspath(arg)
        elif opt in ("-j", "--job"):
            job = arg
        elif opt in ("-t", "--telegramconf"):
            telegramconf = arg
        elif opt in ("-D", "--debug"):
            debug = True


    if debug and memory == '':
        print ("Basic code test - done")
        sys.exit(0)
    
    if not tele == '':
        # ################################################
        #          Telegram Logging
        # ################################################
        ## New Logging features
        from martas import martaslog as ml
        # tele needs to provide logpath, and config path ('/home/cobs/SCRIPTS/telegram_notify.conf')
        telelogpath = os.path.join(logpath,analysistype,"telegram.log")

    if job == 'obssummary':
        if not os.path.exists(memory):
            print ("Memory not existing")
            sys.exit(0)
        table = create_result_table(memory,logpath=obslogpath)
    elif job == 'runtime':
        table = create_runtime_table(logpath=obslogpath)

    print (table)
    table = "```\n{}\n```".format(table)
    if telegramconf:
        telegram_send.send(messages=[table], conf=telegramconf, parse_mode="Markdown")



if __name__ == "__main__":
   main(sys.argv[1:])
