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

  update analysis.sh and follow instructions given in this bash file


TODO:
 - Submission formats and compression are highly variable. Although only two general underlying formats have been used, various different packing/archiving routines are used. 

 - Detailed instructions for submitters
    -> only single level in compressed files

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


# Basic MARTAS Telegram logging configuration for IMBOT manager
logpath = '/var/log/magpy/imbot.log'
notifictaion = {}
name = "IMBOT"

# TODO list
# 1. add a method to check level directory (as last job)
#    rename all level files from level1_underreview.md, level2_underreview.md to level1.md, level2.md
#    if no changes occured within 3 months

partialcheck_v1 = {
		'IMOS-01' : 'Time-stamp accuracy (centred on the UTC second): 0.01s',
		'IMOS-02' : 'Phase response: Maximum group delay: ±0.01s',
		'IMOS-03' : 'Maximum filter width: 25 seconds',
		'IMOS-04' : 'Instrument amplitude range: ≥±4000nT High Lat., ≥±3000nT Mid/Equatorial Lat.',
		'IMOS-05' : 'Data resolution: 1pT',
		'IMOS-06' : 'Pass band: DC to 0.2Hz',
		'IMOS-11' : 'Noise level: ≤100pT RMS',
		'IMOS-12' : 'Maximum offset error (cumulative error between absolute observations): ±2. 5 nT',
		'IMOS-13' : 'Maximum component scaling plus linearity error: 0.25%',
		'IMOS-14' : 'Maximum component orthogonality error: 2mrad',
		'IMOS-15' : 'Maximum Z-component verticality error: 2mrad',
		'IMOS-21' : 'Noise level: ≤10pT/√Hz at 0.1 Hz',
		'IMOS-22' : 'Maximum gain/attenuation: 3dB',
		'IMOS-31' : 'Minimum attenuation in the stop band (≥ 0.5Hz): 50dB',
		'IMOS-41' : 'Compulsory full-scale scalar magnetometer measurements with a data resolution of 0.01nT at a minimum sample period of 30 seconds',
		'IMOS-42' : 'Compulsory vector magnetometer temperature measurements with a resolution of 0.1°C at a minimum sample period of one minute'
		}

IMAGCDFKEYDICT = {     'FormatDescription':'DataFormat', 
                       'IagaCode':'StationID', 
                       'ElementsRecorded':'DataComponents', 
                       'ObservatoryName':'StationName',
                       'Latitude':'DataAcquisitionLatitude',
                       'Longitude':'DataAcquisitionLongitude',
                       'Institution':'StationInstitution',
                       'VectorSensOrient':'DataSensorOrientation',
                       'TermsOfUse':'DataTerms',
                       'UniqueIdentifier':'DataID',
                       'ParentIdentifiers':'SensorID',
                       'ReferenceLinks':'StationWebInfo',
                       'FlagRulesetType':'FlagRulesetType',
                       'FlagRulesetVersion':'FlagRulesetVersion',
                       'StandardLevel':'DataStandardLevel',
                      }



def GetUploadInformation(sourcepath, checkrange = 2, obslist = [],excludeobs=[]):
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
        print (obslist)
        storage = {}
        logdict = {}
        for root, dirs, files in os.walk(sourcepath):
          level = root.replace(sourcepath, '').count(os.sep)
          if (len(obslist) > 0 and root.replace(sourcepath, '')[1:4] in obslist) or len(obslist) == 0:
            if (len(excludeobs) > 0 and not root.replace(sourcepath, '')[1:4] in excludeobs) or len(excludeobs) == 0:
              if level == 1:
                print (root)
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
                    # only if latest file is at least "checkrange" hours old
                    if datetime.utcfromtimestamp(youngest) < datetime.utcnow()-timedelta(hours=checkrange):
                        # check file extensions ... and amount of files (zipped, cdf, sec)
                        # firstly remove txt, par and md from list (meta.txt contain updated parameters)
                        extlist = [el for el in extlist if not el in ['.txt', '.md']]
                        amount = len(files)
                        typ = max(extlist,key=extlist.count)
                        if typ in ['.zip', '.gz', '.tgz', '.tar.gz', '.tar', '.cdf', '.sec']:
                            parameter = {'amount': amount, 'type': typ, 'lastmodified': youngest, 'obscode': obscode}
                            storage[root] = parameter
                        else:
                            logdict[root] = "Found unexpected data type '{}'".format(typ)
                    else:
                        logdict[root] = "Uploaded recently - eventually not finished"
              elif level > 1:
                logdict[root] = "Found subdirectories - ignoring this folder"

        return storage, logdict


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
        print (obslist)
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
                    print (datetime.utcfromtimestamp(youngest), datetime.utcnow()-timedelta(hours=checkrange))
                    # only if latest file is at least "checkrange" hours old
                    if datetime.utcfromtimestamp(youngest) < datetime.utcnow()-timedelta(hours=checkrange):
                        # check file extensions ... and amount of files (zipped, cdf, sec)
                        # firstly remove txt, par and md from list (meta.txt contain updated parameters)
                        print (extlist)
                        extlist = [el for el in extlist if not el in ['.txt', '.md']]
                        amount = len(files)
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
                        logdict[root] = "Uploaded recently - eventually not finished"
              elif level > 1:
                logdict[root] = "Found subdirectories - ignoring this folder"

        return storage, logdict


def CopyTemporary(pathsdict, tmpdir="/tmp", logdict={}):
        """
        DESCRIPTION:
            copy files to temporary directory
            zipped files and tar archives will be extracted
        """

        for element in pathsdict:
            condict = {}
            para = pathsdict[element]
            newdir = os.path.join(tmpdir, 'raw', para.get('obscode'))

            #para['temporaryfolder'] = newdir

            if not os.path.exists(newdir):
                os.makedirs(newdir)

            for fname in os.listdir(element):
                src = os.path.join(element,fname)
                dst = os.path.join(newdir,fname)
                print ("Copying to temporary folder:", fname)
                if fname.endswith('.zip') or fname.endswith('.ZIP'):
                    try:
                        with zipfile.ZipFile(src, 'r') as zip_ref:
                            zip_ref.extractall(newdir)
                        condict[fname] = "unzipped"
                    except:
                        print ("ZIP file problem - trying 7z")
                        try:
                            unzip = "7z x {} -y -o{}".format(src,newdir)
                            print ("Running:", unzip)
                            os.system(unzip)
                            condict[fname] = "unzipped"
                        except:
                            logdict[element] = "Problem with zip file {}".format(fname)
                            print ("endless ZIP file problem")
                elif fname.endswith(".tar.gz") or fname.endswith(".TAR.GZ") or fname.endswith(".tgz") or fname.endswith(".TGZ"):
                    with tarfile.open(src, "r:gz") as tar:
                        tar.extractall(newdir)
                    condict[fname] = "unzipped and tar extracted"
                elif fname.endswith(".tar") or fname.endswith(".TAR"):
                    with tarfile.open(src, "r:") as tar:
                        tar.extractall(newdir)
                    condict[fname] = "tar extracted"
                else:
                    if not os.path.isdir(src):
                        # eventually use a filter method here like "if not fname in []"
                        try:
                            copyfile(src, dst)
                            condict[fname] = "file copied"
                        except:
                            condict[fname] = "copying file failed"


            logdict[element] = condict
            logdict['temporaryfolder'] = newdir

        return logdict


def WriteMemory(memorypath, memdict):
        """
        DESCRIPTION
             write memory
        """
        try:
            with open(memorypath, 'w') as outfile:
                json.dump(memdict, outfile)
        except:
            return False
        return True


def ReadMemory(memorypath):
        """
        DESCRIPTION
             read memory
        """
        memdict = {}
        if os.path.isfile(memorypath):
            print ("Reading memory: {}".format(memorypath))
            with open(memorypath, 'r') as file:
                memdict = json.load(file)
        else:
            print ("Memory path not found - please check (first run?)")
        print ("Found in Memory: {}".format([el for el in memdict]))
        return memdict

def ReadMetaData(sourcepath, filename = "meta*.txt"):
        """
        DESCRIPTION
             read additional metainformation for the specific observatory
        """
        def KeyConvert(key):
            magpykey = IMAGCDFKEYDICT.get(key,key)
            return magpykey

        newhead = {}
        metafilelist = glob.glob(os.path.join(sourcepath,filename))
        #print (os.path.join(sourcepath,filename))
        print ("Loading meta file:", metafilelist, os.path.join(sourcepath,filename))

        if len(metafilelist) > 0:
            if os.path.isfile(metafilelist[0]):
                with open(metafilelist[0], 'r') as infile:
                    for line in infile:
                        if not line.startswith('#'):
                            if line.find(" : ") > 0 or line.find("\t:\t") > 0 or line.find(" :\t") > 0 or line.find("\t: ") > 0:
                                paralist = line.replace(" ","").split(":")
                                # convert paralist [0] to MagPy keys
                                key = KeyConvert(paralist[0].strip())
                                try:
                                    newhead[key] = paralist[1].strip()
                                except:
                                    pass
        return newhead

def GetNewInputs(memory,newdict, notification={}):
        """
        DESCRIPTION
            will return a dictionary with key/value pairs from dir analysis
            which are not in memory
        """
        # newly uploaded
        newlist = []
        tmp = {k:v for k,v in newdict.items() if k not in memory}
        for key in tmp:
            newlist.append(key)
        # newly uploaded and updated
        updatelist = []
        C = {k:v for k,v in newdict.items() if k not in memory or v != memory[k]}
        for key in C:
            if not key in newlist:
                updatelist.append(key)
        notification['New Uploads'] = newlist
        notification['Updated data'] = updatelist

        return C, notification


def GetMonths(sourcepath, addinfo="/tmp", repdict={}):
        """
        DESCRIPTION:
            Reads data files with magpy, perform basic anaylsis and finally export data as ImagCDF
        PARAMETER:
            addinfo contains a link to additional meta information (e.g. provided on GITHUB, webpage, file, etc)
        """
        datelist = []
        # test whether sourcepath exists
        if not os.path.exists(sourcepath):
            print ("Path {} not existing".format(sourcepath))
            return [],repdict
        # need year for that
        # firstly read one file and extract year
        included_extensions = ['sec','SEC', 'cdf', 'CDF', 'gz', 'zip']
        validfilenames = [fn for fn in os.listdir(sourcepath) if any(fn.endswith(ext) for ext in included_extensions)]
        # Delete all files with invalid names?
        try:
            testfile = os.path.join(sourcepath,validfilenames[0])
        except:
            repdict["Readability"] = "No test file found - data could not be extracted?"
            return [], repdict

        repdict["Readability test file"] = testfile
        repdict["Readability"] = "OK"
        try:
            data = read(testfile)
        except:
            repdict["Readability"] = "Error when accessing file"
            return [],repdict

        sr = data.samplingrate()
        header = data.header
        repdict["Data format"] = header.get('DataFormat')
        if sr > 1.2:
            repdict["Readability"] = "Found wrong sampling rate of {}".format(sr)
        if data.length()[0] > 0:
            st, et = data._find_t_limits()
            year = et.year
            repdict["Year"] = year
            s = datetime(year,1,1)
            e = datetime(year+1,1,1)
            datelist = [[(datetime(s.year, s.month, 1)-timedelta(days=1)).strftime('%Y-%m-%d'), (datetime(s.year, s.month, 1) + relativedelta(months=1)+timedelta(days=1)).strftime('%Y-%m-%d')]]
            while s + timedelta(days=32) < e:
                s += timedelta(days=32)
                datelist.append( [(datetime(s.year, s.month, 1)-timedelta(days=1)).strftime('%Y-%m-%d'), (datetime(s.year, s.month, 1) + relativedelta(months=1)+timedelta(days=1)).strftime('%Y-%m-%d')] )
                s = s.replace(day=1)
        else:
            repdict["Readability"] = "Obtained empty DataStream structure"

        return datelist, repdict


def ReadMonth(sourcepath, starttime, endtime, logdict={}, updateinfo={}, optionalheads=['StationWebInfo', 'DataTerms', 'DataReferences']):
        """
        DESCRIPTION:
            reading one month of data and checking contents
        """
        metainfo = {}
        issues = {}
        improvements = {}
        warning = {}   # warnings are included and marked too-be-checked in summaries for data checkers for level 3 acceptance 
        #print ("Reading data from {} to {}".format(starttime,endtime))
        st = datetime.strptime(starttime,'%Y-%m-%d')+timedelta(days=1)
        et = datetime.strptime(endtime,'%Y-%m-%d')-timedelta(days=1)
        days = int(date2num(et) - date2num(st))
        expectedcount = days*24.*3600.
        #print ("Exporting data from {} to {}".format(st,et))
        try:
            data = read(os.path.join(sourcepath,'*'),starttime=starttime, endtime=endtime)
        except:
            data = DataStream()
        data = data.trim(starttime=st,endtime=et)
        if data.length()[0] > 1:
            cntbefore = data.length()[0]
            data = data.get_gaps()
            cntafter = data.length()[0]
            st, et = data._find_t_limits()
            effectivedays = int(date2num(et) - date2num(st))+1
            ### Try to load any additional meta information provided in file meta_obscode.txt
            newmeta = ReadMetaData(sourcepath)
            if len(newmeta) > 0:
                print ("Observatory provided additional meta information: {}".format(newmeta))
                for key in newmeta:
                   print ("Appending new meta info")
                   data.header[key] = newmeta[key]

            #print ("Datalimits from {} to {}".format(st,et))
            logdict['Datalimits'] = [st,et]
            logdict['N'] = data.length()[0]
            logdict['Leap second update'] = data.header.get('DataLeapSecondUpdated')
            logdict['Filled gaps'] = cntafter-cntbefore
            logdict['Difference to expected amount'] = expectedcount-cntafter
            logdict['Level'] = 2
            sr = data.samplingrate()
            logdict['Samplingrate'] = '{} sec'.format(sr)
            #print ("Expected amount", expectedcount)
            #print ("Expected", effectivedays, cntafter)
            if not expectedcount-cntafter == 0:
                # Allow a confirmation in newmeta to indicate that missing data is not available and thus does not need to be considered for monthly file generation - but keep issue
                # Example BDV2016 - the submitted files apparently repeat the same dates each month...
                if newmeta.get('MissingData','') in ['confirmed','Confirmed','confirm']:
                    logdict['Missing data'] = 'confirmed as missing by submitter'
                else:
                    logdict['Level'] = 1
                    issues['MissingData'] = 'Amount of data points {} does not correspond to the expected amount {}'.format(cntafter,expectedcount)
            if (effectivedays*24*3600) < cntafter:
                # apparently more data than expected for coverage (duplicates)
                logdict['Level'] = 0
                issues['Data coverage'] = 'Check data files for duplicates and correct coverage'
            if not sr == 1:
                logdict['Level'] = 0
                issues['Samplingrate'] = 'Found sampling rate of {} sec, expected is 1 sec'.format(sr)
            for head in IMAGCDFMETA:
                if not head == 'DataReferences': # TODO check that
                    value = data.header.get(head,'')
                    if value == '':
                        metainfo[head] = 'missing'
                        if not head in optionalheads:
                            issues[head] = 'header {} missing'.format(head.replace("Data","").replace("Sensor","").replace("Station","") )
                            if not logdict.get('Level') == 0:
                                logdict['Level'] = 1
                        else:
                            improvements[head] = 'provide information on {}'.format(head.replace("Data","").replace("Sensor","").replace("Station","") )
                    else:
                        metainfo[head] = value
        else:
            #if newmeta.get('MissingData','') in ['confirmed','Confirmed','confirm']:
            #    logdict['Missing data'] = 'confirmed as missing by submitter'
            #else:
            logdict['Level'] = 0
            issues['Data coverage'] = 'Check data files - data files missing?'

        logdict['Header'] = metainfo
        logdict['Issues'] = issues
        #logdict['Warnings'] = warnings
        logdict['Improvements'] = improvements

        return data, logdict


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


def CheckStandardLevel(data, logdict={}, partialcheck=partialcheck_v1):
        """
        DESCRIPTION
            extracting Standard levels as required from ImagCDF and creating a table.
            Some contents will be checked 

        STANDARD LEVELS
            as contained in variable partial
            One-second Data: Specifications in the Pass Band [DC to 8mHz (120s)]
            IMOS-01  Time-stamp accuracy (centred on the UTC second): 0.01s
            IMOS-02  Phase response: Maximum group delay: ±0.01s
            IMOS-03  Maximum filter width: 25 seconds
            IMOS-04  Instrument amplitude range:     ≥±4000nT High Lat., ≥±3000nT Mid/Equatorial Lat.
            IMOS-05  Data resolution: 1pT
            IMOS-06  Pass band: DC to 0.2Hz
            IMOS-11  Noise level: ≤100pT RMSIMOS-12Maximum offset error (cumulative error between absolute observations): ±2. 5 nT
            IMOS-13  Maximum component scaling plus linearity error: 0.25%
            IMOS-14  Maximum component orthogonality error: 2mrad
            IMOS-15  Maximum Z-component verticality error: 2mrad
            One-second Data: Specifications in the Pass Band [8mHz (120s) to 0.2Hz]
            IMOS-21  Noise level:                        ≤10pT/√Hz at 0.1 Hz
            IMOS-22  Maximum gain/attenuation: 3dB
            One-second Data: Specifications in the Stop Band [≥ 0.5 Hz]
            IMOS-31  Minimum attenuation in the stop band (≥ 0.5Hz): 50dB
            One-second Data: Auxiliary measurements:
            IMOS-41  Compulsory full-scale scalar magnetometer measurements with a data resolution of 0.01nT at a minimum sample period of 30 seconds.
            IMOS-42  Compulsory vector magnetometer temperature measurements with a resolution of 0.1°C at a minimum sample period of one minute

        VARIABLES
            data    (MagPy DataStream) 	: data and meta information 
            partiacheck   (dict) 	: contains Standard levels and their description 
            logdict	(dict)		: logdict with Issue information

        RETURN
            table with (list) with partial standard description and whether these points are met/considered
            logdict with an updated Issue subdictionary 
        """
        issuedict = {}
        issuedict=logdict.get('Issues',{})
        tablelist = []
        head = data.header
        if head.get('DataStandardLevel','') in ['full','Full','FULL']:
            # all criteria have been confirmed
            for key in partialcheck:
                tableline = []
                tableline.append(key)
                tableline.append(partialcheck.get(key))
                if key == 'IMOS41' and (logdict.get('F') in ['None',''] or logdict.get('F').startswith('found no')):
                    tableline.append('confirmed but invalid')
                    issuedict['StandardLevel - IMOS41'] = 'criteria not met' 
                elif key == 'IMOS42' and logdict.get('T') in ['None','']:
                    tableline.append('confirmed but invalid')
                    issuedict['StandardLevel - IMOS42'] = 'criteria not met' 
                else:
                    tableline.append('validity confirmed by submitter')
                tablelist.append(tableline)
        elif head.get('DataStandardLevel','') in ['partial','Partial','PARTIAL']:
            #print ("Partial descriptions found:", head)
            partialvals = head.get('DataPartialStandDesc')
            for key in partialcheck:
                tableline = []
                tableline.append(key)
                tableline.append(partialcheck.get(key))
                try:
                    if partialvals.find(key) > -1:
                        tableline.append('validity confirmed by submitter')
                        if key == 'IMOS41' and (logdict.get('F') in ['None',''] or logdict.get('F').startswith('found no')):
                            tableline.append('confirmed but invalid')
                            issuedict['StandardLevel - IMOS41'] = 'criteria not met' 
                        elif key == 'IMOS42' and logdict.get('T') in ['None','']:
                            tableline.append('confirmed but invalid')
                            issuedict['StandardLevel - IMOS42'] = 'criteria not met' 
                    else:
                        tableline.append('not met as confirmed by submitter')
                except:
                    tableline.append('information missing')
                    issuedict['PartialStandDesc'] = 'PartialStandDesc required for partial - see TN8: 4.7 Relevant data standards' 
                tablelist.append(tableline)
        else:
            issuedict['StandardLevel'] = 'StandardLevel full or partial - see TN8: 4.7 Relevant data standards' 
            issuedict['PartialStandDesc'] = 'PartialStandDesc required for partial - see TN8: 4.7 Relevant data standards' 
            for key in partialcheck:
                tableline = []
                tableline.append(key)
                tableline.append(partialcheck.get(key))
                tableline.append('not provided')
                tablelist.append(tableline)

        logdict['Issues'] = issuedict

        return tablelist, logdict


def ExtractEMails(path):
        """
        DESCRIPTION
            read text file in path and extract all e-mail addresses in this file
        APPLICATION
            apply on readme.obscode to get e-mails from observers to send report to
        """
        mailaddresslist = []

        regex = re.compile(("([a-z0-9!#$%&'*+\/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+\/=?^_`"
                            "{|}~-]+)*(@)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(\.|"
                            "\sdot\s))+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)"))

        try:
            fulltext = ''
            if os.path.isfile(path):
                with open(path, 'r', encoding="latin-1") as infile:
                    fulltext = infile.read().lower()

            mailaddresslist = [email[0] for email in re.findall(regex, fulltext) if not email[0].startswith('//')]
        except:
            print (" -> Could not extract mails from {} - permission problem?".format(path))

        return mailaddresslist

def CheckDiffs2Minute(data, logdict, minutesource='', obscode='',daterange=[]):
        """
        DESCRIPTION
            Compares the definitive one second data product to one minute
            Please note: differences between the two data products need to be large
            to trigger an automatic issue. The report, however, will contain a summary
            of any questinable differences.
        PARAMETER
            minutesorce needs to be the basedirectory of one mintue data
            this source is scanned for subdirctories with OBSCODE as name
        PROCESSING
            - one second data will be filtered using IM recommended standards
            - filtered on second will then be subtracted from one minute data
            - differences are then analyzed
            - only vector components (x,y,z) are considered
        CHECKING
            - maximal difference amplitudes for each month
            - average difference and its distribtion
        EXPECTED VALUES
            1. average difference needs to be zero, its distribution below the "numerical noise"
            (numerial noise arises from the 0.1 nT resolution if IAF data and the < 0.01 nT 
             resolution of one second data and its filtered product; ) 
            2. maximal amplitudes shoud be in the order of the numerical noise
        CONSEQUENCES
            If the mean difference is significantly larger than zero, both for daily means and monthly
            mean, then both data sets are termed "different" and the submitting institue needs to clarify
            which one is definitive (data remains on level 1)
            Individual difference spikes and larger deviations indicate that one or a combination 
            of different filtering procedures, different outlier treatment, gap treatment, baseline methods,
            or different instruments with other noise characteristics are used for the data sets.
            The average differences are listed in the report, to be considered for level 3 evaluation.
        """

        mindatadict = {}
        issuedict = {}
        warningdict = {}
        issuedict=logdict.get('Issues',{})
        warningdict=logdict.get('Warnings',{})
        logdict['Definitive comparison'] = 'definitive one-minute not available or not readable'

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

        mails = ExtractEMails(pathname(minutesource,obscode,typ='readme'))
        #print (mails)
        logdict['Contact'] = mails

        if minutesource:
            try:
                print ("Loading minute data: ", pathname(minutesource,obscode), daterange[0], daterange[1])
                mindata = read(pathname(minutesource,obscode),starttime=daterange[0], endtime=daterange[1])
                print (" ... success. Got {} data points".format(mindata.length()[0]))
            except:
                print ("Problem when reading minute data")
                logdict['Definitive comparison'] = 'definitive one-minute not available or not readable'
                mindata = DataStream()
        if minutesource and mindata.length()[0] > 1:
            secdata = data.copy()
            highresfilt = secdata.filter(missingdata='iaga')
            diff = subtractStreams(highresfilt,mindata,keys=['x','y','z'])
            #mp.plot(diff)
            print ("  -> diff calculated")
            xd, xdst = diff.mean('x',std=True)
            yd, ydst = diff.mean('y',std=True)
            zd, zdst = diff.mean('z',std=True)
            try:
               xa = diff.amplitude('x')
               ya = diff.amplitude('y')
               za = diff.amplitude('z')
            except:
               print ("Problem determining amplitudes...")
               xa = 0.00
               ya = 0.00
               za = 0.00
            print ("  -> amplitudes determined")
            mindatadict['mean difference - x component'] = "{:.3} nT".format(xd)
            mindatadict['mean difference - y component'] = "{:.3} nT".format(yd)
            mindatadict['mean difference - z component'] = "{:.3} nT".format(zd)
            mindatadict['stddev of difference - x component'] = "{:.3} nT".format(xdst)
            mindatadict['stddev of difference - y component'] = "{:.3} nT".format(ydst)
            mindatadict['stddev of difference - z component'] = "{:.3} nT".format(zdst)
            mindatadict['amplitude of difference - x component'] = "{:.3} nT".format(xa)
            mindatadict['amplitude of difference - y component'] = "{:.3} nT".format(ya)
            mindatadict['amplitude of difference - z component'] = "{:.3} nT".format(za)
            print ("  -> dictionary written")
            if max(xd,yd,zd) > 0.3:
                warningdict['Definitive differences'] = 'one-minute and one-second data differ by more than 0.3 nT in monthly average' 
                logdict['Definitive differences'] = 'One-minute and one-second data differ by more than 0.3 nT in a monthly average' 
            if max(xa,ya,za) < 0.12:
                logdict['Definitive comparison'] = 'excellent agreement between definitive one-minute and one-second data products' 
            elif max(xa,ya,za) <= 0.3:
                logdict['Definitive comparison'] = 'good agreement between definitive one-minute and one-second data products' 
            elif max(xa,ya,za) > 0.3 and max(xa,ya,za) <=5:
                logdict['Definitive comparison'] = 'small differences in peak amplitudes between definitive one-minute and one-second data products observed'
            elif max(xa,ya,za) > 5:
                warningdict['Definitive comparison'] = 'Large amplitude differences between definitive one-minute and one-second data products' 
                logdict['Definitive comparison'] = 'Large amplitude differences between definitive one-minute and one-second data products' 

        logdict['Warnings'] = warningdict
        logdict['DefinitiveStatus'] = mindatadict

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

def UpdateTable(tablelist, readdict):
        # get noiselevel
        lower95noiselevelbound = (float(readdict.get('Noiselevel')) - 2 * float(readdict.get('NoiselevelStdDeviation')))*1000.
        try:
            monthdict = readdict.get('1')
            warndict = monthdict.get('Warnings')
        except:
            warndict = {}
        if lower95noiselevelbound > 100:
            comment =  " - IMBOT indicates failure"
        else:
            comment =  " - IMBOT indicates success"
        newtablelist = []
        for row in tablelist:
            if row[0] == 'IMOS-11':
                if row[2].startswith('validity') and comment.endswith('failure'):
                    #print ("Add a waring that the noise level exceeds the IM criteria and eventually update info in tablelist")
                    warndict['Noiselevel'] = "Noiselevel apparently exceeds 100 pT"
                    try:
                        monthdict['Warnings'] = warnings
                        readdict['1'] = monthdict
                    except:
                        pass
                row[2] += comment
            newtablelist.append(row)

        return newtablelist


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


def ExportMonth(destinationpath, data, logdict={}):
        """
        DESCRIPTION
            exporting final data to an monthly IMAGCDF file 
        """
        success = True
        print ("Writing IMAGCDF file")
        try:
            success = data.write(destinationpath,coverage='month',format_type='IMAGCDF')
            del data
        except:
            sucess = False
        if success:
            print (" ... successful")
        return success


def CreateDailyList(startdate,enddate, output='datetime'):
        daylist = [startdate + timedelta(days=el) for el in range(1, 40) if startdate+timedelta(days=el+1)<enddate]
        if not output=='datetime':
            daylist = [el.strftime('%Y-%m-%d') for el in daylist]
        return daylist



def WriteReport(destinationpath, parameterdict={}, reportdict={}, logdict={}, tablelist=[]):
        """
        DESCRIPTION
            Write a data report with basic information on submitted data set and possible issues
            The report will be written in markup language into the destination directory.
            The name of the report depends on the suggested data level.
            level0.txt (if reading data failed)
            level1*.txt (if reading was successful, but basic information is missing)
            level2*.txt (if reading was successful, and level 2 criteria are met)
        RETURN
            will return the determined level
        """

        def merge_dicts(*dict_args):
            """
            Given any number of dictionaries, shallow copy and merge into a new dict,
            precedence goes to key value pairs in latter dictionaries.
            """
            result = {}
            for dictionary in dict_args:
                result.update(dictionary)
            return result

        """
        def findDiff(d1, d2, path=""):
            for k in d1:
                if (k not in d2):
                    print (path, ":")
                    print (k + " as key not in d2", "\n")
                else:
                    if type(d1[k]) is dict:
                        if path == "":
                            path = k
                        else:
                            path = path + "->" + k
                        findDiff(d1[k],d2[k], path)
                    else:
                        if d1[k] != d2[k]:
                            print (path, ":")
                            print (" - ", k," : ", d1[k])
                            print (" + ", k," : ", d2[k])
        """

        obscode = parameterdict.get('obscode')
        #check reportdict and obtain main
        levellist = []
        issuelist = []
        improvelist = []
        warninglist = []
        #print ("Report", reportdict)
        #print ("Parameter", parameterdict)

        # 1. Extract the monthly dictionaries
        monthlydict = {}
        generaldict = {}
        definitivedict = {}
        headerdict = {}
        issuesummary = {}
        improvementsummary = {}
        warningsummary = {}
        print ("Running WriteReport")
        for month in reportdict:
            if month in ['1','2','3','4','5','6','7','8','9','10','11','12']:
                monthlydict[month] = reportdict[month]
                levellist.append(reportdict[month].get("Level"))
                warningdict = {}
                issuedict = {}
                improvedict = {}
                issuedict = reportdict[month].get("Issues")
                improvedict = reportdict[month].get("Improvements")
                warningdict = reportdict[month].get("Warnings")
                if not improvedict:
                    improvedict = {}
                if not warningdict:
                    warningdict = {}
                print ("   Warning messages for month {}: {}".format(month, warningdict))
                headerdict = reportdict[month].get("Header")
                for issue in issuedict:
                    # get the issue and add the months
                    #print ("Got here", issue)
                    validmonths = issuesummary.get(issuedict.get(issue),[])
                    validmonths.append(month)
                    #print ("Current months", validmonths)
                    issuesummary[issuedict[issue]] = validmonths
                for improve in improvedict:
                    # get the issue and add the months
                    validmonths = improvementsummary.get(improvedict.get(improve),[])
                    #print ("Current", month, validmonths, improvedict.get(improve))
                    validmonths.append(month)
                    #print ("Current months", validmonths)
                    improvementsummary[improvedict[improve]] = validmonths
                for warn in warningdict:
                    # get the issue and add the months
                    validmonths = warningsummary.get(warningdict.get(warn),[])
                    validmonths.append(month)
                    warningsummary[warningdict[warn]] = validmonths
                # Establish a monthly table with all information
                definitivedict[month] = reportdict[month].get("DefinitiveStatus")
            else:
                generaldict[month] = reportdict[month]

        if len(levellist) > 0:
            level = min(levellist)
        else:
            level = 0

        print ("   ISSUES", issuesummary)
        print ("   IMPROVEMENTS", improvementsummary)
        print ("   WARNINGS SUMMARY:", warningsummary)
        #print ("Generaldict", generaldict)

        for issue in issuesummary:
            months = issuesummary[issue]
            issuelist.append("{} | {}\n".format(issue,",".join(months)))

        for improve in improvementsummary:
            months = improvementsummary[improve]
            improvelist.append("{} | {}\n".format(improve,",".join(months)))

        for warn in warningsummary:
            months = warningsummary[warn]
            warninglist.append("{} | {}\n".format(warn,",".join(months)))

        text = ["# {} - Level {}\n\n# Analysis report for one second data from {}\n\n".format(obscode,level,obscode)]
        text.append("### Issues to be clarified for level 2:\n")
        if len(issuelist) > 0:
             text.append("\n")
             text.append("Issue | Observed in months\n")
             text.append("----- | -----\n")
             for issue in issuelist:
                 text.append(issue)
        else:
             text.append("\nNone\n")

        text.append("\n### Possible improvements (not obligatory):\n")
        if len(improvelist) > 0:
             text.append("\n")
             text.append("Improvements | Applicable for months\n")
             text.append("----- | -----\n")
             for improve in improvelist:
                 text.append(improve)
        else:
             text.append("\nNone\n")

        text.append("\n\n### ImagCDF standard levels as provided by the submitter\n\n")
        text.append("StandardLevel | Description | Validity\n--------- | --------- | ---------\n")
        for element in tablelist:
            text.append("{} | {} | {}\n".format(element[0],element[1],element[2]))

        if len(warninglist) > 0 and level >= 1:
            text.append("\n### Too be considered for final evaluation\n")
            text.append("\n")
            text.append("Level 3 considerations | Observered \n")
            text.append("----- | -----\n")
            for warn in warninglist:
                text.append(warn)

        text.append("\n\n### Provided Header information\n\n")
        if len(headerdict) > 0:
             text.append("\n")
             text.append("Header | Content\n")
             text.append("----- | -----\n")
             for head in headerdict:
                text.append("{} | {}\n".format(head,str(headerdict[head]).strip()))
        else:
             text.append("\nNone\n")

        text.append("\n\n### Basic analysis information\n\n")
        #for month in monthlydict:
        #    # Create a monthly table with issues
        #    parameterdict = merge_dicts(parameterdict,monthlydict[month])
        for key in parameterdict:
            # if not key a dictionary
            if not isinstance(parameterdict[key],dict):
                text.append("* {}  :  {}\n".format(key,parameterdict[key]))

        for key in generaldict:
            # if not key a dictionary
            if not isinstance(generaldict[key],dict):
                if key.startswith('Noiselevel'):
                    text.append("* {}  :  {:.0f} pT\n".format(key,float(generaldict[key])*1000.))
                else:
                    text.append("* {}  :  {}\n".format(key,generaldict[key]))
        #TODO: add daylist

        text.append("\n\n### Details on monthly evaluation\n\n")
        for month in definitivedict:
            defdi = definitivedict.get(month)
            monthly = monthlydict.get(month)
            #print (monthly)
            text.append("\nMonth {} | Value \n".format(month))
            text.append("------ | ----- \n".format(month))
            for el in defdi:
                text.append("{} | {}\n".format(el,defdi[el]))
            for el in monthly:
                if not isinstance(monthly[el],dict):
                    text.append("{} | {}\n".format(el,str(monthly[el]).strip()))


        # delete any previous level description
        def removeFilesByMatchingPattern(dirPath, pattern):
            listOfFilesWithError = []
            for parentDir, dirnames, filenames in os.walk(dirPath):
                for filename in fnmatch.filter(filenames, pattern):
                    try:
                        os.remove(os.path.join(parentDir, filename))
                    except:
                        print("Error while deleting file : ", os.path.join(parentDir, filename))
                        listOfFilesWithError.append(os.path.join(parentDir, filename))
            return listOfFilesWithError

        removeFilesByMatchingPattern(destinationpath, "level*.txt")

        # path might not exist for level0 data
        if not os.path.exists(destinationpath):
            os.makedirs(destinationpath)

        filename = os.path.join(destinationpath, "level{}_underreview.txt".format(level))
        with open(filename, 'w') as out:
            out.write("".join(text))

        # Now also construct an update file for new meta information
        issuesum = {}
        for month in reportdict:
            if month in ['1','2','3','4','5','6','7','8','9','10','11','12']:
                issuedict = reportdict[month].get("Issues")
                issuesum = merge_dicts(issuesum,issuedict)
        if len(issuesum) > 0:
            WriteMetaUpdateFile(os.path.join(destinationpath,"meta_{}.txt".format(obscode)), issuesum)

        print ("... WriteReport finished")
        return level


def WriteMetaUpdateFile(destination, dictionary):
        """
        DESCRIPTION
            prepare a correction sheet.
            submitters can edit this sheet and update missing information
        """
        print ("WRITING correction sheet")

        def KeyConvert(magpykey):
            try:
                key = (list(IMAGCDFKEYDICT.keys())[list(IMAGCDFKEYDICT.values()).index(magpykey)])
                return key
            except:
                return magpykey

        text = ['## Parameter sheet for additional or missing meta information\n',
                '## ------------------------------------------------------\n',
                '## Please provide "key : value" pairs as shown below.\n',
                '## The key need to correspond to the IMAGCDF key. Please\n',
                '## check out the IMAGCDF format description at INTERMAGNET\n',
                '## for details. Alternatively you can use MagPy header keys.\n',
                '## Values must not contain special characters or colons.\n',
                '## Enter "None" to indicate that a value is not available.\n',
                '## Comments need to start in new lines beginning with a\n',
                '## hash.\n',
                '## Please note - you can also provide optional keys here.\n',
                '## \n',
                '## Example:\n',
                '## Providing Partial standard value descriptions as requested:\n',
                '# StandardLevel  :  partial\n',
                '# PartialStandDesc  :  IMOS11,IMOS14,IMOS41\n\n\n']

        headlinedict = {'StandardLevel': '# Provide a valid standard level (full, partial), None is not accepted\n',
                        'PartialStandDesc' : '# If Standard Level is partial, provide a list of standards met\n',
                        'ReferenceLinks' : '# Reference to your institution (e.g. webaddress)\n',
                        'TermsOfUse' : '# Provide Terms of Use (e.g. creative common lisence)\n',
                        'MissingData' : '# If data is not available please confirm by MissingData  :  confirmed\n',
                       }

        for key in dictionary:
            if headlinedict.get(key,''):
                text.append("{}".format(headlinedict[key]))
            text.append("{}  :  {}\n\n".format(KeyConvert(key), dictionary[key]))
        try:
            with open(destination, 'w') as outfile:
                outfile.write("".join(text))
        except:
            return False
        return True


def GetConf(path):
    """
    Version 2020-10-28
    DESCRIPTION:
       can read a text configuration file and extract lists and dictionaries
    SUPPORTED:
       key   :    stringvalue                                 # extracted as { key: str(value) }
       key   :    intvalue                                    # extracted as { key: int(value) }
       key   :    item1,item2,item3                           # extracted as { key: [item1,item2,item3] }
       key   :    subkey1:value1;subkey2:value2               # extracted as { key: {subkey1:value1,subkey2:value2} }
       key   :    subkey1:value1;subkey2:item1,item2,item3    # extracted as { key: {subkey1:value1,subkey2:[item1...]} }
    """
    ok = True
    if ok:
        #try:
        config = open(path,'r')
        confs = config.readlines()
        confdict = {}
        for conf in confs:
            conflst = conf.split(':')
            if conf.startswith('#'):
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                conflst = conf.split(':')
                key = conflst[0].strip()
                value = conflst[1].strip()
                # Lists
                if value.find(',') > -1:
                    value = value.split(',')
                    value = [el.strip() for el  in value]
                try:
                    confdict[key] = int(value)
                except:
                    confdict[key] = value
            elif len(conflst) > 2:
                # Dictionaries
                if conf.find(';') > -1 or len(conflst) == 3:
                    ele = conf.split(';')
                    main = ele[0].split(':')[0].strip()
                    cont = {}
                    for el in ele:
                        pair = el.split(':')
                        # Lists
                        subvalue = pair[-1].strip()
                        if subvalue.find(',') > -1:
                            subvalue = subvalue.split(',')
                            subvalue = [el.strip() for el  in subvalue]
                        try:
                            cont[pair[-2].strip()] = int(subvalue)
                        except:
                            cont[pair[-2].strip()] = subvalue
                    confdict[main] = cont
                else:
                    print ("Subdictionary expected - but no ; as element divider found")
    #except:
    #    print ("Problems when loading conf data from file. Using defaults")

    return confdict


def GetDataChecker(obscode, path="/path/to/refereelist.cfg"):
        """
        DESCRIPTION
            determine a data checker for the Observatory defined by obscode.
        PARAMETER:
            path ideally should be the same as for mail.cfg
        RETURNS:
            two strings, a name and a email address
        """
        checker = ''
        checkermail = ''
        fallback = 'Max Mustermann'
        fallbackmail = 'max@mustermann.at'
        if not os.path.isfile(path):
            print ("DID NOT FIND REFEREE CONFIGURATION FILE")
            return fallback, fallbackmail
        checkdict = GetConf(path)
        for mail in checkdict:
            subdict = checkdict[mail]
            obslist = subdict.get('obslist',[])
            if obscode in obslist:
                checker = subdict.get('name','')
                checkermail = mail
            if len(obslist) == 0:
                fallback = subdict.get('name','')
                fallbackmail = mail
        if not checker == '' and not checkermail == '':
            return checker, checkermail
        else:
            return fallback, fallbackmail


def GetMailFromList(obscode, path="/path/to/mailinglist.cfg"):
        """
        DESCRIPTION
            locate any additional mailing addresses for obscode. Replace
            other mail addresses.
        PARAMETER:
            path ideally should be the same as for mail.cfg
        RETURNS:
            list with email address(es)
        """
        if not os.path.isfile(path):
            print ("DID NOT FIND MAILINGLIST CONFIGURATION FILE")
            return []
        obsdict = GetConf(path)
        maillist = obsdict.get(obscode,[])

        return maillist


def CreateMinuteMail(level, obscode, stationname='', year=2016, nameofdatachecker="Max Mustermann"):

        maintext =  "Dear data submitter,\n\nyou receive the following information as your e-mail address is connected to submissions of geomagnetic data products from {} observatory.\nYour one-minute data submission for {} has been automatically evaluated by IMBOT, an automatic data checker of INTERMAGNET.\n\nThe evaluation process resulted in\n\n".format(obscode, year)


        maintext += "LEVEL {}".format(level)

        if int(level) == 0:
            maintext += "    ISSUES to be resolved\n\n"
        else:
            maintext += "    READY for manual data checking\n\n"

        # TODO to be removed
        maintext += "!! Please note: this is just a preliminary test of an automatic evaluation routine. The following text is fictional, ratings are NOT related to any decision of INTERMAGNET. Text and reports are suggestions to be reviewed by the INTERMAGNET data commitee. !!\n\n"

        level0 = "Your data did not pass the automatic evaluation test. Please update your data submission.\nDetails can be found in the attached report. Please update your submission accordingly and perform a data check with checking tools provided by INTERMAGNET (link) before resubmission of your data set. If you need help please contact {}\n\n".format(nameofdatachecker)
        level1 = "Congratulations! A basic data analysis indicates that your submission is ready for final checking by IM officers. So far all tests have been perfomed automatically. Please check the attached report for details.\n\nYour data set has been assigned to an INTERMAGNET data checker for evaluation.\nYour data checker is {}.\nPlease note that INTERMAGNET data checkers perform all checks on voluntary basis beside their usual duties. So please be patient. The data checker will contact you if questions arise.\n\n".format(nameofdatachecker)
        level2 = "Congratulations!\n\nYour data fulfills all requirements for a final review. A level 2 data product is already an excellent source for high resolution magnetic information. Your data set has been assigned to an INTERMAGNET data checker for final evaluation regarding data quality.\nYour data checker is {}.\nPlease note that INTERMAGNET data checkers perform all check on voluntary basis beside their usual duties. So please be patient. The data checker will contact you if questions arise.\n\n".format(nameofdatachecker)

        if int(level) == 0:
            maintext += level0
        elif int(level) == 1:
            maintext += level1
        elif int(level) == 2:
            maintext += level2

        maintext += "If you have any questions regarding the evalutation process please check out the general instructions (https://github.com/INTERMAGNET/IMBOT/blob/master/README.md) or contact the IMBOT manager.\n\n"
        maintext += "\nSincerely,\n       IMBOT\n\n"


        if int(level) < 2:
            instructionstext = """
    -----------------------------------------------------------------------------------
    Important Links:

    check1min

    MagPy
                               """
            maintext += instructionstext.replace('OBSCODE',obscode)

        return maintext

def DOS_check1min(sourcepath, obscode, year=2020, winepath='/home/leon/.wine/drive_c/',logdict={}, updateinfo={}, optionalheads=['StationWebInfo', 'DataTerms', 'DataReferences'], debug= False):
    # requires wine

    sleeptime = 10

    src = sourcepath
    dst = os.path.join(winepath,'daten',obscode)
    # This creates a symbolic link on python in tmp directory
    if os.path.isdir(dst):
        os.unlink(dst)
    os.symlink(src, dst)

    curwd = os.getcwd()
    os.chdir(winepath)

    cmd = "wine start check1min.exe C:\\\\daten\\\\{} {} {} C:\\\\daten\\\\{}\\\\{}report{}.txt".format(obscode,obscode,year,obscode,obscode.lower(),year)
    print (cmd)
    import subprocess
    import time

    subprocess.call(cmd, shell=True)
    #proc = subprocess.Popen(cmd, cwd=winepath)

    os.chdir(curwd)
    time.sleep(sleeptime) # wait a while to finish analysis
    os.unlink(dst)


    attach = logdict.get('Attachment',[])
    attach.append(os.path.join(sourcepath,"{}report{}.txt".format(obscode.lower(),year)))
    logdict['Attachment'] = attach
    checklist = logdict.get('CheckList',[])
    checklist.append('check1min (dos) performed')
    logdict['CheckList'] = checklist
    logdict['Level'] = 1

    return logdict


def MagPy_check1min(sourcepath, obscode, logdict={}, updateinfo={}, optionalheads=['StationWebInfo', 'DataTerms', 'DataReferences'], debug= False):
    """
    DESCRIPTION:
        reading data and checking contents
    """

    issuelist = []

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
        mails = ExtractEMails(pathname(minpath,obscode,typ='readme'))
        #print (mails)
        logdict['Contact'] = mails
    except:
        issue = "Failed to extract an email address from README file"
        issuelist.append(issue)

    extension = 'BIN'
    #======== Checking presence readme.imo yearmean.imo imoyyyy.blv =======
    print ("======== Checking presence readme.imo yearmean.imo imoyyyy.blv =======")
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
        print ("Result", bincnt, blvcnt, addcnt)
        if bincnt == 12:
            print ("   Requested binary files are present")
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
        print ("Updating year")
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

    logdict['Issues'] = issuelist
    checklist = logdict.get('CheckList',[])
    checklist.append('basic MagPy test performed')
    logdict['CheckList'] = checklist

    return data, logdict


def ObtainEmailReceivers(logdict, obscode, mailinglist, referee, debug=False):

        managermail = ''
        # Create mailing list
        # -----------
        # Extract e-mail address from contact in README
        contacts = logdict.get('Contact',[])
        emails = contacts

        # if alternative email contacts are provided, then use those
        # read file with -e emails option - name: mailinglist.cfg
        alternativeemails = GetMailFromList(obscode, mailinglist)
        if debug:
            print (" -> Contacts: {}".format(contacts))
            print (" -> Alternative contacts: {}".format(alternativeemails))
        if not isinstance(alternativeemails, list):
            alternativeemails = [alternativeemails]
        if alternativeemails and len(alternativeemails) > 0:
            emails = alternativeemails

        manager = GetMailFromList('manager', mailinglist)
        if not isinstance(manager, list):
            manager = [manager]
        if len(manager) > 0:
            managermail = ",".join(manager)  # used for mails not in testobslist

        #print ("Mailing list looks like:", emails)
        if emails:
            # Email could be extracted from contact or from alternativelist
            if referee: # referee is determined by GetDataChecker
                emails.append(referee)
            if manager:
                for man in manager:
                    emails.append(man)
            # emails
            print (emails)
            # Remove Duplicates
            emails = list(set(emails))
            print (emails)
            email = ",".join(emails)
        else:
            emails = []
            # IMBOT managers are always informed
            for man in manager:
                emails.append(man)
            email = ",".join(emails)

        if debug:
            print (" -> Referee: {}".format(referee))
            print (" -> Manager: {}".format(managermail))
            print (" -> all receipients: {}".format(email))
            emails = []
            email = ''
            print (" Skipping all mail addresses and only sending to IMBOT administrator")
            admin = GetMailFromList('admin', mailinglist)
            if not isinstance(admin, list):
                admin = [admin]
            for ad in admin:
                emails.append(ad)
            email = ",".join(emails)
            manageremail = email
            print (" -> debug recipient: {}".format(email))


        return email, managermail


def CheckOneMinute(pathsdict, tmpdir="/tmp", destination="/tmp", logdict={}, selecteddayslist=[], testobslist=[], checklist=['default'], pathemails=None, mailcfg='', debug=False):
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
        readdict = {}
        loggingdict = {}
        loggingdict['Issues'] = []
        loggingdict['Level'] = None
        for element in pathsdict:
                print ("Starting analysis for {}".format(element))
                #try
                readdict = {}
                para = pathsdict.get(element)
                dailystreamlist = []
                loggingdict = {}
                tablelist = []
                datelist = []
                emails = None
                referee = None
                nameofdatachecker = ''
                sourcepath = os.path.join(tmpdir, 'raw', para.get('obscode'))
                destinationpath = os.path.join(destination, 'level', para.get('obscode'))
                readdict['Obscode'] = para.get('obscode')
                readdict['Sourcepath'] = sourcepath
                readdict['Destinationpath'] = destinationpath
                # get month list

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
                loggingdict = DOS_check1min(sourcepath,para.get('obscode'),year=readdict.get('Year'),updateinfo=updatedictionary,logdict=loggingdict, debug=debug)

                #print (loggingdict)
                #sys.exit()

                """
                    # - perform level test (delta f)
                    # -----------
                    if debug:
                        print ("Running delta F test")
                    loggingdict = DeltaFTest(mdata, loggingdict)
                    # - perform level test (standard descriptions)
                    # -----------
                    if debug:
                        print ("Running Standard level test")
                    tablelist, loggingdict = CheckStandardLevel(mdata, loggingdict)
                    # - perform level test (definitive status) - requires path to definitive minute values
                    # -----------
                    # is it possible to extract an e-mail address here?
                    if debug:
                        print ("Checking definitive status")
                    loggingdict = CheckDiffs2Minute(mdata, loggingdict, minutesource=pathminute, obscode=para.get('obscode'), daterange=[dates[0],dates[1]])
                    # extract some daily records
                    # -----------
                    if debug:
                        print ("Extracting quiet days")
                    daylist = CreateDailyList(datetime.strptime(dates[0],'%Y-%m-%d'), datetime.strptime(dates[1],'%Y-%m-%d'),output='text')
                    for day in selecteddayslist:
                        if day in daylist:
                            print ("Found a quiet day ({}) for power analysis - extracting information:".format(day))
                            dayst = DataStream()
                            dayar = mdata._select_timerange(starttime=day,endtime=datetime.strptime(day,'%Y-%m-%d')+timedelta(days=1))
                            dayst.ndarray = dayar
                            dayst.header = mdata.header
                            if dayst.length()[0] > 0:
                                dailystreamlist.append(dayar)
                                del dayar
                    # export data
                    # -----------
                    if debug:
                        print ("Exporting monthly ImagCDF files")
                    success = ExportMonth(destinationpath, mdata, logdict={})
                    # clear existing month
                """

                # Report
                # -----------------
                # Construct a detailed report with graphs from loggingdict and readdict and temporary graphs


                #if len(loggingdict.get('Issues')) > 0 and not loggingdict.get('Level') == 0:
                #        loggingdict['Level'] = 1
                readdict['MagPyVersion'] = magpyversion

                # perform noise analysis on selcted days
                # -----------
                if len(dailystreamlist) > 0:
                    readdict = PowerAnalysis(dailystreamlist, readdict)
                    # eventually update tablelist if noiselvel to large
                    tablelist = UpdateTable(tablelist, readdict)

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
                #level = WriteReport(destinationpath, para, readdict, logdict, tablelist=tablelist)
                level = loggingdict.get('Level')
                print ("-Asigning data checker")
                nameofdatachecker, referee = GetDataChecker(para.get('obscode').upper(),os.path.join(pathemails,"refereelist_minute.cfg"))
                print ("-Creating Mail")
                stationname = ''  # contained in readme - extract
                mailtext = CreateMinuteMail(level, para.get('obscode'), stationname=stationname, year=readdict.get("Year"), nameofdatachecker=nameofdatachecker)


                email, managermail = ObtainEmailReceivers(loggingdict, para.get('obscode'), os.path.join(pathemails,"mailinglist_minute.cfg"), referee, debug=debug)

                print (" -> sending to {}".format(email))

                # DEFINE A LIST OF OBERVATORIES FOR A TEST RUN - ONLY THESE OBSERVATORIES WILL GET NOTIFICATIONS
                # Send out emails
                # -----------
                if email and mailcfg:
                    print ("Using mail configuration in ", mailcfg)
                    maildict = ReadMetaData(mailcfg, filename="mail.cfg")
                    attachfilelist = loggingdict.get('Attachment')
                    print ("ATTACHMENT looks like:", attachfilelist)
                    print (" -> for file sending", ",".join(attachfilelist))
                    maildict['Attach'] = ",".join(attachfilelist)
                    maildict['Text'] = mailtext
                    maildict['Subject'] = 'IMBOT one-minute analysis for {}'.format(para.get('obscode'))
                    maildict['From'] = 'roman_leonhardt@web.de'
                    print ("Joined Mails", email)
                    print ("-> currently only used for selected. Other mails only send to leon")
                    if para.get('obscode').upper() in testobslist: #or not testobslist
                        print (" Selected observatory is part of a Testing list")
                        maildict['To'] = email
                    else:
                        maildict['To'] = managermail
                    print ("MAILDICT", maildict)
                    sm(maildict)
                else:
                    print ("Could not find mailconfiguration - skipping mail transfer")
                    #logdict['Not yet informed'].append(para.get('obscode'))
                    pass

                if not debug:
                    mailname = os.path.join(destinationpath, "mail-to-send.txt")
                    with open(mailname, 'w') as out:
                        out.write(mailtext)

                # Cleanup
                # -----------
                # Delete temporary directory
                # -----------
                print ("Deleting tempory directory {}".format(sourcepath))
                try:
                    if sourcepath.find(para.get('obscode')) > -1:
                        # just make sure that temporary information is only deleted for the current path
                        # it might happen that treatment/read failures keep some old information in dicts
                        print ("Cleaning up temporary folder ", sourcepath)
                        shutil.rmtree(sourcepath, ignore_errors=True)
                except:
                    pass

                readdict.clear()
                gc.collect()

                #except:
                #    logdict["element"] = "Analysis problem in ConvertData routine"

        return reportdict


def main(argv):
    imbotversion = '1.0.1'
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
    mailcfg = '/etc/martas/mail.cfg'
    quietdaylist = ['2016-01-25','2016-01-29','2016-02-22','2016-03-13','2016-04-01','2016-08-28','2016-10-21','2016-11-05','2016-11-17','2016-11-19','2016-11-30','2016-12-01','2016-12-03','2016-12-04']
    manager = ['ro.leonhardt@googlemail.com','jreda@igf.edu.pl','hom@ngs.ru','tero.raita@sgo.fi','heumez@ipgp.fr','Andrew.Lewis@ga.gov.au']
    memory='/tmp/secondanalysis_memory.json'
    tmpdir="/tmp"
    testobslist=['WIC','BOX','DLT','IPM','KOU','LZH','MBO','PHU','PPT','TAM','CLF']
    analysistype = 'minuteanalysis'

    debug=False

    try:
        opts, args = getopt.getopt(argv,"hs:d:t:q:m:r:n:o:i:e:l:c:p:D",["source=", "destination=", "temporary=", "quietdaylist=","memory=","report=","notify=","observatories=","minutesource=","emails=","logpath=","mailcfg=","testobslist=","debug=",])
    except getopt.GetoptError:
        print ('secondanalysis.py -s <source> -d <destination> -t <temporary> -q quietdaylist -n <notify> -o <observatories> -i <minutesource> -e <emails> -l <logpath> -c <mailcfg> -p <testobslist>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- secondanalysis.py will automatically analyse one second data products --')
            print ('-----------------------------------------------------------------')
            print ('secondanalysis is a python3 program to automatically')
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
            print ('python3 minuteanalysis.py -s /media/leon/Images/Mag2020 -d /tmp -t /tmp -o CLF')
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
        print ('-- check secondanalysis.py -h for more options and requirements')
        sys.exit()
    else:
        memdict = ReadMemory(memory)

    if not os.path.exists(tmpdir):
        print ('Specify a valid path to to temporarly save converted files:')
        print ('-- check secondanalysis.py -h for more options and requirements')
        sys.exit()


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

    print ("Got New uploads:", newdict)
    # 2. For each new input --- copy files to a temporary local directory (unzip if necessary)
    logdict = CopyTemporary(newdict, tmpdir=tmpdir, logdict=logdict)

    print ("Running conversion and data check:")
    # 3. Convert Data includes validity tests, report creation and exporting of data
    fullreport = CheckOneMinute(newdict, tmpdir=tmpdir, destination=destination, logdict=logdict,selecteddayslist=quietdaylist,testobslist=testobslist,pathemails=pathemails,mailcfg=mailcfg, debug=debug)

    # 4. send a report to the IMBOT manager containing failed and successful analysis

    print ("INFORMATION for BOT MANAGER")
    print ("---------------------------")
    print ("Source", currentdirectory)
    #print ("Mainlog", logdict) # - should be stored somewhere...
    #print ("Fullreport of all analyses", fullreport) # - should be stored somewhere...
    print ("Send to Telegram", notification)
    # TODO add ignored directories into the notification

    #if something happend: if len(newdict) > 0:
    if len(newdict) > 0:
        savelogpath = os.path.join(logpath,"minuteanalysis","logdict.json")
        WriteMemory(savelogpath, logdict)
        savelogpath = os.path.join(logpath,"minuteanalysis","fulldict.json")
        WriteMemory(savelogpath, fullreport)

    # 4.1 send a report to the IMBOT manager containng all failed and successful analysis and whether submitter was informed

    sys.exit()


    if not tele == '' and not debug:
        martaslog = ml(logfile=telelogpath,receiver='telegram')
        martaslog.telegram['config'] = tele
        martaslog.msg(notification)

    print ("-> ONE-MINUTE DATA ANALYSIS SUCCESSFULLY FINISHED")


if __name__ == "__main__":
   main(sys.argv[1:])
