

user='cobs'

# TESTING IMBOT methods
import sys
sys.path.insert(1,'/home/{}/Software/magpy/'.format(user))
from magpy.stream import *
sys.path.insert(1,'/home/{}/MARTAS/core/'.format(user))
from martas import martaslog as ml
from martas import sendmail as sm

sys.path.insert(1,'/home/{}/Software/IMBOT/imbot/'.format(user))
import minuteanalysis as ma

# Copy step3 from NRCAN structure to IM structure
success = ma.ConverTime2LocationDirectory('/home/{}/Tmp/step3/2020'.format(user), '/home/{}/Tmp/step3new/mag2020'.format(user), debug=False)

# Obtain statistics
st3, ld3 = ma.GetGINDirectoryInformation('/home/{}/Tmp/step3new/mag2020'.format(user), flag=None, checkrange=0, obslist=['EBR','THY','UPS','VAL','VOS','WIC'],excludeobs=[], debug=False)
st2, ld2 = ma.GetGINDirectoryInformation('/home/{}/Tmp/step2/mag2020'.format(user), flag=None, checkrange=0, obslist=['EBR','THY','UPS','VAL','VOS','WIC'],excludeobs=[], debug=False)
sttmp, ldtmp = ma.GetGINDirectoryInformation('/home/{}/Tmp/step1/Mag2020'.format(user), flag=None, checkrange=0, obslist=['EBR','THY','UPS','VAL','VOS','WIC'],excludeobs=[], debug=False)

# Create a false memory record
vos = sttmp.get('VOS')
vos['lastmodified'] = vos.get('lastmodified') - 200000
vosmod = vos.get('moddict')
vosmod['vos20Aug.bin'] = vosmod.get('vos20Aug.bin') - 200000
sttmp.pop('VAL', None)
#memory = '/home/{}/Tmp/imbot_memory.json'
#success = WriteMemory(memory, memdict)

# Obtain statistics for step1 again
st1, ld1 = ma.GetGINDirectoryInformation('/home/{}/Tmp/step1/Mag2020'.format(user), flag=None, checkrange=0, obslist=['EBR','THY','UPS','VAL','VOS','WIC'],excludeobs=[], debug=False)

# Remove CODES already existing in step3 (and put to notification list)
st1new,noti = ma.GetNewInputs(st3, st1, simple=True, notification={}, notificationkey='Reached step3', debug=False)

# Put CODES already existing in step2 to notification list
stforget,noti = ma.GetNewInputs(st2, st1new, simple=True, notification=noti, notificationkey='Reached step2', debug=False)

# Get changed records
newdict,noti = ma.GetNewInputs(sttmp, st1new, simple=False, notification=noti)


# Save notification (use reached step3 info for one second analysis)
### IMPORT: test if step3, step2 are not existing

# Coyp data to temporary directory
logdict = ma.CopyTemporary(newdict, tmpdir='/tmp/', logdict=ld1)

print (logdict)


pathemails = '/home/{}/IMANALYSIS/Config'.format(user)
mailcfg = '/etc/martas/mail_imbot.cfg'
winepath='/home/{}/.wine/drive_c/'.format(user)
reportdestination='/home/{}/IMANALYSIS/Datacheck/minute/'.format(user)
fullreport = ma.CheckOneMinute(newdict, tmpdir='/tmp/', destination=reportdestination, logdict=logdict,testobslist=['WIC'],pathemails=pathemails,mailcfg=mailcfg,notification=noti, winepath=winepath, debug=False)

memory='/home/cobs/IMANALYSIS/Datacheck/minute/min_analysis2020.json'
memdict={}
for key in newdict:
    memdict[key] = newdict[key]

print ("Updating Memory: {}".format(memdict))
success = ma.WriteMemory(memory, memdict)



Just a personal comment on definitive data storage and access on NRCAN:
The provided file and directory structure follows a concept typically used for seismic data. Such "event" based structure is optimal for seismic data analysis where you need to access data from multiple stations for short duration events. For potential field analysis where you typically analyze long duration time series from specific locations, such storage concept is a pain in the ... especially for user with poor programming skills. I would strongly recommend to change that in a way as used at the GIN's, or other potential field communities like gravity (IGETS) or the GNSS community. The same applies btw for holding meta information. 


{"id": "KHB", "iaga": "KHB", "name": "Khabarovsk", "elevation": 92.0, "region": "Asia", "gin": "Edi", "institutes": ["IKIR"], "latitude": 47.61, "latitude_region": "NH", "longitude": 134.69, "contacts": ["Dumbrava_Zinaida"], "orientation": "HDZ|HDZF", "status": "imo", "instruments_ml": [{"lang": "en", "lines": ["Variations: dIdD GSM-9FD (GEM Systems)", "Absolutes: Mag-01H (theodolite Wild-T1), proton precession magnetometers (type MMP-203)", "CMVS-6 (IZMIRAN)"]}], "country": "ru"}

