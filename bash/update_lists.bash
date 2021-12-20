#!/bin/bash

#OBTAIN new referee and mailing lists
GIT=/usr/bin/git
RSYNC=/usr/bin/rsync
CHOWN=/usr/bin/chown
GITDIR="/home/user/IMANALYSIS/Runtime/git"
CFGDIR="/home/user/IMANALYSIS/Config"
$GIT clone https://USERCODE@github.com/INTERMAGNET/IMBOTconfig.git $GITDIR
$RSYNC -av --exclude=".git" $GITDIR"/" $CFGDIR
$CHOWN user:user $CFGDIR
rm -rf $GITDIR
