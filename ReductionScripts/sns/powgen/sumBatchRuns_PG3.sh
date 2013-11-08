#!/bin/bash

echo "Usage: sumBatchRuns_PG3.sh proposalDirectory outputDirectory"
echo "Usage example: sumBatchRuns_PG3.sh /SNS/PG3/IPTS-9284/0 /tmp/shelly.csv"
instrument=PG3
script=/SNS/$instrument/shared/autoreduce/sumRun_$instrument.py
echo $script
output=$2
for file in `find $1 -name "*_event.nxs" -print` 
do
  echo $file 
  python $script $instrument $file $output
done

