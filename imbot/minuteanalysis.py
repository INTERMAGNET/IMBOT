#!/usr/bin/env python3
# coding=utf-8

"""
MagPy - Analysis one second data files automatically

PREREQUISITES:

  sudo pip3 install geomagpy==0.9.7
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

  Options:
      if OBStestlist is given:
          if obs in testobslist:
             -> full reports will be send to referee, obs and admin (refereelist_minute)
          if not :
             -> reports will be send  to managers from (mailinglist_minute)
      if not given:
          -> full reports will be send to referee, obs and admin (refereelist_minute)
      
      if OBSLIST:
          -> only these obs will be analyzed
          -> if REFREE is contained, then all all obs listes in refereelist_minute will be used

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

import os
import glob
import getopt
import pwd
import zipfile
import tarfile
from shutil import copyfile
from dateutil.relativedelta import relativedelta
import gc

from imbotcore import *

# Basic MARTAS Telegram logging configuration for IMBOT manager
logpath = '/var/log/magpy/imbot.log'
notifictaion = {}
name = "IMBOT"


def GetUploadMinuteInformation(sourcepath, checkrange = 2, obslist = [],excludeobs=[]):
        """
        DESCRIPTION:
            Method will check directory structure of the STEP1 one second directory
            It will extract directory, amount of files, filetype, and last modification date
        APPLICTAION:
            to check step 1 one second directory
            Suggested technique for updating previously submitted and updated step10,level1, and level2 data:
            Data passing all level0 clearance is moved to a new path (raw: step1, level1-3: level)
            --- extract level information from directory:
            --- thus add a file called " levelx.txt" with the highest reached level after each treatment, add a asterix for data awaiting a check
            This way, the same method can also be applied to the level directory
        """
        print ("Running - getting upload information")
        print (" for observatories: {}".format(obslist))
        storage = {}
        logdict = {}
        for root, dirs, files in os.walk(sourcepath):
          level = root.replace(sourcepath, '').count(os.sep)
          if (len(obslist) > 0 and root.replace(sourcepath, '')[1:4] in obslist) or len(obslist) == 0:
            if (len(excludeobs) > 0 and not root.replace(sourcepath, '')[1:4] in excludeobs) or len(excludeobs) == 0:
              if level == 1:
                print ("Found directory:", root)
                # append root, and ctime of youngest file in directory
                timelist = []
                extlist = []
                obscode = root.replace(sourcepath, '')[1:4]
                for f in files:
                    try:
                        stat=os.stat(os.path.join(root, f))
                        mtime=stat.st_mtime
                        ctime=stat.st_ctime
                        ext = os.path.splitext(f)[1]
                        timelist.append(mtime)
                        extlist.append(ext)
                    except:
                        logdict[root] = "Failed to extract mtimes"
                if len(timelist) > 0:
                    youngest = max(timelist)
                    print (" Last modified : {} ; checking data older than {}".format(datetime.utcfromtimestamp(youngest), datetime.utcnow()-timedelta(hours=checkrange)))
                    # only if latest file is at least "checkrange" hours old
                    if datetime.utcfromtimestamp(youngest) < datetime.utcnow()-timedelta(hours=checkrange):
                        # check file extensions ... and amount of files (zipped, cdf, sec)
                        # firstly remove txt, par and md from list (meta.txt contain updated parameters)
                        print (extlist)
                        extlist = [el for el in extlist if not el in ['.txt', '.md']]
                        amount = len(files)
                        if len(extlist) > 0:
                            typ = max(extlist,key=extlist.count)
                            if typ in ['.zip', '.gz', '.tgz', '.tar.gz', '.tar', '.cdf', '.sec']:
                                parameter = {'amount': amount, 'type': typ, 'lastmodified': youngest, 'obscode': obscode}
                                storage[root] = parameter
                            elif typ in ['.min', '.bin', '.{}'.format(obscode.lower()), '.blv', '.BIN', '.BLV', '.{}'.format(obscode.upper())]:
                                parameter = {'amount': amount, 'type': typ, 'lastmodified': youngest, 'obscode': obscode}
                                storage[root] = parameter
                            else:
                                logdict[root] = "Found unexpected data type '{}'".format(typ)
                        else:
                            logdict[root] = "Directory existing - but no files found"
                    else:
                        logdict[root] = "Uploaded recently - eventually not finished"
              elif level > 1:
                logdict[root] = "Found subdirectories - ignoring this folder"

        return storage, logdict

### ####################################
### MagPy Testing methods - one-second 
### ####################################

def DeltaFTest(data, logdict):
        """
        DESCRIPTION
            reading F values in file, analyzing independency and delta F variaton
        """
        issuedict = {}
        warningdict = {}
        issuedict=logdict.get('Issues',{})
        warningdict=logdict.get('Warnings',{})
        fcol = data._get_column('f')
        dfcol = data._get_column('df')
        fmean = 99
        fstd = 99
        if len(fcol) == 0 and len(dfcol) == 0:
            print ("No F or dF values found")
            logdict['F'] = "None"
            logdict['delta F'] = "None"
        else:
            f1text = 'found f-col - problem -'
            scal=''
            if len(fcol) > 0:
                scal = 'f'
            elif len(dfcol) > 0:
                scal = 'df'
            ftest = data.copy()
            ftest = ftest._drop_nans(scal)
            fsamprate = ftest.samplingrate()
            f1text = "found independend"
            if scal=='f':
                ftest = ftest.delta_f()

            fmean, fstd = ftest.mean('df',std=True)
            logdict['delta F'] = "mean delta F of {:.3f} with a std of {:.3f}".format(fmean,fstd)
            if np.abs(fmean) >= 1.0:
                warningdict['F'] = 'mean delta F exceeds 1 nT'
            if fstd >= 3.0:
                issuedict['F'] = 'dF/G shows large scatter about mean'
            if np.abs(fmean) < 0.01 and fstd < 0.01:
                f1text = 'found'   # eventually not-independent
            if np.abs(fmean) < 0.001 and fstd < 0.001:
                f1text = 'found not-independend'

            f2text = "{} {} with sampling period: {} sec\n".format(f1text,scal, fsamprate)
            logdict['F'] = f2text

        logdict['Issues'] = issuedict
        logdict['Warnings'] = warningdict

        return logdict


def GetDayPSD(stream, comp):
        dt = stream.get_sampling_period()*24.*3600.
        t = np.asarray(stream._get_column('time'))
        val = np.asarray(stream._get_column(comp))
        mint = np.min(t)
        tnew, valnew = [],[]
        nfft = int(nearestPow2(len(t)))
        if nfft > len(t):
            nfft = int(nearestPow2(len(t) / 2.0))

        for idx, elem in enumerate(val):
            if not isnan(elem):
                tnew.append((t[idx]-mint)*24.*3600.)
                valnew.append(elem)

        tnew = np.asarray(tnew)
        valnew = np.asarray(valnew)

        psdm = mlab.psd(valnew, nfft, 1/dt)
        asdm = np.sqrt(psdm[0])
        freqm = psdm[1]

        return (psdm, asdm, freqm)


def PowerAnalysis(dailystreamlist, readdict, period=10.):
        """
        DESCRIPTION
            very simple noiselevel analysis
            calculates mean noise level below a certain threshold period (e.g. 10sec)
            from each daily stream
        RETURNS
            dictionary input at "Noiselevel" containing the arithmetic mean of all noiselevels  
            dictionary input at "NoiselevelStdDeviation" containing the StandardDeviation of all noiselevels  
        """
        print ("Running Power Analysis for {} records".format(len(dailystreamlist)))
        if len(dailystreamlist) > 0:
            noiselevellist = []
            failedlist = [0]
            for daystream in dailystreamlist:
                dayst = DataStream()
                dayst.ndarray = daystream
                #print (daystream, dayst.length()[0])

                if dayst.length()[0]>0:
                    try:
                        #print( "getting power") 
                        (psdm, asdm, freqm) = GetDayPSD(dayst, 'x')
                        #print( "getting power 2", len(asdm))
                        asdmar = np.asarray(asdm)
                        idx = (np.abs(freqm - (1./period))).argmin()   # for testing purpose the noise level is calculated between nyquist and 10 sec
                        #print( "getting power 3", idx)
                        noiselevel = np.mean(asdmar[idx:])
                        #print( "getting power 4", noiselevel)
                        noiselevellist.append(noiselevel)
                    except:
                        failedlist.append(1)
            #print ("NOISELIST", noiselevellist)
            try:
                readdict['Noiselevel'] = np.mean(np.asarray(noiselevellist))
            except:
                pass
            if len(failedlist) > 1:
                readdict['Failed noiselevel determinations'] = np.sum(np.asarray(failedlist))
            try:
                readdict['NoiselevelStdDeviation'] = np.std(np.asarray(noiselevellist))
            except:
                readdict['NoiselevelStdDeviation'] = 0.0

        return readdict


### ####################################
### Minute specific methods 
### ####################################


def CreateMinuteMail(level, obscode, stationname='', year=2016, nameofdatachecker="Max Mustermann"):

        maintext =  "Dear data submitter,\n\nyou receive the following information as your e-mail address is connected to submissions of geomagnetic data products from {} observatory.\nYour one-minute data submission for {} has been automatically evaluated by IMBOT, an automatic data checker of INTERMAGNET.\n\nThe evaluation process resulted in\n\n".format(obscode, year)


        maintext += "LEVEL {}".format(level)

        if int(level) == 0:
            maintext += "    ISSUES to be resolved\n\n"
        else:
            maintext += "    READY for manual data checking\n\n"

        # TODO to be removed
        maintext += "!! Please note: this is just a preliminary test of an automatic evaluation routine. The following text is fictional, ratings are NOT related to any decision of INTERMAGNET. Text and reports are suggestions to be reviewed by the INTERMAGNET data committee. !!\n\n"

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

    curwd = os.getcwd()
    os.chdir(winepath)

    cmd = 'WINEPREFIX="{}" /usr/bin/wine start check1min.exe C:\\\\daten\\\\{} {} {} C:\\\\daten\\\\{}\\\\{}report{}.txt'.format(winepath,obscode,obscode,year,obscode,obscode.lower(),year)
    if debug:
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
    attach.append(os.path.join(sourcepath,"{}report{}.txt".format(obscode.lower(),year)))
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
            print ("   check presence of all requested binary files")
            logdict['Level'] = 0
        if blvcnt >= 1:
            print ("   Requested files are present")
        else:
            issuelist.append("check presence of baseline data")
            print ("   check baseline data")
            logdict['Level'] = 0
        if addcnt >= 2:
            print ("   Yearmean and readme seem to be present")
        else:
            issuelist.append("check yearmean/readme")
            print ("   check presence of yearmean /readme")
            logdict['Level'] = 0
    except:
        issue = "problem when accessing data files"
        issuelist.append(issue)
        print ("   {}".format(issue))
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

    print (data.length())

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


def CheckOneMinute(pathsdict, tmpdir="/tmp", destination="/tmp", logdict={}, selecteddayslist=[], testobslist=[], checklist=['default'], pathemails=None, mailcfg='',notification={}, winepath='/root/.wine', debug=False):
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
        for element in pathsdict:
                print ("-------------------------------------------")
                print ("Starting analysis for {}".format(element))
                #try
                readdict = {}
                para = pathsdict.get(element)
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
                #print (notification)
                print (" Notification: ", notification.get('Updated data',[]))
                print (" Obscode:", para.get('obscode'))
                # Extract a list of obscodes from updated data
                updatelist = notification.get('Updated data',[])
                if len(updatelist) > 0:
                    updatelist = [os.path.split(el)[-1] for el in updatelist]
                print (" Updated data sets:", updatelist)
                updatestr = ''
                obscode = para.get('obscode')
                if obscode in updatelist:
                    updatestr = 'Submission UPDATE received: '

                print (" Update string:", updatestr)
                updatedictionary = {} #GetMetaUpdates()
                loggingdict = {}

                # Initializing analysis year
                year = datetime.utcnow().year - 1
                loggingdict['year'] = year

                # - perform MagPy basic read and content check, extract binary data
                # -----------
                data, loggingdict = MagPy_check1min(sourcepath,para.get('obscode'),logdict=loggingdict, updateinfo=updatedictionary, debug=debug)
                readdict['Year'] = loggingdict.get('year',year)

                # - perform check1min (dos) analysis  -> report will be attached to the mail
                # -----------
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
                if len(dailystreamlist) > 0:
                    readdict = PowerAnalysis(dailystreamlist, readdict)
                    # eventually update tablelist if noiselvel to large
                    #tablelist = UpdateTable(tablelist, readdict)

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
                nameofdatachecker, referee = GetDataChecker(para.get('obscode').upper(),os.path.join(pathemails,"refereelist_minute.cfg"))
                print ("   -> found {}: {}".format(nameofdatachecker,referee))
                print (" - Creating Mail")
                stationname = ''  # contained in readme - extract
                mailtext = CreateMinuteMail(level, para.get('obscode'), stationname=stationname, year=readdict.get("Year"), nameofdatachecker=nameofdatachecker)


                email, managermail = ObtainEmailReceivers(loggingdict, para.get('obscode'), os.path.join(pathemails,"mailinglist_minute.cfg"), referee, debug=debug)

                print ("   -> sending to {}".format(email))

                # DEFINE A LIST OF OBERVATORIES FOR A TEST RUN - ONLY THESE OBSERVATORIES WILL GET NOTIFICATIONS
                # Send out emails
                # -----------
                if email and mailcfg:
                    if debug:
                        print ("  Using mail configuration in ", mailcfg)
                    maildict = ReadMetaData(mailcfg, filename="mail.cfg")
                    attachfilelist = loggingdict.get('Attachment')
                    if debug:
                        print ("  ATTACHMENT looks like:", attachfilelist)
                        print ("   -> for file sending", ",".join(attachfilelist))
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
                            maildict['To'] = email
                        else:
                            print ("  Selected observatory is NOT part of the 'productive' list")
                            print ("   - > emails will be send to IMBOT managers only")
                            maildict['To'] = managermail
                    else:
                        maildict['To'] = email
                    print ("  ... sending mail now")
                    #### Stop here with debug mode for basic tests without memory and mails
                    #sys.exit()
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
                            print (" saving file {}".format(atf))
                            copyfile(atf,destinationpath)
                    except:
                        pass

                    if len(loggingdict) > 0:
                        savelogpath = os.path.join(destinationpath,"logdict.json")
                        WriteMemory(savelogpath, loggingdict)
                        savelogpath = os.path.join(destinationpath,"readdict.json")
                        WriteMemory(savelogpath, readdict)


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
    imbotversion = '1.0.3'
    checkrange = 0 #3 # 3 hours
    statusmsg = {}
    obslist = []
    excludeobs = []
    source = ''
    destination = ''
    pathminute = ''
    pathemails = ''
    tele = ''
    logpath = '/var/log/magpy'
    mailcfg = '/etc/martas'
    quietdaylist = ['2016-01-25','2016-01-29','2016-02-22','2016-03-13','2016-04-01','2016-08-28','2016-10-21','2016-11-05','2016-11-17','2016-11-19','2016-11-30','2016-12-01','2016-12-03','2016-12-04']
    manager = ['ro.leonhardt@googlemail.com','jreda@igf.edu.pl','hom@ngs.ru','tero.raita@sgo.fi','heumez@ipgp.fr','Andrew.Lewis@ga.gov.au']
    memory='/tmp/secondanalysis_memory.json'
    tmpdir="/tmp"
    #testobslist=['WIC','BOX','DLT','IPM','KOU','LZH','MBO','PHU','PPT','TAM','CLF']
    testobslist=[]
    analysistype = 'minuteanalysis'
    winepath='/root/.wine'

    debug=False

    try:
        opts, args = getopt.getopt(argv,"hs:d:t:q:m:r:n:o:i:e:l:c:p:w:D",["source=", "destination=", "temporary=", "quietdaylist=","memory=","report=","notify=","observatories=","minutesource=","emails=","logpath=","mailcfg=","testobslist=","winepath=","debug=",])
    except getopt.GetoptError:
        print ('minuteanalysis.py -s <source> -d <destination> -t <temporary> -q quietdaylist -n <notify> -o <observatories> -i <minutesource> -e <emails> -l <logpath> -c <mailcfg> -p <testobslist>  -w <winepath>')
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
            print ('secondanalysis requires magpy >= 0.9.5.')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python3 secondanalysis.py -s <source> -d <destination> -t <temporary>')
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
            print ('-i            : basic directory on one minute data (IAF files)')
            print ('-e            : path to a local email repository - names: mailinglist.cfg, refereelist.cfg')
            print ('-n            : path for telegram configuration file for notifications')
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
        elif opt in ("-i", "--minutesource"):
            pathminute = os.path.abspath(arg)
        elif opt in ("-e", "--emails"):
            pathemails = arg
        elif opt in ("-q", "--quietdaylist"):
            quietdaylist = arg.split(',')
        elif opt in ("-o", "--observatories"):
            obslist = arg.replace(" ","").split(',')
            if 'REFEREE' in obslist:
                obslist = GetObsListFromChecker(obslist, os.path.join(pathemails,"refereelist_minute.cfg"))
            print (" OBSLIST provided: dealing only with {}".format(obslist))
        elif opt in ("-x", "--exclude"):
            excludeobs = arg.replace(" ","").split(',')
        elif opt in ("-n", "--notify"):
            tele = os.path.abspath(arg)
        elif opt in ("-c", "--mailcfg"):
            mailcfg = os.path.abspath(arg)
        elif opt in ("-l", "--logpath"):
            logpath = os.path.abspath(arg)
        elif opt in ("-p", "--testobslist"):
            testobslist = arg.split(',')
        elif opt in ("-w", "--winepath"):
            winepath = os.path.abspath(arg)
        elif opt in ("-D", "--debug"):
            debug = True


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
    # 1. got to source directory and locate files, check memory and whether file dates agree with criterion

    ## 1.1 Get current directory structure of source
    currentdirectory, logdict = GetUploadMinuteInformation(source, checkrange=checkrange,obslist=obslist,excludeobs=excludeobs)
    print ("Obtained Step1 directory: {}".format(currentdirectory))

    print ("Previous uploads: ", memdict)
    ## 1.2 Subtract the two directories - only new files remain
    newdict, notification = GetNewInputs(memdict,currentdirectory)
    print (notification)

    print ("Got New uploads:", newdict)
    # 2. For each new input --- copy files to a temporary local directory (unzip if necessary)
    logdict = CopyTemporary(newdict, tmpdir=tmpdir, logdict=logdict)

    print ("Running conversion and data check:")
    # 3. Convert Data includes validity tests, report creation and exporting of data
    fullreport = CheckOneMinute(newdict, tmpdir=tmpdir, destination=destination, logdict=logdict,selecteddayslist=quietdaylist,testobslist=testobslist,pathemails=pathemails,mailcfg=mailcfg,notification=notification, winepath=winepath, debug=debug)

    # 4. Memory for already analyzed data
    # add successful analysis to memory
    # -----------
    for key in newdict:
        memdict[key] = newdict[key]
    print ("Updating Memory: {}".format(memdict))
    success = WriteMemory(memory, memdict)

    # I need an analysis report and a "program" runtime log
    print ("Fullreport", fullreport)
    # 

    # 4.1 send a report to the IMBOT manager containng all failed and successful analysis and whether submitter was informed


    if not tele == '' and not debug:
        martaslog = ml(logfile=telelogpath,receiver='telegram')
        martaslog.telegram['config'] = tele
        martaslog.msg(notification)

    print ("-> ONE-MINUTE DATA ANALYSIS SUCCESSFULLY FINISHED")


if __name__ == "__main__":
   main(sys.argv[1:])
