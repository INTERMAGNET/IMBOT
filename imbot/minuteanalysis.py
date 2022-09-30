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

DESCRIPTION:
   IMBOT is performing data checks on data products submitted to INTERMAGNET. Currently supported are
   one minute and one second submission. Principally, IMBOT analyses contents of directories, containing
   directory names with Observatory codes. A summary with a dictionary of file types, modification times, etc
   will be stored in a local memory file. An analysis is triggered if by comparison of two summaries, usually
   a new one with a memory of a previous run, an analysis trigger is found i.e. not yet analyzed, modified


APPLICATION:

  $PYTHON $APP -s $MINDIR -d $DESTINATION -t $TMPDIR -m $MEMORY -n /etc/martas/telegram.cfg -e $CFGDIR -p $OBSTESTLIST -o $OBSLIST

"""

# Local reference for development purposes
# ------------------------------------------------------------
import sys
user='cobs'
local = True
if local:
    sys.path.insert(1,'/home/{}/Software/magpy/'.format(user))

from magpy.stream import *

sys.path.insert(1,'/home/{}/MARTAS/core/'.format(user))
from martas import martaslog as ml
from martas import sendmail as sm

import os
import glob
import getopt
import pwd
import zipfile
import tarfile
from shutil import copyfile
import filecmp
from dateutil.relativedelta import relativedelta
import gc

from imbotcore import *
from version import __version__ as imbotversion

# Basic MARTAS Telegram logging configuration for IMBOT manager
logpath = '/var/log/magpy/imbot.log'
notifictaion = {}
name = "IMBOTmin"

"""
 run GetGINDirectoryInformation(sourcepath, checkrange = 2, obslist = [],excludeobs=[]) also for step2 and step3.
  use obslist of earlier step1 run

            ** NEW Version 1.0.4**
            - It will also try to access the STEP2 and 3 directory
              If files have been moved to step2 - mail content is changed
              If files are existing in step3 they are finished
            ** NEW Version 1.0.4**
"""


def ConverTime2LocationDirectory(sourcepath, destinationpath, debug=False):
    """
    DESCRIPTION:
        reads a seimsic year-month directory structure to a year-obscode structure
        and copies all yet non-existing files in the new local structure
    VARIABLES:
        sourcepath : string : the base path of the i.e. my/path/step3/2020
        destination : string : the base path of the new directory i.e. my/path/step3new/mag2020
    """
    for root, dirs, files in os.walk(sourcepath):
        #level = root.replace(sourcepath, '').count(os.sep)
        if not dirs and files:  #asume we reached the final directory if there are no further subdirectories but files
            # new directory name is defined from first three characters of filename
            for file in files:
                dirname =  file[:3].upper()
                dstpath = os.path.join(destinationpath,dirname)
                dst = os.path.join(destinationpath,dirname,file)
                src = os.path.join(root,file)
                if not os.path.exists(dstpath):
                    if not debug:
                        print ("ConverTime2LocationDirectory: Creating new directory: {}".format(dstpath))
                        os.makedirs(dstpath)
                    else:
                        print ("ConverTime2LocationDirectory DEBUG: would create destination path {}".format(dstpath))
                if not os.path.exists(dst) or not filecmp.cmp(src, dst):
                    if not debug:
                        print ("ConverTime2LocationDirectory: copying {} to {}".format(src,dst))
                        copyfile(src, dst)
                    else:
                        print ("ConverTime2LocationDirectory DEBUG: would copy {} to {}".format(src,dst))



### ####################################
### Minute specific methods
### ####################################


def CreateMinuteMail(level, obscode, stationname='', year=2016, nameofdatachecker="Max Mustermann", notification={}):

        updatelist = notification.get('Updated data',[])
        moddict = notification.get('Modified data',{})
        step2list = notification.get('Reached step2',[])
        print ("ModDict", moddict)
        print ("step2list", step2list)
        modstr = ''
        step2str = ''
        if 'obscode' in updatelist:
            step2str = '\n\nPlease note that this submission has already been moved to STEP 2.'
        if moddict.get(obscode,None):
            filedic = moddict.get(obscode)
            modstr = ",".join([key for key in filedic])

        if obscode in updatelist:
            maintext =  "Dear data submitter,\n\nyou receive the following information as your e-mail address is connected to submissions of geomagnetic data products from {} observatory.\nYour one-minute data submission for {} has been updated within the step1 directory.\n The following files have been modified or newly uploaded:\n {}{}\n\nSuch updates automatically trigger a new evaluation by IMBOT, an automatic data checker of INTERMAGNET.\n\nThe evaluation process resulted in\n\n".format(obscode, year, modstr, step2str)
        else:
            maintext =  "Dear data submitter,\n\nyou receive the following information as your e-mail address is connected to submissions of geomagnetic data products from {} observatory.\nYour one-minute data submission for {} has been automatically evaluated by IMBOT, an automatic data checker of INTERMAGNET.\n\nThe evaluation process resulted in\n\n".format(obscode, year)


        #maintext += "LEVEL {}".format(level)

        if int(level) == 0:
            maintext += "    ISSUES to be resolved\n\n"
        else:
            maintext += "    READY for manual data checking\n\n"

        # TODO to be removed -> Done
        #maintext += "!! Please note: this is just a preliminary test of an automatic evaluation routine. The following text is fictional, ratings are NOT related to any decision of INTERMAGNET. Text and reports are suggestions to be reviewed by the INTERMAGNET data committee. !!\n\n"

        level0 = "Your data did not pass the automatic evaluation test. Please update your data submission.\nDetails can be found in the attached report. Please update your submission accordingly and perform a data check with checking tools provided by INTERMAGNET (see links below) before re-submission of your data set. If you need help please contact {}\n\n".format(nameofdatachecker)
        level1 = "Congratulations! A basic data analysis indicates that your submission is ready for final evaluation by INTERMAGNET data checkers. So far all tests have been performed automatically. Please check the attached check1min report for details.\n\nYour data set has been assigned to an INTERMAGNET data checker for evaluation.\nYour data checker is {}.\nPlease note that INTERMAGNET data checkers perform all checks on voluntary basis beside their usual duties. So please be patient. The data checker will contact you if questions arise.\n\n".format(nameofdatachecker)
        level2 = "Congratulations!\n\nYour data fulfills all requirements for a final review. A level 2 data product is already an excellent source for high resolution magnetic information. Your data set has been assigned to an INTERMAGNET data checker for final evaluation regarding data quality.\nYour data checker is {}.\nPlease note that INTERMAGNET data checkers perform all check on voluntary basis beside their usual duties. So please be patient. The data checker will contact you if questions arise.\n\n".format(nameofdatachecker)

        if int(level) == 0:
            maintext += level0
        elif int(level) == 1:
            maintext += level1
        elif int(level) == 2:
            maintext += level2

        maintext += "If you have any questions regarding the evaluation process please check out/request the general instructions (https://github.com/INTERMAGNET/IMBOT/blob/master/README.md - currently available online only for the IM definitive data committee) or contact the IMBOT manager.\n\n"
        maintext += "\nSincerely,\n       IMBOT\n\n"


        if int(level) < 2:
            instructionstext = """
    -----------------------------------------------------------------------------------
    Important Links:

    check1min (http://magneto.igf.edu.pl/soft/check1min/)

    MagPy (https://github.com/geomagpy/magpy)
                               """
            maintext += instructionstext.replace('OBSCODE',obscode)

        return maintext

def DOS_check1min(sourcepath, obscode, year=2020, winepath='/root/.wine',logdict={}, updateinfo={}, optionalheads=['StationWebInfo', 'DataTerms', 'DataReferences'], debug= False):
    # requires wine

    sleeptime = 10

    src = sourcepath
    dst = os.path.join(winepath,'daten',obscode)
    # This creates a symbolic link on python in tmp directory
    if os.path.isdir(dst):
        os.unlink(dst)
    #if not os.path.exists(dst):   # daten need to exist
    #    os.makedirs(dst)
    os.symlink(src, dst)
    if debug:
        print ("Linking {} to {}".format(src,dst))
        print (" ... now analyzing data for year {}".format(year))

    curwd = os.getcwd()
    os.chdir(winepath)

    #cmd = 'WINEPREFIX="{}" /usr/bin/wine start check1min.exe C:\\\\daten\\\\{} {} {} C:\\\\daten\\\\{}\\\\{}report{}.txt'.format(winepath,obscode,obscode,year,obscode,obscode.lower(),year)
    #if debug:
    cmd = '/usr/bin/wine start check1min.exe C:\\\\daten\\\\{} {} {} C:\\\\daten\\\\{}\\\\{}report{}.txt'.format(obscode,obscode,year,obscode,obscode.lower(),year)
    print (" Calling {}".format(cmd))
    import subprocess
    import time

    subprocess.call(cmd, shell=True)
    #proc = subprocess.Popen(cmd, cwd=winepath)

    os.chdir(curwd)
    time.sleep(sleeptime) # wait a while to finish analysis
    dirs = os.listdir(dst)
    if debug:
        print (" DIRS:", dirs)
    os.unlink(dst)


    attach = logdict.get('Attachment',[])
    attachfile = os.path.join(sourcepath,"{}report{}.txt".format(obscode.lower(),year))
    if os.path.isfile(attachfile):
        attach.append(attachfile)
    logdict['Attachment'] = attach
    checklist = logdict.get('CheckList',[])
    checklist.append('check1min (dos) performed')
    logdict['CheckList'] = checklist

    return logdict


def MagPy_check1min(sourcepath, obscode, logdict={}, updateinfo={}, optionalheads=['StationWebInfo', 'DataTerms', 'DataReferences'], debug= False):
    """
    DESCRIPTION:
        reading data and checking contents
    """

    issuelist = []
    logdict['Level'] = 1

    checkingdict = {'blvcheck':{'perfom':True}}

    print (" Running basic MagPy read and folder content test ...")

    def most_frequent(List):
            return max(set(List), key = List.count)

    # get the pathname
    def pathname(minutesource, obscode, typ='data'):
            path = ''
            readme = ''
            rlst = []
            ext = ".bin"
            extlist = []
            for root, dirs, files in os.walk(minutesource):
                #print (dirs)
                for dire in dirs:
                    if dire.endswith(obscode) and not root.find('Meta') > 0:
                        path = os.path.join(root,dire)
                        rlst = glob.glob(os.path.join(path,'*eadme*'))
                        rlst.extend(glob.glob(os.path.join(path,'README*')))
                        if len(rlst) > 1:
                            testlist = [".{}".format(obscode.lower()), ".{}".format(obscode.upper())]
                            rlst = [el for el in rlst if os.path.splitext(el)[1] in testlist]
                        if len(rlst) > 0:
                            readme = rlst[0]
                        extlist = [os.path.splitext(f)[1] for f in os.listdir(path)]
                        #if len(rlst) > 0:
                        ext = most_frequent(extlist)

            #print ("Located minute data in ", path)
            #print ("Located readme in ", readme)
            #print ("Located main extension ", ext)

            if path:
                thepath = os.path.join(path, "*{}".format(ext))

            if typ == 'readme' and readme and path:
                return os.path.join(path,readme)
            elif path:
                return thepath

            return ''

    minpath = os.path.join(sourcepath,'..')
    try:
        #print (" TRYING TO EXTRACT EMAIL ADRESSES from readme", pathname(minpath,obscode,typ='readme'))
        mails = ExtractEMails(pathname(minpath,obscode,typ='readme'))
        #print (mails)
        logdict['Contact'] = mails
    except:
        issue = "Failed to extract an email address from README file"
        issuelist.append(issue)

    extension = 'BIN'
    #======== Checking presence readme.imo yearmean.imo imoyyyy.blv =======
    try:
        bincnt = len(glob.glob(os.path.join(sourcepath,"*.bin")))
        if bincnt == 12:
             extension = 'bin'
        bincnt += len(glob.glob(os.path.join(sourcepath,"*.BIN")))
        blvcnt = len(glob.glob(os.path.join(sourcepath,"*.blv")))
        blvcnt += len(glob.glob(os.path.join(sourcepath,"*.BLV")))
        addcnt = len(glob.glob(os.path.join(sourcepath,"*.{}".format(obscode.lower()))))
        addcnt += len(glob.glob(os.path.join(sourcepath,"*.{}".format(obscode.upper()))))
        #check yearmean and readme
        print ("  -> Result: {} binary files, {} BLV files, {} *.{} files".format(bincnt, blvcnt, addcnt, obscode.lower()))
        if bincnt == 12:
            print ("   Requested binary files are present")
        elif bincnt > 12:
            print ("   More than requested binary files are present")
            issuelist.append("please check the amount of binary files - only one year")
        else:
            issuelist.append("check binary files")
            print ("   ISSUE: check presence of all requested binary files")
            logdict['Level'] = 0
        if blvcnt >= 1:
            print ("   Requested files are present")
        else:
            issuelist.append("check presence of baseline data")
            print ("   ISSUE: check baseline data")
            logdict['Level'] = 0
        if addcnt >= 2:
            print ("   Yearmean and readme seem to be present")
        else:
            issuelist.append("check yearmean/readme")
            print ("   ISSUE: check presence of yearmean /readme")
            logdict['Level'] = 0
    except:
        issue = "problem when accessing data files"
        issuelist.append(issue)
        print ("   ISSUE: {}".format(issue))
        logdict['Level'] = 0

    #==============  Readability of files
    try:
        data = read(pathname(minpath,obscode))
        logdict['AmountMin'] = data.length()[0]
    except:
        issuelist.append("binary data read problem")
        logdict['Level'] = 0
        logdict['Issues'] = issuelist
        return logdict

    #logdict['year'] = data.ndarray[0][5]

    try:
        print (" - Updating year:")
        print (data.ndarray[0][5])
        print (num2date(data.ndarray[0][5]))
        dt = num2date(data.ndarray[0][5])
        year = dt.year
        logdict['Year'] = year
    except:
        pass

    if debug:
        print ("Data length:", data.length())

    #============== Checking W01..W16 headers in IAF files ================
    """
    W01 Station code              " CLF"  (20 43 4C 46)
    W02 Year and day number      2020001  (A1 D2 1E 00)
    W03 Co-latitude (deg x 1000)   41975  (F7 A3 00 00)
    W04 Longitude (deg x 1000)      2260  (D4 08 00 00)
    W05 Elevation (metres)           145  (91 00 00 00)
    W06 Reported elements         "XYZG"  (58 59 5A 47)
    W07 Institute code            "IPGP"  (49 50 47 50)
    W08 D-conversion factor        10000  (10 27 00 00)
    W09 Data quality code         "IMAG"  (49 4D 41 47)
    W10 Instrument code           "  RC"  (20 20 52 43)
    W11 Limit for K9                 450  (C2 01 00 00)
    W12 Sample period (ms)           200  (C8 00 00 00)
    W13 Sensor orientation        "HDZF"  (48 44 5A 46)
    W14 Publication date          "2102"  (32 31 30 32) Date of acceptation as Definitive - will be set by INTERMAGNET
    W15 Format version           ver 2.1  (03 00 00 00)
    W16 Reserved word                  0  (00 00 00 00)
    """
    if debug:
        print (data.header)
        print (data.header.get('StationIAGAcode'))
        print (data.header.get('DataAcquisitionLatitude'))
        print (data.header.get('DataAcquisitionLongitude'))
        print (data.header.get('DataElevation'))
        print (data.header.get('DataComponents'))
        print (data.header.get('StationInstitution'))
        print (data.header.get('StationK9'))
        print (data.header.get('DataPublicationDate'))
        print (data.header.get('DataSensorOrientation'))
        print (data.header.get('DataFormat'))

    # ================ YEARMEAN file versus IAF files ======================


    #================ Checking BLV file ===================================


    #============== Checking K-indices in IAF files =======================


    #================== Checking Readme.IMO file ==========================


    #====== Checking the calculation daily and hourly means ===============



    #=================== Checking yearmean.imo ============================


    #=================== Creating MagPy report ============================


    logdict['Issues'] = issuelist
    checklist = logdict.get('CheckList',[])
    checklist.append('basic MagPy test performed')
    logdict['CheckList'] = checklist

    return data, logdict


def CheckOneMinute(pathsdict, tmpdir="/tmp", destination="/tmp", logdict={}, selecteddayslist=[], testobslist=[], checklist=['default'], pathemails=None, mailcfg='',notification={}, winepath='/root/.wine', year=2020, debug=False):
        """
        DESCRIPTION
            method to perfom data conversion and call the check methods
            reports and mail will be constructed for each new/updated observatory data set
        PARAMETER
            logdict (dictionary) : external, contains logging information for all analyszed data sets to be send to the IMBOT manager
            reportdict (dictionary) : internal, containes analysis reports for observatories
            readdict (dictionary) : contains a dictionary with parameters for a single observatory
            testobslist = ['WIC','BOX','DLT','IPM','KOU','LZH','MBO','PHU','PPT','TAM','CLF']

            Structure of reportdict:
                'OBSCODE'    :  { ... }  -> readdict
            Structure of readdict:
                 key                    :       value
              month_number              :      { ... } -> loggingdict
              Obscode                   :      code
              #Level                    :      obtained average quality level
              Sourcepath                :      obtained quality level
              Readability test file     :      test file
              Readability               :      only good if "OK"

        """
        reportdict = {}
        #readdict = {}
        #loggingdict = {}
        for obscode in pathsdict:
                print ("-------------------------------------------")
                print ("Starting analysis for {}".format(obscode))
                #try
                readdict = {}
                updatedictionary = {} #GetMetaUpdates()
                para = pathsdict.get(obscode)

                dailystreamlist = []
                loggingdict = {}
                loggingdict['Issues'] = []
                loggingdict['Level'] = None
                tablelist = []
                datelist = []
                emails = None
                referee = None
                nameofdatachecker = ''
                sourcepath = os.path.join(tmpdir, 'raw', para.get('obscode'))
                destinationpath = os.path.join(destination, para.get('obscode'))
                readdict['Obscode'] = para.get('obscode')
                readdict['Sourcepath'] = sourcepath
                readdict['Destinationpath'] = destinationpath

                # Check notification whether update or new
                # Extract a list of obscodes from updated data
                updatelist = notification.get('Updated data',[])
                print (" Updated data sets:", updatelist)
                updatestr = ''
                if para.get('obscode') in updatelist:
                    updatestr = 'Submission UPDATE received: '
                if debug:
                    print (" Mail subject starts with:", updatestr)

                loggingdict['year'] = year

                # - perform MagPy basic read and content check, extract binary data
                # -----------
                print (" Running MagPy test ...")
                data, loggingdict = MagPy_check1min(sourcepath,para.get('obscode'),logdict=loggingdict, updateinfo=updatedictionary, debug=debug)
                readdict['Year'] = loggingdict.get('year',year)

                destinationpath = os.path.join(destination,str(readdict.get('Year')),para.get('obscode'))
                readdict['Destinationpath'] = destinationpath

                # - perform check1min (dos) analysis  -> report will be attached to the mail
                # -----------
                print (" Running check1min ...")
                loggingdict = DOS_check1min(sourcepath,para.get('obscode'),year=readdict.get('Year'),winepath=winepath,updateinfo=updatedictionary,logdict=loggingdict, debug=debug)

                # Report
                # -----------------
                # Construct a detailed report with graphs from loggingdict and readdict and temporary graphs
                print (" Report for {}: {}".format(para.get('obscode'),loggingdict))

                #if len(loggingdict.get('Issues')) > 0 and not loggingdict.get('Level') == 0:
                #        loggingdict['Level'] = 1
                readdict['MagPyVersion'] = magpyversion

                # perform noise analysis on selcted days
                # -----------
                #if len(dailystreamlist) > 0:
                #    readdict = PowerAnalysis(dailystreamlist, readdict)
                #    # eventually update tablelist if noiselvel to large
                #    #tablelist = UpdateTable(tablelist, readdict)

                # add results to a large dictionary for logging on the IMBOT server
                # -----------
                reportdict[para.get('obscode')] = {}
                nedic = {}
                for key in readdict:
                    value = readdict[key]
                    nedic[key] = value
                reportdict[para.get('obscode')] = nedic

                # For each Obs create report and mailtext for submitter, select and inform data checker
                # -----------
                level = loggingdict.get('Level')
                print (" - Asigning data checker")
                pathrefereelist = check_path_year(os.path.join(pathemails,"refereelist_minute.cfg"),readdict.get("Year"))
                if debug:
                    print ("Loading referees from {}".format(pathrefereelist))
                nameofdatachecker, referee = GetDataChecker(para.get('obscode').upper(),pathrefereelist)
                print ("   -> found {}: {}".format(nameofdatachecker,referee))
                print (" - Creating Mail")
                stationname = ''  # contained in readme - extract
                mailtext = CreateMinuteMail(level, para.get('obscode'), stationname=stationname, year=readdict.get("Year"), nameofdatachecker=nameofdatachecker, notification=notification)
                if debug:
                    print (mailtext)

                pathmailinglist = check_path_year(os.path.join(pathemails,"mailinglist_minute.cfg"),readdict.get("Year"))
                if debug:
                    print ("Loading alternative mailing addresses from {}".format(pathmailinglist))
                email, managermail = ObtainEmailReceivers(loggingdict, para.get('obscode'), pathmailinglist, referee, debug=debug)

                print ("   -> sending to {}".format(email))

                # DEFINE A LIST OF OBERVATORIES FOR A TEST RUN - ONLY THESE OBSERVATORIES WILL GET NOTIFICATIONS
                # Send out emails
                # -----------
                if email and mailcfg:
                    if debug:
                        print ("  Using mail configuration in ", mailcfg)
                    maildict = ReadMetaData(mailcfg, filename="mail.cfg")
                    attachfilelist = loggingdict.get('Attachment',None)
                    if debug:
                        print ("  ATTACHMENT looks like:", attachfilelist)
                    if attachfilelist:
                        maildict['Attach'] = ",".join(attachfilelist)
                    maildict['Text'] = mailtext
                    maildict['Subject'] = '{}IMBOT one-minute analysis for {} {}'.format(updatestr,para.get('obscode'),readdict.get("Year"))
                    #### take FROM from mail.cfg
                    if debug:
                        print ("  Joined Mails", email)
                        print ("  -> currently only used for selected. Other mails only send to leon")
                    if len(testobslist) > 0:
                        if para.get('obscode').upper() in testobslist: #or not testobslist
                            print ("  Selected observatory is part of the 'productive' list")
                            print ("   - > emails will be send to referee, submitters and manager")
                            print ("       receivers are: {}".format(email))
                            maildict['To'] = email
                        else:
                            print ("  Selected observatory is NOT part of the 'productive' list")
                            print ("   - > emails will be send to IMBOT managers only")
                            print ("       receivers are: {}".format(managermail))
                            maildict['To'] = managermail
                    else:
                        maildict['To'] = email
                    print ("  ... sending mail now")
                    print ("       receivers are: {}".format(maildict['To']))
                    #### Stop here with debug mode for basic tests without memory and mails
                    sm(maildict)
                    print (" -> DONE: mail and report send")
                else:
                    print ("  Could not find mailconfiguration - skipping mail transfer")
                    #logdict['Not yet informed'].append(para.get('obscode'))
                    pass

                # Saving Logs and
                # Create a destination path to save reports and mails
                if not debug:
                    if not os.path.exists(destinationpath):
                        os.makedirs(destinationpath)
                    mailname = os.path.join(destinationpath, "mail-to-send.log")
                    with open(mailname, 'w') as out:
                        out.write(mailtext)
                    # write report
                    try:
                        for atf in attachfilelist:
                            print (" saving report file {}".format(atf))
                            atfname = os.path.basename(atf)
                            copyfile(atf,os.path.join(destinationpath,atfname))
                    except:
                        pass

                    if len(loggingdict) > 0:
                        savelogpath = os.path.join(destinationpath,"logdict.json")
                        WriteMemory(savelogpath, loggingdict)
                        savelogpath = os.path.join(destinationpath,"readdict.json")
                        WriteMemory(savelogpath, readdict)
                        savelogpath = os.path.join(destination,str(readdict.get('Year')),"notification.json")
                        WriteMemory(savelogpath, notification)


                # Cleanup
                # -----------
                # Delete temporary directory
                # -----------
                print (" - Deleting tempory directory {}".format(sourcepath))
                try:
                    if sourcepath.find(para.get('obscode')) > -1:
                        # just make sure that temporary information is only deleted for the current path
                        # it might happen that treatment/read failures keep some old information in dicts
                        print (" - Cleaning up temporary folder ", sourcepath)
                        shutil.rmtree(sourcepath, ignore_errors=True)
                except:
                    pass

                readdict.clear()
                gc.collect()

                #except:
                #    logdict["element"] = "Analysis problem in ConvertData routine"

        return reportdict


def main(argv):
    #imbotversion = '1.0.5'
    checkrange = 2 #3 # 3 hours
    statusmsg = {}
    obslist = []
    excludeobs = []
    source = ''
    destination = ''
    pathminute = ''
    step3mounted=''
    step3source=''
    step2source=''
    pathemails = ''
    year = 1971
    tele = '/etc/martas/telegram.cfg'
    logpath = '/var/log/magpy'
    mailcfg = '/etc/martas'
    manager = ['ro.leonhardt@googlemail.com','jreda@igf.edu.pl']
    memory='/tmp/secondanalysis_memory.json'
    tmpdir="/tmp"
    #testobslist=['WIC','BOX','DLT','IPM','KOU','LZH','MBO','PHU','PPT','TAM','CLF']
    testobslist=[]
    analysistype = 'minuteanalysis'
    winepath='/root/.wine'
    step2 = {}
    step3 = {}
    newdict={}
    logdict={}
    notifictaion={}

    debug=False

    try:
        opts, args = getopt.getopt(argv,"hs:d:t:q:m:r:n:o:i:j:k:e:l:y:c:p:w:D",["source=", "destination=", "temporary=", "quietdaylist=","memory=","report=","notify=","observatories=","step2source=","step3source=","step3mounted=","emails=","logpath=","mailcfg=","testobslist=","winepath=","debug=",])
    except getopt.GetoptError:
        print ('minuteanalysis.py -s <source> -d <destination> -t <temporary> -q quietdaylist -n <notify> -o <observatories> -i <step2source> -j <step3source> -k <step3mounted> -e <emails> -l <logpath> -y <year> -c <mailcfg> -p <testobslist>  -w <winepath>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- minuteanalysis.py will automatically analyse one second data products --')
            print ('-----------------------------------------------------------------')
            print ('minuteanalysis is a python3 program to automatically')
            print ('evaluate one second data submissions to INTERMAGNET.')
            print ('')
            print ('')
            print ('minuteanalysis requires magpy >= 0.9.5.')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python3 minuteanalysis.py -s <source> -d <destination> -t <temporary>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-s (required) : source path')
            print ('-d (required) : destination path - within this path a directory "Obscode"/level will be created')
            print ('-t            : temporary directory for conversion and analysis')
            print ('-m            : a json file with full path for "memory"')
            print ('-q            : a comma separated list of quiet days for noiselevel determination')
            print ('-o            : a comma separated list of Obscodes/directories to deal with')
            print ('-x            : a comma separated list of Obscodes/directories to exclude')
            print ('-p            : preliminary obslist for full reporting - testobslist')
            print ('-i            : basic directory for step2 minute data (IAF files)')
            print ('-j            : basic directory for step3 minute data (IAF files)')
            print ('-k            : mounted NRCAN definitive directory (IAF files)')
            print ('-e            : path to a local email repository - names: mailinglist.cfg, refereelist.cfg')
            print ('-n            : path for telegram configuration file for notifications')
            print ('-y            : year of analysis')
            print ('-c            : path for mail configuration file "mail.cfg" - default is /etc/martas')
            print ('-l            : path for logs and logging info, default is /var/log/magpy')
            print ('-------------------------------------')
            print ('Example of memory:')
            print ('-------------------------------------')
            print ('Application:')
            print ('-------------------------------------')
            print ('- debug mode')
            print ('python3 /home/leon/Software/IMBOT/imbot/minuteanalysis.py -s /home/leon/Cloud/Test/IMBOTminute/IMinput/2020_step1 -d /home/leon/Cloud/Test/IMBOTminute/IMoutput/ -t /tmp -m /home/leon/Cloud/Test/IMBOTminute/analysetest.json -n /etc/martas/telegram.cfg -e /home/leon/Software/IMBOTconfig -o DOU -w /home/leon/.wine/drive_c -D')
            print ('- test mode')
            print ('python3 minuteanalysis.py -s /home/leon/Tmp -t /tmp -d /tmp -o BOU -i /home/leon/Tmp/minute')
            print ('python3 secondanalysis.py -s /media/leon/Images/Mag2020 -d /tmp -t /media/leon/Images/DataCheck/tmp -i /media/leon/Images/DataCheck/2016/minute/Mag2016 -m /media/leon/Images/DataCheck/2016/testanalysis.json -o WIC')
            print ('python3 minuteanalysis.py -s /media/leon/Images/Mag2020 -d /tmp -t /tmp -o CLF -e /home/leon/IMBOT/minute -D')
            sys.exit()
        elif opt in ("-s", "--source"):
            # delete any / at the end of the string
            source = os.path.abspath(arg)
        elif opt in ("-d", "--destination"):
            destination = os.path.abspath(arg)
        elif opt in ("-t", "--temporary"):
            tmpdir = os.path.abspath(arg)
        elif opt in ("-m", "--memory"):
            memory = os.path.abspath(arg)
        elif opt in ("-i", "--step2source"):
            step2source = os.path.abspath(arg)
        elif opt in ("-j", "--step3source"):
            step3source = os.path.abspath(arg)
        elif opt in ("-k", "--step3mounted"):
            step3mounted = os.path.abspath(arg)
        elif opt in ("-e", "--emails"):
            pathemails = arg
        elif opt in ("-q", "--quietdaylist"):
            quietdaylist = arg.split(',')
        elif opt in ("-o", "--observatories"):
            obslist = arg.replace(" ","").split(',')
        elif opt in ("-x", "--exclude"):
            excludeobs = arg.replace(" ","").split(',')
        elif opt in ("-n", "--notify"):
            tele = os.path.abspath(arg)
        elif opt in ("-c", "--mailcfg"):
            mailcfg = os.path.abspath(arg)
        elif opt in ("-y", "--year"):
            year = int(arg)
        elif opt in ("-l", "--logpath"):
            logpath = os.path.abspath(arg)
        elif opt in ("-p", "--testobslist"):
            if arg in ['None','False','none','false','No','no',' ']:
                testobslist = []
            else:
                testobslist = arg.split(',')
        elif opt in ("-w", "--winepath"):
            winepath = os.path.abspath(arg)
        elif opt in ("-D", "--debug"):
            debug = True

    begin = datetime.utcnow()


    if 'REFEREE' in obslist:
        pathreferee = check_path_year(os.path.join(pathemails,"refereelist_minute.cfg"),year)
        obslist = GetObsListFromChecker(obslist, pathreferee)
        print (" OBSLIST provided: dealing only with {}".format(obslist))

    if debug and source == '':
        print ("Basic code test - done")
        sys.exit(0)

    if not os.path.exists(os.path.join(logpath,analysistype)):
        os.makedirs(os.path.join(logpath,analysistype))

    if not tele == '':
        # ################################################
        #          Telegram Logging
        # ################################################
        ## New Logging features
        from martas import martaslog as ml
        # tele needs to provide logpath, and config path ('/home/cobs/SCRIPTS/telegram_notify.conf')
        telelogpath = os.path.join(logpath,analysistype,"telegram.log")

    if source == '':
        print ('Specify a valid path to a jobs dictionary (json):')
        print ('-- check minuteanalysis.py -h for more options and requirements')
        sys.exit()
    else:
        memdict = ReadMemory(memory)

    if not os.path.exists(tmpdir):
        print ('Temporary path not exististig - creating it..')
        os.makedirs(tmpdir)


    """
    Main Prog
    """

    print ("Running IMBOT version {}".format(imbotversion))
    print (" 1. entering source directory and locate files, check memory and whether file dates agree with criterion")

    ## 1.1 Get current directory structure of sources
    try:
        #  1.1.1 Access and transform step3 directory
        #try:
        if step3mounted:
            if debug:
                print ("Converting step3 definitive data from seismic to magnetic representation")
            success = ConverTime2LocationDirectory(step3mounted, step3source, debug=False)
        if step3source:
            step3, ld3 = GetGINDirectoryInformation(step3source, checkrange=0, obslist=obslist,excludeobs=excludeobs)
            try:
                print (" -> obtained in Step3 directory: {}".format([key for key in step3]))
            except:
                print (" -> no Step3 data")
        else:
            print (" 1.1.1 step3 source not defined")
    except:
        print ("Failure in step 1.1.1")
        step3 = {}
    try:
        #  1.1.2 Access step2 directory
        if step2source:
            step2, ld2 = GetGINDirectoryInformation(step2source, checkrange=checkrange, obslist=obslist,excludeobs=excludeobs)
            try:
                print (" -> obtained Step2 directory: {}".format([key for key in step2]))
            except:
                print (" -> no Step2 data")
        else:
            print (" 1.1.2 step2 source not defined")
    except:
        print ("Failure in step 1.1.1")
        step2 = {}
    try:
        #  1.1.3 Access step1 directory
        step1, logdict = GetGINDirectoryInformation(source, checkrange=checkrange,obslist=obslist,excludeobs=excludeobs)
        try:
            print (" -> obtained in Step1 directory: {}".format([key for key in step1]))
        except:
            print (" -> no Step1 data")
    except:
        print ("Failure in step 1.1")

    ## 1.2 Subtract the two directories - only files will remain which are not yet listed in final step 3
    #try:
    ok =True
    if ok:
        #  1.2.1 Remove CODES already existing in step3 (and put to notification list)
        st1new,noti = GetNewInputs(step3, step1, simple=True, notification={}, notificationkey='Reached step3', debug=False)
        print ("1", noti)
        #  1.2.2 Put CODES already existing in step2 to notification list
        stforget,noti = GetNewInputs(step2, st1new, simple=True, notification=noti, notificationkey='Reached step2', debug=False)
        print ("2", noti)
        #  1.2.3 Get changed records
        print (memdict)
        print (st1new)
        newdict, notification = GetNewInputs(memdict, st1new, simple=False, notification=noti)
        print (" -> removed all obscodes which have been moved/copied to step3")
        print ("    result: {}".format(notification))
    #except:
    #    print ("Failure in step 1.2")

    print ("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    print ("++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

    if debug:
        print ("Got New uploads:", newdict)

    # 2. For each new input --- copy files to a temporary local directory (unzip if necessary)
    logdict = CopyTemporary(newdict, tmpdir=tmpdir, logdict=logdict)

    print ("Running conversion and data check:")
    # 3. Convert Data includes validity tests, report creation and exporting of data
    fullreport = CheckOneMinute(newdict, tmpdir=tmpdir, destination=destination, logdict=logdict,testobslist=testobslist,pathemails=pathemails,mailcfg=mailcfg,notification=notification, winepath=winepath, year=year, debug=debug)

    # 4. Memory for already analyzed data
    # add successful analysis to memory
    # -----------
    for key in newdict:
        memdict[key] = newdict[key]
    if debug:
        print ("Updating Memory: {}".format(memdict))
    else:
        print ("Updating Memory...")
    success = WriteMemory(memory, memdict)

    # I need an analysis report and a "program" runtime log
    if debug:
        print ("Fullreport", fullreport)

    # 4.1 send a report to the IMBOT manager containg all failed and successful analysis and whether submitter was informed
    # drop Reached step2
    notification.pop('Reached step2', None)
    # drop Reached step3
    notification.pop('Reached step3', None)
    # drop Modified data
    notification.pop('Modified data', None)

    if not tele == '' and not debug:
        martaslog = ml(logfile=telelogpath,receiver='telegram')
        martaslog.telegram['config'] = tele
        martaslog.msg(notification)

    end = datetime.utcnow()

    print ("   needed {}".format(end-begin))
    print ("=> ONE-MINUTE DATA ANALYSIS SUCCESSFULLY FINISHED")


if __name__ == "__main__":
   main(sys.argv[1:])
