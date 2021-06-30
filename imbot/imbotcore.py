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
            print ("  -> Contacts: {}".format(contacts))
            print ("  -> Alternative contacts: {}".format(alternativeemails))
        if not isinstance(alternativeemails, list):
            alternativeemails = [alternativeemails]
        if alternativeemails and len(alternativeemails) > 0:
            emails = alternativeemails

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
            print ("  Debug mode: Skipping all mail addresses and only sending to IMBOT administrator")
            admin = GetMailFromList('admin', mailinglist)
            if not isinstance(admin, list):
                admin = [admin]
            for ad in admin:
                emails.append(ad)
            email = ",".join(emails)
            manageremail = email
            print ("  -> debug recipient: {}".format(email))

        return email, managermail


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

