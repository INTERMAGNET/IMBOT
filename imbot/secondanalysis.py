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
import json
from shutil import copyfile
from dateutil.relativedelta import relativedelta
import gc

from imbotcore import *
from version import __version__ as imbotversion

# Basic MARTAS Telegram logging configuration for IMBOT manager
logpath = '/var/log/magpy/imbot.log'
notifictaion = {}
name = "IMBOT"

# TODO list
# 1. add a method to check level directory (as last job)
#    rename all level files from level1_underreview.md, level2_underreview.md to level1.md, level2.md
#    if no changes occured within 3 months


def add_minute_state(cd,step1dir,step2dir,step3dir,obslist=[],excludeobs=[],debug=False):
    """
    DESCRIPTION:
        Get current state of one-minute analysis and add this info
    """

    st3d, ld3 = GetGINDirectoryInformation(step3dir, flag=None, checkrange=0, obslist=obslist,excludeobs=excludeobs, debug=debug)
    st2d, ld2 = GetGINDirectoryInformation(step2dir, flag=None, checkrange=0, obslist=obslist,excludeobs=excludeobs, debug=debug)
    st1d, ld1 = GetGINDirectoryInformation(step1dir, flag=None, checkrange=0, obslist=obslist,excludeobs=excludeobs, debug=debug)

    step3list = [key for key in st3d]
    step2list = [key for key in st2d]
    step1list = [key for key in st1d]
    for key in cd:
        val = cd.get(key)
        if key in step3list:
            val['minute'] = {'step3':step3dir}
        elif key in step2list:
            val['minute'] = {'step2':step2dir}
        elif key in step1list:
            val['minute'] = {'step1':step1dir}
        else:
            val['minute'] = {'step0':''}
    return cd


def update_contacts(contactdict, localmailinglist):
    """
    DESCRIPTION:
        Get current state of one-minute analysis and add this info
    """
    d={}
    d2= contactdict.copy()
    # load localmailinglist if existing - json
    if os.path.exists(localmailinglist):
        with open(localmailinglist) as json_file:
            d = json.load(json_file)
    # add contactdict / overwrite if different
    if d:
        for key, value in d2.items():
            if not (d2.get(key,[]) == []):
                d[key] = value
    else:
        d = d2
    # save  localmailinglist as json
    with open(localmailinglist, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=4)
    # load localmailinglist when calling ObtainE-Mailreceiver function
    # use stored mails if none provided, and use primary mailinglist if contained there
    return True


def GetUploadInformation(sourcepath, checkrange = 2, obslist = [],excludeobs=[], debug=False):
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
        if len(obslist) > 0:
            print ("  -> scanning only for {}".format(obslist))
        storage = {}
        logdict = {}
        for root, dirs, files in os.walk(sourcepath):
          level = root.replace(sourcepath, '').count(os.sep)
          if (len(obslist) > 0 and root.replace(sourcepath, '')[1:4] in obslist) or len(obslist) == 0:
            if (len(excludeobs) > 0 and not root.replace(sourcepath, '')[1:4] in excludeobs) or len(excludeobs) == 0:
              if level == 1:
                if debug:
                    print ("  -> found matching directory: {}".format(root))
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
                    if debug:
                         print ("  -> youngest file: {}".format(youngest))
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
        validfilenames = [fn for fn in os.listdir(sourcepath) if any([fn.endswith(ext) for ext in included_extensions])]
        # Delete all files with invalid names?
        print (" Valid files for read test are:", validfilenames)
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


def ReadMonth(sourcepath, starttime, endtime, logdict={}, updateinfo={}, optionalheads=['StationWebInfo', 'DataTerms', 'DataReferences'], debug=False):
        """
        DESCRIPTION:
            reading one month of data and checking contents
        """
        metainfo = {}
        issues = {}
        issues=logdict.get('Issues',{})
        improvements = {}
        warningdict = {}   # warnings are included and marked too-be-checked in summaries for data checkers for level 3 acceptance
        warningdict=logdict.get('Warnings',{})
        #print ("Reading data from {} to {}".format(starttime,endtime))
        st = datetime.strptime(starttime,'%Y-%m-%d')+timedelta(days=1)
        et = datetime.strptime(endtime,'%Y-%m-%d')-timedelta(days=1)
        days = int(date2num(et) - date2num(st))
        expectedcount = int(days*24.*3600.)
        #print ("Exporting data from {} to {}".format(st,et))
        try:
            data = read(os.path.join(sourcepath,'*'),starttime=starttime, endtime=endtime)
        except:
            data = DataStream()
        data = data.trim(starttime=st,endtime=et)
        newmeta = ReadMetaData(sourcepath)
        if data.length()[0] > 1:
            print (" -> second data: {}".format(data.length()[0]))
            # drop flagged data
            data = data.remove_flagged()
            # drop temperature anad other columns
            temp1 = data._get_column('t1')
            temp2 = data._get_column('t2')
            var = data._get_column('var1')
            if len(temp1) > 0:
                print (" Found temperature column")
                data = data._drop_column('t1')
                try:
                    txt = "{}+/-{} degC".format(np.nanmean(temp1),np.nanstd(temp1))
                    logdict['Temperature1 record contained'] = data.header.get('DataLeapSecondUpdated')
                except:
                    pass
            if len(temp2) > 0:
                data = data._drop_column('t2')
            if len(var) > 0:
                data = data._drop_column('var')
            cntbefore = data.length()[0]
            data = data.get_gaps()
            cntafter = int(data.length()[0])
            st, et = data._find_t_limits()
            if debug:
                print (" ReadMonth: got range from {} to {}".format(st,et))
            effectivedays = int(date2num(et) - date2num(st))+1
            ### Try to load any additional meta information provided in file meta_obscode.txt
            if len(newmeta) > 0:
                print ("Observatory provided additional meta information: {}".format(newmeta))
                for key in newmeta:
                   nkey = key
                   print ("Appending new meta info for {}".format(key))
                   HEADTRANSLATE = {'FormatDescription':'DataFormat', 'IagaCode':'StationID', 'ElementsRecorded':'DataComponents', 'ObservatoryName':'StationName', 'Latitude':'DataAcquisitionLatitude', 'Longitude':'DataAcquisitionLongitude', 'Institution':'StationInstitution', 'VectorSensOrient':'DataSensorOrientation', 'TermsOfUse':'DataTerms','UniqueIdentifier':'DataID','ParentIdentifiers':'SensorID','ReferenceLinks':'StationWebInfo', 'FlagRulesetType':'FlagRulesetType','FlagRulesetVersion':'FlagRulesetVersion'} # taken from format_imagcdf
                   for cdfhead in HEADTRANSLATE:
                       if cdfhead.find(key) > -1 or HEADTRANSLATE[cdfhead].find(key) > -1:
                           nkey = HEADTRANSLATE[cdfhead]
                   print (" {}".format(nkey))
                   data.header[nkey] = newmeta[key]

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
            if not (expectedcount-cntafter) == 0:
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
            if newmeta.get('MissingData','') in ['confirmed','Confirmed','confirm']:
                logdict['Missing data'] = 'confirmed as missing by submitter'
                warningdict['Missing data'] = 'missing data confirmed by submitter - please verify that all data has been correctly uploaded as IMBOT in this case cannot distinguish between corrupted and missing data'
            else:
                logdict['Level'] = 0
                issues['Data coverage'] = 'Check data files - data files missing?'

        logdict['Header'] = metainfo
        logdict['Issues'] = issues
        logdict['Warnings'] = warningdict
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
            #TODO proper treatment of -S values in delta_f in MagPy
            # or ignore: G is quality value for variometer data and
            #should be provided for existing variometer values.
            # If F(S) should be provided, an independent measurement with
            # with eventually different sampling rate or data value at non-existing
            # variometer data, then please provide it as S. G can be easily calculated
            #quick workaround -> exclude large negative  values
            ftest = ftest.extract('df',-15000,'>')

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
                if key in ['IMOS41','IMOS-41'] and (logdict.get('F') in ['None',''] or logdict.get('F').startswith('found no')):
                    tableline.append('confirmed but invalid')
                    issuedict['StandardLevel - IMOS-41'] = 'criteria not met'
                elif key in ['IMOS42','IMOS-42'] and logdict.get('T') in ['None','']:
                    tableline.append('confirmed but invalid')
                    issuedict['StandardLevel - IMOS-42'] = 'criteria not met'
                else:
                    tableline.append('validity confirmed by submitter')
                tablelist.append(tableline)
        elif head.get('DataStandardLevel','') in ['partial','Partial','PARTIAL']:
            pkeyl = [key for key in head if key.find('PartialStandDesc') > -1]
            if len(pkeyl) > 0:
                partialvals = head.get(pkeyl[0])
            else:
                partialvals = []
            print ("Partial descriptions necessary. They look like:", partialvals)
            if partialvals and not isinstance(partialvals, list):
                print ('partialvals are not provided as list - converting')
                partialvals = partialvals.split(',')
            # Convert IMOS41 to IMOS-41
            nl = []
            for el in partialvals:
                if el.startswith('IMOS') and not el.startswith('IMOS-'):
                    nl.append(el.replace('IMOS','IMOS-'))
                else:
                    nl.append(el)
            partialvals = ",".join(nl)
            print ("provided partial vals look like:",  partialvals)
            for key in partialcheck:
                tableline = []
                tableline.append(key)
                tableline.append(partialcheck.get(key))
                try:
                    print (key, partialvals)
                    if partialvals.find(key) > -1:
                        print ("Found the key in partialvals")
                        tableline.append('validity confirmed by submitter')
                        if key == 'IMOS-41' and (logdict.get('F') in ['None',''] or logdict.get('F').startswith('found no')):
                            tableline.append('confirmed but invalid')
                            issuedict['StandardLevel - IMOS41'] = 'criteria not met'
                        elif key == 'IMOS-42' and logdict.get('T') in ['None','']:
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


def compare_meta(minhead,sechead,mindatadict,issuedict, warningdict, debug=False):
    """
    DESCRIPTION:
        compare meta information of second and minutedata
    """
    if debug:
        print ("Minute data header: {}".format(minhead))
        print ("Second data header: {}".format(sechead))

    diffcnt=0
    excludelist = ['DataFormat','SensorID','DataComponents','DataSamplingRate','DataPublicationDate','DataSamplingFilter','DataDigitalSampling','StationInstitution']
    floatlist = {'DataElevation':0,'DataAcquisitionLongitude':2,'DataAcquisitionLatitude':2}
    if minhead and sechead:
        for key in sechead:
            if not key.startswith('col') and not key.startswith('unit') and not key in excludelist and key in minhead:
                onlywarn = False
                if debug:
                    print ("Checking key: {}".format(key))
                refvalue = str(sechead.get(key))
                compvalue1 = str(minhead.get(key,''))
                keyname = key.replace('Data','').replace('Station','')
                refshort = refvalue
                compshort = compvalue1
                if key in floatlist:
                    try:
                        refshort = np.round(float(refvalue),floatlist.get(key))
                    except:
                        refshort = 0
                    try:
                        compshort = np.round(float(compvalue1),floatlist.get(key))
                    except:
                        compshort = 0
                if key == 'DataSensorOrientation':
                    refshort = refvalue.lower()[:3]
                    compshort = compvalue1.lower()[:3]
                    # only warn here as both data sources might come from different instruments
                    onlywarn = True
                if not refshort == compshort:
                    if not onlywarn:
                        diffcnt += 1
                    warningdict[keyname] = "found differences for {}: {} (sec) vs {} (min)".format(keyname, refvalue, compvalue1)
                    if debug:
                        print (" Found diff for {}: {} (sec) vs {} (min)".format(keyname, refvalue, compvalue1))
                    #mindatadict['meta-info diff'] = "{}: {} (sec) vs {} (min)".format(keyname, refvalue, compvalue1)
        if diffcnt == 0:
            mindatadict['meta-info diff'] = "meta info fits well to data provided in minute data (note: location data compared at accuracy of 2 digits)".format(keyname, refvalue, compvalue1)
        else:
            issuedict['meta-info minute vs second data'] = "differences observed - see below"
    else:
        mindatadict['meta-info minute vs second data'] = "could not access meta information"
        issuedict['meta-info minute vs second data'] = "could not access meta information"

    return mindatadict, issuedict, warningdict

def extract_mindict(d):
        minstepl = list(d.keys())
        if len(minstepl) > 0:
            minstep=minstepl[0]
            minpath = d.get(minstep)
        else:
            minstep ='step0'
            minpath = ''
        return minstep, minpath


def CheckDiffs2Minute(data, logdict, minutesource={}, obscode='',daterange=[],contactdict={},debug=False):
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
            - since 1.0.4: basic meta data
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

        minstep, minpath = extract_mindict(minutesource)
        if debug:
            print ("Minute source:", minutesource, minstep, minpath)

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


        # TODO -- readme etc is not contained in step3 at NRCAN any more
        mails = ExtractEMails(pathname(minpath,obscode,typ='readme'))
        #print (mails)
        print (" #########################################")
        print (" setting contact dict", mails)
        contactdict[obscode] = mails
        logdict['Contact'] = mails

        if minpath:
            try:
                print ("Loading minute data: ", pathname(minpath,obscode), daterange[0], daterange[1])
                mindata = read(pathname(minpath,obscode),starttime=daterange[0], endtime=daterange[1])
                print (" ... success. Got {} data points".format(mindata.length()[0]))
            except:
                print ("Problem when reading minute data")
                logdict['Definitive comparison'] = 'definitive one-minute not available or not readable'
                mindata = DataStream()
        if minpath and mindata.length()[0] > 1:
            print (" Creating backup of one second data...")
            secdata = data.copy()
            print (" ... done")
            mindatadict, issuedict, warningdict = compare_meta(mindata.header,secdata.header,mindatadict,issuedict, warningdict, debug=debug)
            highresfilt = secdata.filter(missingdata='iaga')
            if debug:
                print ("  -> seconddata filtered to one-minute using iaga standard filter")
            diff = subtractStreams(highresfilt,mindata,keys=['x','y','z'])
            if debug:
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
            if debug:
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
            if np.isnan(sum([xd,yd,zd,xa,ya,za])):
                logdict['Definitive comparison'] = 'not conclusive as NAN values are found'
            print ("  -> one-minute comparison finished")
        else:
            warningdict['Comparison with definitive one-minute'] = 'definitive one-minute not available or not readable'


        logdict['Issues'] = issuedict
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



def WriteReport(destinationpath, parameterdict={}, reportdict={}, logdict={}, tablelist=[], year=2016):
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

        print (levellist)
        # remove Nones from levellist
        levellist = [el for el in levellist if not el in [None,'']]
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

        text = ["# {} - Level {}\n\n# Analysis report for one second data from {} {}\n\n".format(obscode,level,obscode,year)]
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
            text.append("Considerations for manual checking | Observered \n")
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
        print ("Definitive dict", definitivedict)
        for month in definitivedict:
            defdi = definitivedict.get(month)
            monthly = monthlydict.get(month)
            #print (monthly)
            text.append("\nMonth {} | Value \n".format(month))
            text.append("------ | ----- \n".format(month))
            try: # if month is not evaluated as no data has been provided...
                for el in defdi:
                    text.append("{} | {}\n".format(el,defdi[el]))
            except:
                pass
            try:
                for el in monthly:
                    if not isinstance(monthly[el],dict):
                        text.append("{} | {}\n".format(el,str(monthly[el]).strip()))
            except:
                pass


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


def CreateSecondMail(level, obscode, stationname='', year=2016, nameofdatachecker="Max Mustermann",minutestate='step0'):

        print ("MINUTESTATE: {}".format(minutestate))

        maintext =  "Dear data submitter,\n\nyou receive the following information as your e-mail address is connected to submissions of geomagnetic data products from {} {} observatory.\nYour one-second data submission from {} has been automatically evaluated by IMBOT, an automatic data checker of INTERMAGNET.\n\nThe evaluation process resulted in\n\n".format(stationname, obscode, year)


        maintext += "LEVEL {}\n\n".format(level)

        if minutestate in ['','step0','step1','step2',None]:
            maintext += "!! Please note: this is just a preliminary evaluation result as your obligatory one-minute data product has not yet been finally accepted. "
            if minutestate in ['','step0',None]:
                maintext += "Currently there is no one-minute data available. "
            else:
                maintext += "Your one-minute data is currently on {}. ".format(minutestate)
            maintext += "You will receive an update of your evaluation report whenever your one-minute data reaches the next step. If corrections to your one-second product are suggested in the following, please perform those already now in order to speed up the final acceptance process.\n\n"
            time = 'will be'
            last = ' as soon as your one-minute data is finally accepted.'
        else:
            time = 'has been'
            last = ". Your data checker is {}.\nPlease note that INTERMAGNET data checkers perform all check on voluntary basis beside their usual duties. So please be patient. The data checker will contact you if questions arise".format(nameofdatachecker)

        level0 = "Level 0 means that your data did not pass the automatic reading and conversion test. Please update your data submission.\nOften a level 0 report is connected to corrupted files.\nPlease read the attached report and instructions before re-submission.\n\n"
        level1 = "Level 1 indicates that your data is almost ready for final reviews. In order to continue the evaluation process some issues need to be clarified. Please read the attached report and follow the instructions. In most cases obligatory meta-information is missing. You can easily provide that by filling out and uploading the attached meta_{}.txt file.\n\n".format(obscode)

        level2 = "Congratulations! Your data fulfills all requirements of the automatic checking process. A level 2 data product is an excellent source for high resolution magnetic information. Your data set {} assigned to an INTERMAGNET data checker for final decision{}\n\n".format(time,last)

        if int(level) == 0:
            maintext += level0
        elif int(level) == 1:
            maintext += level1
        elif int(level) == 2:
            maintext += level2

        maintext += "The attached report makes use of markdown syntax and can be viewed in a formatted way i.e. using https://dillinger.io/. If you have any questions regarding the evaluation process please check out the general instructions (https://github.com/INTERMAGNET/IMBOT/blob/master/README.md - currently only available online for IM definitive data committee) or contact the IMBOT manager and request a pdf.\n\n"
        maintext += "\nSincerely,\n       IMBOT\n\n"


        if int(level) < 2:
            instructionstext = """
    -----------------------------------------------------------------------------------
    Instructions to update files and meta information for re-evaluation of your data:

    1. Do NOT edit any file in the submitting step1 directories as long as you are NOT ready to submit a revised version

    2. Check the report you received by mail for issues and suggested improvements

         The report is a text file in markdown language. You can read it in any text editor
         or you might choose a special markdown editor (e.g. https://dillinger.io/)

    2.1. The report is titled "level0_underreview"

         There are general problems with file structure, data files, or
         readability of your files. Eventually a file got corrupted during upload. Please
         check the submitted files and convert them either to IAGA-2002 and or IMAGCDF.
         Data which can be read by MagPy can usually also be analyzed. Please upload
         corrected files into the step1 directory of the GIN.

    2.2. The report is titeled "level1_underreview"

         Your data is almost acceptable by INTERMAGNET.
         There are, however, minor issues. Mostly some meta information, which is required for
         INTERMAGNET archiving is missing. Please follow the instructions in section 3 of these
         instructions on how to obtain a level 2 clearance.

    2.3. The report is titled "level2_underreview"

         Your data set meets all criteria of the automatic data check and is ready for final evaluation.
         Nevertheless, please check the report for suggested improvements and follow the steps
         outlined in section 3 if you want to consider them for the final data product (not obligatory).
         A reviewer will automatically be assigned abd contacted as soon as your one-minute
         product has been formally accepted.
         Please note:
         Data checkers do all reviews and evaluation beside their usual duties. Depending on their workload
         it might need a while.
         Usually, a final data check summary is obtained within three months after level 2 submission.

         The final manual evaluation contains a data quality check of your one second data product.
         Failing this evaluation has no consequence for your INTERMAGNET status which is
         related to one-minute data. Anyway, please analyze any upcoming issues carefully:
         it might be useful to check your data preparation
         routines and might trigger improvements of instrumentation,
         powering systems and, eventually, instruments location.

    3. You are ready to perform updates to your submission

    3.1 Prepare you updates locally and upload them altogether.

    3.2 Upload new files and information sheets into the
        step1 directory of the GIN.

    3.3 For meta information updates:
        Please use the "meta_OBSCODE.txt" template attached to this mail or download it
        from the GIN within directory year/"OBSCODE".
        Please add the requested meta data into this file.

    3.4 For data file updates:
        Upload the new/corrected files and replace/delete old files within
        the step1 directory of the GIN. If you are uploading packed/zipped
        archives, then make sure that data is located within the primary level
        of this archive.

    3.6 Within 24 hours after you finished your uploads
        an automatic (re)evaluation will be triggered.

    4. Problems

        If you have problems or questions please contact the IMBOT manager.
                               """
            maintext += instructionstext.replace('OBSCODE',obscode)

        return maintext


# Read files, anaylse them and write to IMAGCDF
def CheckOneSecond(pathsdict, tmpdir="/tmp", destination="/tmp", logdict={}, selecteddayslist=[], testobslist=[], mailcfg='', pathemails='', notification=None, contactdict={}, debug=False):
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
        for obscode in pathsdict:
                print ("Starting analysis for {}".format(obscode))
                #try
                readdict = {}
                para = pathsdict.get(obscode)
                dailystreamlist = []
                loggingdict = {}
                tablelist = []
                datelist = []
                emails = None
                referee = None
                submissionstatus = ''
                nameofdatachecker = ''
                sourcepath = os.path.join(tmpdir, 'raw', para.get('obscode'))
                destinationpath = os.path.join(destination, 'level', para.get('obscode'))
                readdict['Obscode'] = para.get('obscode')
                readdict['Sourcepath'] = sourcepath
                readdict['Destinationpath'] = destinationpath
                if debug:
                    print ("--------------------------------------")
                    print (" CheckOneSecond - 1: get months")
                datelist, readdict = GetMonths(sourcepath,readdict)  # here we already know whether data is readable
                if debug:
                    print ("GetMonth done for {}: {}, {}".format(obscode, datelist, readdict))
                # - eventually read dictionary with meta information update (should be contained in pathsdict)
                # Check notification whether update or new
                if debug:
                    print ("--------------------------------------")
                    print (" CheckOneSecond - 2: identifying submission status")
                updatelist = notification.get('Updated data',[])
                print (" Updated data sets:", updatelist)
                updatestr = ''
                if para.get('obscode') in updatelist:
                    submissionstatus = 'Submission UPDATE received: '
                if debug:
                    print (" Mail subject starts with:", updatestr)

                if debug:
                    print (" --------------------------------------")
                    print (" Starting analysis:")
                updatedictionary = {} #GetMetaUpdates()
                if debug:
                    print ("!! DEBUG SELECTED: only analyzing first month !!")
                    datelist = datelist[:1]
                for i, dates in enumerate(datelist): #enumerate(datelist[:1]): # enumerate(datelist):
                    loggingdict = {}
                    if debug:
                        print ("  Analyzing time range: {}".format(dates))
                        print ("  Reading data ...")
                    # - read a month of data (including meta info and completeness check)
                    # -----------
                    # - each month gets an dictionary with level suggestions
                    mdata, loggingdict = ReadMonth(sourcepath,dates[0],dates[1],updateinfo=updatedictionary,debug=debug)
                    # - perform level test (delta f)
                    # -----------
                    if debug:
                        print ("Header looks like:", mdata.header)

                    if mdata.length()[0] > 0:

                        if debug:
                            print ("  Running delta F test ...")
                        loggingdict = DeltaFTest(mdata, loggingdict)

                        # - perform level test (standard descriptions)
                        # -----------
                        if debug:
                            print ("  Running Standard level test ...")
                        tablelist, loggingdict = CheckStandardLevel(mdata, loggingdict)
                        # - perform level test (definitive status) - requires path to definitive minute values
                        # -----------

                        # is it possible to extract an e-mail address here?
                        if debug:
                            print ("  Checking definitive status ...")
                        print ("  comparing with: {}".format(para.get('minute')))
                        loggingdict = CheckDiffs2Minute(mdata, loggingdict, minutesource=para.get('minute'), obscode=para.get('obscode'), daterange=[dates[0],dates[1]],contactdict=contactdict,debug=debug)

                        # - extract some daily records
                        # -----------
                        if debug:
                            print ("  Extracting quiet days ...")
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
                            print (" Exporting monthly ImagCDF files")
                        success = ExportMonth(destinationpath, mdata, logdict={})
                        # clear existing month

                    if len(loggingdict.get('Issues')) > 0 and not loggingdict.get('Level') == 0:
                        loggingdict['Level'] = 1

                    if not emails:
                        emails = loggingdict.get('Contact',None)
                        logdict['Contact'] = emails

                    if debug:
                        print ("CHECK ISSUES:", loggingdict.get('Issues'))
                        print ("CHECK WARNINGS:", loggingdict.get('Warnings'))

                    readdict[str(i+1)] = {}
                    newdict = {}
                    for key in loggingdict:
                        value = loggingdict[key]
                        newdict[key] = value
                    readdict[str(i+1)] = newdict
                    loggingdict.clear()

                if debug:
                    print ("analysis finished")
                print ("-----------------------------")
                if debug:
                    print ("Start reporting ...")

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
                level = WriteReport(destinationpath, para, readdict, logdict, tablelist=tablelist,year=readdict.get("Year"))
                print (" Asigning data checker")
                pathreferee = check_path_year(os.path.join(pathemails,"refereelist_second.cfg"),readdict.get("Year"))
                if debug:
                    print ("Loading referees from {}".format(pathreferee))
                nameofdatachecker, referee = GetDataChecker(para.get('obscode').upper(),pathreferee)
                try:
                    stationname = readdict.get('1').get('Header').get('StationName','')
                except:
                    stationname = ''
                if debug:
                    print ("  -> data checker: {}".format(nameofdatachecker))
                print (" Creating Mail")
                minstep, minpath = extract_mindict(para.get('minute'))
                mailtext = CreateSecondMail(level, para.get('obscode'), stationname=stationname, year=readdict.get("Year"), nameofdatachecker=nameofdatachecker, minutestate=minstep)

                # Create mailing list
                # -----------
                pathmailinglist = check_path_year(os.path.join(pathemails,"mailinglist_second.cfg"),readdict.get("Year"))
                email, managermail = ObtainEmailReceivers(logdict, para.get('obscode'), pathmailinglist, referee, localmailinglist= os.path.join(destination,"localmailrep.json"), debug=debug)
                print ("=> sending to {}".format(email))

                print ("---------------------------- ")
                if debug:
                    print ("MAILTEXT for {} to be send to {}:\n{}".format(para.get('obscode'), email, mailtext))
                    print ("---------------------------- ")
                print ("Sending e-mail notifictaion")
                # Send out emails
                # -----------
                if email and mailcfg:
                    if debug:
                        print ("  Using mail configuration in ", mailcfg)
                    maildict = ReadMetaData(mailcfg, filename="mail.cfg")
                    #attachfilelist = loggingdict.get('Attachment')
                    attachfilelist = glob.glob(os.path.join(destinationpath,"*.txt"))
                    if debug:
                        print ("  ATTACHMENT looks like:", attachfilelist)
                        print ("   -> for file sending", ",".join(attachfilelist))
                    maildict['Attach'] = ",".join(attachfilelist)
                    maildict['Text'] = mailtext
                    maildict['Subject'] = '{}IMBOT one-second analysis for {} {}'.format(submissionstatus,para.get('obscode'),readdict.get("Year"))
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
                    if debug:
                        print ("  mail dictionary:", maildict)
                    sm(maildict)
                    print (" -> DONE: mail and report send")
                else:
                    print ("!! Could not find mailconfiguration - skipping mail transfer !!")
                    #logdict['Not yet informed'].append(para.get('obscode'))
                    pass

                if debug:
                    print (" DEBUG mode: Saving mail to a text file")
                    mailname = os.path.join(destinationpath, "mail-to-send.txt")
                    with open(mailname, 'w') as out:
                        out.write(mailtext)

                # Cleanup
                # -----------
                print ("---------------------------- ")
                print ("Cleaning up")
                # Upload data to GIN
                # -----------
                print (" Copying data to destination directory {}".format(destination))
                localsrc = os.path.join(destination, 'level', para.get('obscode'))
                # Pleas note: GIN directory needs to be mounted
                gindest = ''
                #destination = shutil.copytree(localsrc, gindest)
                # Delete temporary directory
                # -----------
                if not debug:
                  print (" Deleting tempory directory {}".format(sourcepath))
                  try:
                    if sourcepath.find(para.get('obscode')) > -1:
                        # just make sure that temporary information is only deleted for the current path
                        # it might happen that treatment/read failures keep some old information in dicts
                        print (" Cleaning up temporary folder ", sourcepath)
                        shutil.rmtree(sourcepath, ignore_errors=True)
                  except:
                    pass

                logdict['Contact'] = []
                readdict.clear()
                gc.collect()

                #except:
                #    logdict["element"] = "Analysis problem in ConvertData routine"

        return reportdict


def main(argv):
    #imbotversion = '1.0.6'
    checkrange = 3 # 3 hours
    statusmsg = {}
    obslist = []
    excludeobs = []
    source = ''
    destination = ''
    pathminute = ''
    pathemails = ''
    tele = ''
    year = 1971
    logpath = '/var/log/magpy'
    mailcfg = '/etc/martas'
    quietdaylist = ['2016-01-25','2016-01-29','2016-02-22','2016-03-13','2016-04-01','2016-08-28','2016-10-21','2016-11-05','2016-11-17','2016-11-19','2016-11-30','2016-12-01','2016-12-03','2016-12-04']
    manager = ['ro.leonhardt@googlemail.com']
    memory='/tmp/secondanalysis_memory.json'
    tmpdir="/tmp"
    #testobslist=['WIC','BOX','DLT','IPM','KOU','LZH','MBO','PHU','PPT','TAM','CLF']
    debug=False
    testobslist = []
    minstep1dir,minstep2dir,minstep3dir = '','',''

    try:
        opts, args = getopt.getopt(argv,"hs:d:t:q:m:r:n:o:i:j:k:e:l:c:p:y:w:D",["source=", "destination=", "temporary=", "quietdaylist=","memory=","report=","notify=","observatories=","minutestep1=","minutestep2=","minutestep3=","emails=","logpath=","mailcfg=","testobslist=","year=","waitingtime=","debug=",])
    except getopt.GetoptError:
        print ('secondanalysis.py -s <source> -d <destination> -t <temporary> -q quietdaylist -n <notify> -o <observatories> -i <minutestep1> -j <minutestep2> -k <minutestep3> -e <emails> -l <logpath> -c <mailcfg> -p <testobslist> -y <year> -w <waitingtime>')
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
            print ('-i            : basic directory for step1 one minute data (IAF files)')
            print ('-j            : basic directory for step2 one minute data (IAF files)')
            print ('-k            : basic directory for step3 one minute data (IAF files)')
            print ('-e            : path to a local email repository - names: mailinglist_second.cfg, refereelist_second.cfg')
            print ('-n            : path for telegram configuration file for notifications')
            print ('-c            : path for mail configuration file "mail.cfg" - default is /etc/martas')
            print ('-l            : path for logs and logging info, default is /var/log/magpy')
            print ('-y            : year')
            print ('-w            : waiting time - default is 3 hours')
            print ('-------------------------------------')
            print ('Example of memory:')
            print ('-------------------------------------')
            print ('Application:')
            print (" - debug mode:")
            print (" python3 /home/leon/Software/IMBOT/imbot/secondanalysis.py -s /home/leon/Cloud/Test/IMBOTsecond/IMinput/2020_step1 -d /home/leon/Cloud/Test/IMBOTsecond/IMoutput/ -t /tmp -i /home/leon/Cloud/Test/IMBOTminute/IMinput/2020_step1 -m /home/leon/Cloud/Test/IMBOTsecond/analysetest.json -n /etc/martas/telegram.cfg -e /home/leon/Software/IMBOTconfig -q '2020-01-13,2020-01-14,2020-02-16,2020-07-11,2020-09-11,2020-10-10,2020-11-18,2020-12-04' -o WIC -D")
            print ('python3 secondanalysis.py -s /tmp/SecondTest -d /tmp -t /tmp')
            print ('python3 secondanalysis.py -s /home/leon/Tmp -t /tmp -d /tmp -o BOU -i /home/leon/Tmp/minute')
            print ('python3 secondanalysis.py -s /media/leon/Images/DataCheck/2016/second/2016_step1 -d /media/leon/Images/DataCheck/IMBOT -t /media/leon/Images/DataCheck/tmp -i /media/leon/Images/DataCheck/2016/minute/Mag2016 -m /media/leon/Images/DataCheck/2016/testanalysis.json -o WIC')
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
        elif opt in ("-i", "--minutestep1"):
            minstep1dir = os.path.abspath(arg)
        elif opt in ("-j", "--minutestep2"):
            minstep2dir = os.path.abspath(arg)
        elif opt in ("-k", "--minutestep3"):
            minstep3dir = os.path.abspath(arg)
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
        elif opt in ("-l", "--logpath"):
            logpath = os.path.abspath(arg)
        elif opt in ("-p", "--testobslist"):
            if arg in ['None','False','none','false','No','no',' ']:
                testobslist = []
            else:
                testobslist = arg.split(',')
        elif opt in ("-y", "--year"):
            year = int(arg)
        elif opt in ("-w", "--waitingtime"):
            try:
                checkrange = int(arg)
            except:
                pass
        elif opt in ("-D", "--debug"):
            debug = True

    if 'REFEREE' in obslist:
        pathreferee = check_path_year(os.path.join(pathemails,"refereelist_second.cfg"),year)
        if debug:
            print ("Loading referees from {}".format(pathreferee))
        obslist = GetObsListFromChecker(obslist, pathreferee)
        print (" OBSLIST provided: dealing only with {}".format(obslist))

    if debug and source == '':
        print ("Basic code test - done")
        sys.exit(0)

    if not os.path.exists(os.path.join(logpath,"secondanalysis")):
        os.makedirs(os.path.join(logpath,"secondanalysis"))

    if not tele == '':
        # ################################################
        #          Telegram Logging
        # ################################################
        ## New Logging features
        from martas import martaslog as ml
        # tele needs to provide logpath, and config path ('/home/cobs/SCRIPTS/telegram_notify.conf')
        telelogpath = os.path.join(logpath,"secondanalysis","telegram.log")

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
    currentdirectory, logdict = GetGINDirectoryInformation(source, checkrange=checkrange,obslist=obslist,excludeobs=excludeobs,debug=debug)
    print ("Obtained Step1 directory: {}".format([key for key in currentdirectory]))

    ## 1.2 Determine publication state and paths for minute data
    currentdirectory = add_minute_state(currentdirectory,minstep1dir,minstep2dir,minstep3dir, obslist=obslist)

    print ("Previous uploads: ", [key for key in memdict])
    ## 1.3 Subtract the two directories - only new files remain
    newdict, notification = GetNewInputs(memdict,currentdirectory)

    print ("Got New uploads:", [key for key in newdict])
    # 2. For each new input --- copy files to a temporary local directory (unzip if necessary)
    logdict = CopyTemporary(newdict, tmpdir=tmpdir, logdict=logdict)

    print ("Running conversion and data check:")
    contactdict = {}
    # 3. Convert Data includes validity tests, report creation and exporting of data
    fullreport = CheckOneSecond(newdict, tmpdir=tmpdir, destination=destination, logdict=logdict,selecteddayslist=quietdaylist,testobslist=testobslist,mailcfg=mailcfg,pathemails=pathemails, notification=notification,contactdict=contactdict,debug=debug)

    print ("---------------------------")
    # 4. if successfully analyzed create new memory

    # 4.1 write/check contact addresses
    addsuccess = update_contacts(contactdict, os.path.join(destination,"localmailrep.json"))

    # 4.2 write analysis memory
    for key in newdict:
        memdict[key] = newdict[key]
    if debug:
        print ("Updating Memory: {}".format(memdict))
    else:
        print ("Updating Memory ...")
    success = WriteMemory(memory, memdict)
    print ("... done")

    # 5. send a report to the IMBOT manager containing failed and successful analysis

    print ("---------------------------")
    print ("INFORMATION for BOT MANAGER")
    print ("---------------------------")
    if debug:
        print ("Source", currentdirectory)
    print ("Send to Telegram", notification)
    # TODO add ignored directories into the notification

    #if something happend: if len(newdict) > 0:
    if len(newdict) > 0:
        savelogpath = os.path.join(destination,"logdict.json")
        WriteMemory(savelogpath, logdict)
        savelogpath = os.path.join(destination,"fulldict.json")
        WriteMemory(savelogpath, fullreport)
        savelogpath = os.path.join(destination,"notification.json")
        WriteMemory(savelogpath, notification)

    # 5.1 send a report to the IMBOT manager containng all failed and successful analysis and whether submitter was informed

    if not tele == '' and not debug:
        martaslog = ml(logfile=telelogpath,receiver='telegram')
        martaslog.telegram['config'] = tele
        martaslog.msg(notification)

    print ("-> ONESECOND DATA ANALYSIS SUCCESSFULLY FINISHED")


if __name__ == "__main__":
   main(sys.argv[1:])
