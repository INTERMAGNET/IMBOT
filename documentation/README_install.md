# How to get IMBOT running

IMBOT consists of several python3.x scripts. IMBOT does not come with an installer. In order to run it you just need to clone the GITHUB repository to your local harddrive. All jobs and configurations need to be adjusted manually. A periodic execution is perfomred using crontab. Please note, although the code is platform independent it is highly recommended to run IMBOT in a LINUX environment. All instructions will assume such a platform. IMBOT requires Python >= 3.6. 

## Prerequisites

IMBOT requires a few python packages as listed below: 

        sudo pip3 install geomagpy>=0.9.7
        sudo pip3 install telegram_send

Besides the following Linux packages need to be installed:

        sudo apt-get install curlftpfs
        sudo apt install p7zip-full p7zip-rar


## Installation

1. Download/Clone the IMBOT repository. In the following we assume that you clone it to directory "/home/user/Software/IMBOT/".

        mkdir /home/user/Software/
        cd /home/user/Software/
        git clone https://

2. Create a path for your runtime jobs and logs

        mkkdir /home/user/IMANALYSIS
        mkkdir /home/user/IMANALYSIS/Runtime

3. Copy configuration files and runtime bash scripts into this directory

        cp /home/user/Software/config/*.cfg /home/user/IMANALYSIS/Runtime/
        cp /home/user/Software/bash/*.sh /home/user/IMANALYSIS/Runtime/

4. Modify configuration files and runtime scripts according to your system (see next chapter "Application" for details)

5. Create paths to store temporary conversion files and a local performance memory. Please do not use the systems "/tmp" folder.

        mkdir /home/user/IMANALYSIS/Datacheck

6. IMBOT-minute specific installations

Install wine and add check1min.exe program.

        sudo apt-get install wine

Start an exe program to get wine to be initialized for "root".

Create a data folder in drive_c

        sudo mkdir /root/.wine/drive_c/daten

Copy check1min into /root/.wine/drive_c/

        sudo cp check1min.exe /root/.wine/drive_c/

7. If all modifications have been performed, then start a test run

8. Add IMBOT jobs to crontab


## Updating IMBOT parameter on GITHUB

When performed as listed above, then IMBOT parameters will periodically be cloned from GITHUB. IMBOT paremeters can be changed by all persons having access to this GITHUB repository. Particularly important are changes to mailinglists and refereelists.


IMPORTANT: if mailaddresses are provided within mailinglist_minute.txt for a specific IMO, then these mailaddresses will replace any contacts as listed in the readme.imo file. 



## Testing and running IMBOT


### IMBOT-minute (and IMBOT-second soon)

1. Travis CI mode:

2. Debug mode: 
   Running for a specifc observatory -> notification only for IMBOT admin
   (debugging, testing new specifications and methods)
   modify analysisminuteYEAR.sh:
   OBSTESTLIST="IAGACODE"  e.g. OBSTESTLIST="WIC"
   OBSLIST="IAGACODE"      e.g. OBSLIST="WIC"
   add debug=True in minuteanalysis.py line

3. Selected testmode:
   Testing for a specific observatory (only managermail)
   modify analysisminuteYEAR.sh:
   OBSTESTLIST=""  e.g. OBSTESTLIST=""
   OBSLIST="IAGACODE"      e.g. OBSLIST="WIC"

4. Partial testmode:
   Running for all observatories listed in refereelist_minute (full report for selected)
   e.g. refereelist_minute contains ABC,BCD,CBA
   OBSTESTLIST="ABC,BCD,CBA"
   OBSLIST="REFEREE,WIC"
   
   -> full report for ABC,BCD,CBA; only managermail for all others in refereelist

5. Full testmode:
   Running for all observatories -> notification only for IMBOT manager
   (to be used for major test runs) e.g. one-second test run

6. Selected productive mode: 
   specific obs list -> referee, submitter, manager mail

   OBSTESTLIST=""
   OBSLIST="IAGACODE"      e.g. OBSLIST="WIC"

7. Productiv mode:
   all obs in referee list -> referee, submitter, manager mail; no fallback
   current minute state

   OBSTESTLIST=""
   OBSLIST="REFEREE,IAGACODE"      e.g. OBSLIST="REFEREE,WIC"

8. Full productive mode:
   all obs -> referee, submitter, manager mail; obs not in referee list -> fallback referee, submitter, manager
   Running for all observatories making use of fallback e-mail in refereelist if obs not listed

   OBSTESTLIST=""
   OBSLIST=""
   and remove options -p and -o from minuteanalysis.py line
   (TODO: UNTESTED)

9. Issues to be tested:
   - if obscode and mailaddress is listed in mailinglist (alternative contacts):
     do the alternative mails replace or extend the receiver list from readme.xxx
     

### IMBOT-second




## Application: Updating configuration and runtime script(s)
 
In the following we will install a job to automatically analyse all new data uploaded to the GIN for 2019.

   - update analysis.sh
   - cp mail and telegram.cfg (check/update contents)
   - get ginsource file
   - get analysis20xx.json
   - add credentials


  update analysis.sh and follow instructions given in this bash file

