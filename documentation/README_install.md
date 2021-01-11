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

6. If all modifications have been performed, then start a test run

7. Add IMBOT jobs to crontab


## Application: Updating configuration and runtime script(s)
 
In the following we will install a job to automatically analyse all new data uploaded to the GIN for 2019.

   - update analysis.sh
   - cp mail and telegram.cfg (check/update contents)
   - get ginsource file
   - get analysis20xx.json
   - add credentials


  update analysis.sh and follow instructions given in this bash file

