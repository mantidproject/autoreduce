#!/bin/bash

#
#process_run.sh 
#

export PYTHONPATH=/SNS/software/lib/python2.6/site-packages:/SNS/software/lib/python2.6/site-packages/HLRedux:/SNS/software/lib64/python2.6/site-packages/DOM:/SNS/software/lib/python2.6/site-packages/sns_common_libs

echo "Calling sendMessage.py "$1

#nohup /usr/bin/post_process.sh $1 >> /var/log/SNS_applications/autoreduce.log 2>&1 &

python /usr/bin/sendMessage.py $1

echo "End calling sendMessage.py"


