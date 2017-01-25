#!/bin/bash

LOG_DIR="${HOME}/cron_logs"
WORK_DIR="/tmp/autoreduction"
SCRIPT_DIR=$(dirname "$0")
cd $SCRIPT_DIR
SCRIPT_DIR=`pwd`

# setup logging
mkdir -m 0755 -p $LOG_DIR
LOG_FILE="${LOG_DIR}/repo_sync.log"
echo $LOG_FILE
echo `date` > $LOG_FILE

# checkout/update git repo
mkdir -m 0755 -p $WORK_DIR
cd $WORK_DIR
if [[ -d "$WORK_DIR/autoreduce" ]]; then
    cd autoreduce
    git fetch >> $LOG_FILE
    git rebase origin master >> $LOG_FILE
else
    #git clone git@github.com:mantidproject/autoreduce.git >> $LOG_FILE
    ssh-agent bash -c 'ssh-add ~/.ssh/autoreduce.rsa; git clone git@github.com:mantidproject/autoreduce.git >> $LOG_FILE'
    cd autoreduce

    git config user.name "mantid-publisher"
    git config user.email "mantid-developers@mantidproject.org"
fi

# copy files
/usr/bin/env python "${SCRIPT_DIR}/copyreductionfiles.py" "${WORK_DIR}/autoreduce" >> $LOG_FILE

# commit the result
if [[ -n $(git status) ]];then
    echo "Pushing updates to github" >> $LOG_FILE
    git add ReductionScripts/sns >> $LOG_FILE
    git commit -m 'Updated reduction script by cron job' >> $LOG_FILE
    git push >> $LOG_FILE
fi
