#!/bin/bash

echo "Usage: sumBatchRuns_PG3.sh instrument proposalDirectory outputDirectory"
echo "Usage example: sumBatchRuns_PG3.sh PG3 /SNS/PG3/IPTS-9284/0 /tmp/shelly.csv"
script=/SNS/$1/shared/autoreduce/sumRun_$1.py
echo $script
echo $1
echo $3
for file in `find $2 -name "*_event.nxs" -print` 
do
  echo $file 
  python $script $1 $file $3
done

