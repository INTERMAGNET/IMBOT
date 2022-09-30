#!/usr/bin/env python3
# coding=utf-8

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
import filecmp
from dateutil.relativedelta import relativedelta
import gc

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


def GetGINDirectoryInformation(sourcepath, flag=None, checkrange=2, obslist=[],excludeobs=[], debug=False):
        """
        DESCRIPTION:
            Method will check directory structure of the STEP1 one second directory
            It will extract directory, amount of files, filetype, and last modification date
            ** NEW Version 1.0.4**
            - modified files will be logged
            - test environment for this method
            - would it not be better to use obscode as key and root path as value?
            - added flag (can be step1, step2, step3)
            - new name: GetGINDirectoryInformation
            ** NEW Version 1.0.4**
        RETURN:
            storage   DICT  a dictionary with key root path (.../WIC) and values {'amount': amount, 'type': typ, 'lastmodified': youngest, 'obscode': obscode} ** NEW Version 1.0.4** 'moddict': {file1 : modtime1, file2 : modtime2, ...}
            logdict   DICT

        APPLICTAION:
            to check step 1 one second directory for new or modified data sources
            Suggested technique for updating previously submitted and updated step10,level1, and level2 data:
            Data passing all level0 clearance is moved to a new path (raw: step1, level1-3: level)
            --- extract level information from directory:
            --- thus add a file called " levelx.txt" with the highest reached level after each treatment, add a asterix for data awaiting a check
            This way, the same method can also be applied to the level directory
        TEST:
            $ mount sorcedict
            $ python3
            >>> import minuteanalysis as ma
            >>> storage, log = ma.GetGINDirectoryInformation(sourcepath,checkrange=2,obslist=obslist,excludeobs=[],debug=True)
        """
        print (" Running directory information analysis")
        if debug:
            print (" for observatories: {}".format(obslist))
        if not sourcepath or not os.path.exists(sourcepath):
            print (" GetGINDirectoryInformation: could not access sourcepath {}".format(sourcepath))
            return {},{}
        storage = {}
        logdict = {}
        obscode = 'None'
        for root, dirs, files in os.walk(sourcepath):
          level = root.replace(sourcepath, '').count(os.sep)
          if (len(obslist) > 0 and root.replace(sourcepath, '')[1:4] in obslist) or len(obslist) == 0:
            if (len(excludeobs) > 0 and not root.replace(sourcepath, '')[1:4] in excludeobs) or len(excludeobs) == 0:
              if level == 1:
                if debug:
                    print (" Found level 1 directory: {}".format(root))
                # append root, and ctime of youngest file in directory
                timelist = []
                extlist = []
                obscode = root.replace(sourcepath, '')[1:4]
                obscode = obscode.upper()
                moddict = {}
                for f in files:
                    try:
                        stat=os.stat(os.path.join(root, f))
                        mtime=stat.st_mtime
                        ctime=stat.st_ctime
                        ext = os.path.splitext(f)[1]
                        timelist.append(mtime)
                        extlist.append(ext)
                        moddict[f] = mtime
                    except:
                        logdict[obscode] = "Failed to extract mtimes"
                if len(timelist) > 0:
                    youngest = max(timelist)
                    if debug:
                        #print ("  -> youngest file: {}".format(youngest))
                        print ("  -> last modified : {} ; checking data older than {}".format(datetime.utcfromtimestamp(youngest), datetime.utcnow()-timedelta(hours=checkrange)))
                    # only if latest file is at least "checkrange" hours old
                    if datetime.utcfromtimestamp(youngest) < datetime.utcnow()-timedelta(hours=checkrange):
                        # check file extensions ... and amount of files (zipped, cdf, sec)
                        # firstly remove txt, par and md from list (meta.txt contain updated parameters)
                        if debug:
                            print ("  -> extensions: {}".format(extlist))
                        extlist = [el for el in extlist if not el in ['.txt', '.md']]
                        amount = len(files)
                        if len(extlist) > 0:
                            typ = max(extlist,key=extlist.count)
                            if typ in ['.zip', '.gz', '.tgz', '.tar.gz', '.tar', '.cdf', '.sec']:
                                parameter = {'amount': amount, 'type': typ, 'lastmodified': youngest, 'obscode': obscode, 'rootdir': root, 'flag': flag, 'moddict': moddict}
                                storage[obscode] = parameter
                            elif typ in ['.min', '.bin', '.{}'.format(obscode.lower()), '.blv', '.BIN', '.BLV', '.{}'.format(obscode.upper())]:
                                parameter = {'amount': amount, 'type': typ, 'lastmodified': youngest, 'obscode': obscode, 'rootdir': root, 'flag': flag, 'moddict': moddict}
                                storage[obscode] = parameter
                            else:
                                logdict[obscode] = "Found unexpected data type '{}'".format(typ)
                        else:
                            logdict[obscode] = "Directory existing - but no files found"
                    else:
                        logdict[obscode] = "Uploaded recently - eventually not finished"
              elif level > 1:
                logdict[obscode] = "Found subdirectories - ignoring this folder"

        return storage, logdict


def GetDataChecker(obscode, path="/path/to/refereelist.cfg"):
        """
        DESCRIPTION
            determine a data checker for the Observatory defined by obscode.
            Please note that only one data checker can be asigned for each record.
            The last one will be chosen.
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
            if not isinstance(obslist,list):
                obslist = [obslist]

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

def GetObsListFromChecker(obslist=[],path="/path/to/refereelist.cfg"):
        """
        DESCRIPTION
            determine a data checker for the Observatory defined by obscode.
        PARAMETER:
            path ideally should be the same as for mail.cfg
        RETURNS:
            two strings, a name and a email address
        """
        cleanobslist = [el for el in obslist if not el in ['REFEREE','referee']]
        fullobslist = []
        if not os.path.isfile(path):
            print ("DID NOT FIND REFEREE CONFIGURATION FILE")
            return []
        checkdict = GetConf(path)
        for mail in checkdict:
            subdict = checkdict[mail]
            obslist = subdict.get('obslist',[])
            if not isinstance(obslist,list):
                obslist = [obslist]
            if len(obslist) > 0:
                if len(fullobslist) > 0:
                    fullobslist.extend(obslist)
                else:
                    fullobslist = obslist
        if len(cleanobslist) > 0:
            fullobslist.extend(cleanobslist)

        return list(set(fullobslist))


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

def ObtainEmailReceivers(logdict, obscode, mailinglist, referee, localmailinglist='', debug=False):

        managermail = ''
        # Create mailing list
        # -----------
        # Extract e-mail address from contact in README
        import copy
        d2 = copy.deepcopy(logdict)
        contacts = d2.get('Contact',[])
        emails = contacts

        # if emails is empty then check the local mail repository for mail addresses
        try:
            with open(localmailinglist) as json_file:
                d3 = json.load(json_file)
            localmails = d3.get(obscode,[])
        except:
            localmails = []

        # if alternative email contacts are provided, then use those
        # read file with -e emails option - name: mailinglist.cfg
        alternativeemails = GetMailFromList(obscode, mailinglist)
        if debug:
            print ("  -> Contacts: {}".format(contacts))
            print ("  -> Local Mails: {}".format(localmails))
            print ("  -> Alternative contacts: {}".format(alternativeemails))
        if not isinstance(alternativeemails, list):
            alternativeemails = [alternativeemails]
        if alternativeemails and len(alternativeemails) > 0:
            emails = alternativeemails
        elif contacts and len(contacts) > 0:
            emails = contacts
        else:
            emails = localmails

        manager = GetMailFromList('manager', mailinglist)
        if not isinstance(manager, list):
            manager = [manager]
        if len(manager) > 0:
            managermail = ",".join(manager)  # used for mails not in testobslist

        print ("Mailing list looks like:", emails)
        print ("Referee:", referee)
        if emails:
            # Email could be extracted from contact or from alternativelist
            if referee: # referee is determined by GetDataChecker
                emails.append(referee)
            if manager:
                for man in manager:
                    emails.append(man)
            # emails
            if debug:
                print ("  -> All identified receivers including duplicates:", emails)
            # Remove Duplicates
            emails = list(set(emails))
            email = ",".join(emails)
        else:
            # contact could not be extracted from README and none is provided in alternativelist
            emails = []
            if referee: # referee is determined by GetDataChecker
                emails.append(referee)
            # IMBOT managers are always informed
            for man in manager:
                emails.append(man)
            email = ",".join(emails)

        if debug:
            print ("  -> Referee: {}".format(referee))
            print ("  -> Manager: {}".format(managermail))
            print ("  -> all receipients: {}".format(email))
            emails = []
            email = ''
            print ("  !! DEBUG mode: Skipping all mail addresses and only sending to IMBOT administrator !!")
            admin = GetMailFromList('admin', mailinglist)
            if not isinstance(admin, list):
                admin = [admin]
            for ad in admin:
                emails.append(ad)
            email = ",".join(emails)
            manageremail = email
            print ("  -> debug recipient: {}".format(email))

        return email, managermail

def check_path_year(path,year):
	"""
    if pathname xxx.cfg exists with year (i.e. xxx2020.cfg)
    then return the name with year
	"""
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    blist = basename.split(".")
    blist.insert(-1,year)
    blist.insert(-1,".")
    newpath = os.path.join(dirname,"".join(blist))
    if os.path.isfile(newpath):
        return newpath
    else:
        return path

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


def WriteMemory(memorypath, memdict):
        """
        DESCRIPTION
             write memory
        """
        try:
            with open(memorypath, 'w', encoding='utf-8') as f:
                json.dump(memdict, f, ensure_ascii=False, indent=4)
            #with open(memorypath, 'w') as outfile:
            #    json.dump(memdict, outfile)
        except:
            return False
        return True


def ReadMemory(memorypath,debug=False):
        """
        DESCRIPTION
             read memory
        """
        memdict = {}
        if os.path.isfile(memorypath):
            if debug:
                print ("Reading memory: {}".format(memorypath))
            with open(memorypath, 'r') as file:
                memdict = json.load(file)
        else:
            print ("Memory path not found - please check (first run?)")
        if debug:
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
        if os.path.isfile(sourcepath):
            print (" ReadMetaData: from sourcepath=file")
            metafilelist = [sourcepath]
        else:
            print (" ReadMetaData: from sourcepath=directory")
            metafilelist = glob.glob(os.path.join(sourcepath,filename))
        print (" Loading meta file:", metafilelist)

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


def GetNewInputs(memory, newdict, simple=False, notification={}, notificationkey='', debug=False):
        """
        DESCRIPTION
            will return a dictionary with key/value pairs from dir analysis
            which are not in memory.
             simple only compare keys
        TESTING:
            mem = ma.ReadMemory('/home/leon/Tmp/Mag2020/mem.json')
            new, note = GetNewInputs(mem,storage)
        """
        if not newdict:
            print ("Empty new obs dictionary - returning empty dict")
            return {},notification
        # newly uploaded
        newlist = []
        updatelist = []
        valuelist = []
        out = {}
        mod = {}
        for key, value in newdict.items():
            if not key in memory:
                newlist.append(key)
                out[key] = value
            elif value != memory[key] and not simple:
                memval = memory[key].get('moddict')
                moddict = value.get('moddict')
                #for k,v in moddict.items():
                #    print ("k", memval.get(k,'Not found'))
                #    print ("v", v)
                changed = {k:v for k,v in moddict.items() if v != memval.get(k,'Not found')}
                updatelist.append(key)
                mod[key] = changed
                out[key] = value
            else:
                valuelist.append(key)
        if not simple:
            notification['New Uploads'] = newlist
            notification['Updated data'] = updatelist
            notification['Modified data'] = mod
        if simple and key:
            notification[notificationkey] = valuelist

        if debug:
            print ("Out dictionary:", out)
            print ("Notification:", notification)

        return out,notification

"""
def GetNewInputs(memory,newdict, notification={}):
        #""
        DESCRIPTION
            will return a dictionary with key/value pairs from dir analysis
            which are not in memory
        #""
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
"""

def CopyTemporary(pathsdict, tmpdir="/tmp", logdict={}):
        """
        DESCRIPTION:
            copy files to temporary directory
            zipped files and tar archives will be extracted
        """

        for obscode in pathsdict:
            condict = {}
            para = pathsdict[obscode]
            path = para.get('rootdir')
            newdir = os.path.join(tmpdir, 'raw', para.get('obscode'))

            #para['temporaryfolder'] = newdir

            if not os.path.exists(newdir):
                os.makedirs(newdir)

            for fname in os.listdir(path):
                src = os.path.join(path,fname)
                dst = os.path.join(newdir,fname)
                print ("Copying {} to temporary folder {}".format(fname,dst))
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
                            logdict[obscode] = "Problem with zip file {}".format(fname)
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
                            if not os.path.exists(dst) or not filecmp.cmp(src, dst):
                                copyfile(src, dst)
                                condict[fname] = "file copied"
                            else:
                                condict[fname] = "file already exists"
                        except:
                            condict[fname] = "copying file failed"


            logdict[obscode] = condict
            logdict['temporaryfolder'] = newdir

        return logdict
