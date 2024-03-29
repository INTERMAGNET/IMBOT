from magpy.stream import *

from martas import martaslog as ml
from martas import sendmail as sm

import telegram_send
import os
import getopt


# Basic MARTAS Telegram logging configuration for IMBOT manager


def main(argv):
    notification = ''
    tele = ''
    name = "IMBOTmaster"
    logpath = '/var/log/magpy/imbot_master.log'
    note = {}

    try:
        opts, args = getopt.getopt(argv,"ht:n:l:p:",["telegram=","notification=","logname=","logpath=",])
    except getopt.GetoptError:
        print ('telegramnote.py -t <telegramcfg> -n <notifocation> -l <logname> -p <logpath>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- telegramnote.py will send a note to the specificied telemgram channel --')
            print ('-----------------------------------------------------------------')
            print ('telegramnote is a python3 program to send')
            print ('a note.')
            print ('')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python3 telegramnote.py -t <telegramcfg> -n <notification>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-t            : temporary directory for conversion and analysis')
            print ('-n            : path for telegram configuration file for notifications')
            print ('-l            : logname')
            print ('-p            : logpath')
            print ('-------------------------------------')
            print ('Example of memory:')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 telegramnote.py -t /etc/telegram.cfg -n "Hello World" -l IMBOTmaster')
            sys.exit()
        elif opt in ("-n", "--notifictaion"):
            notification = arg
        elif opt in ("-t", "--telegramcfg"):
            tele = os.path.abspath(arg)
        elif opt in ("-l", "--logname"):
            name = arg
        elif opt in ("-p", "--logpath"):
            logpath = os.path.abspath(arg)

    if notification == '':
        sys.exit()

    note[name] = notification

    print ("Selected logging path is ", logpath)
    martaslog = ml(logfile=logpath,receiver='telegram')
    martaslog.telegram['config'] = tele
    martaslog.msg(note)


if __name__ == "__main__":
   main(sys.argv[1:])

