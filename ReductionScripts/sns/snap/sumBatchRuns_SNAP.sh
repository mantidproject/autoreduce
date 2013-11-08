#!/bin/bash

echo "Usage: sumBatchRuns_SNAP.sh proposalDirectory outputDirectory"
echo "Usage example: sumBatchRuns_SNAP.sh /SNS/SANP/IPTS-9140/0 /tmp/shelly.csv"
instrument=SNAP
#script=/SNS/$instrument/shared/autoreduce/sumRun_$instrument.py
script=sumRun_$instrument.py
echo $script
output=$2
for file in `find $1 -name "*_event.nxs" -print` 
do
  echo $file 
  python $script $instrument $file $output
done

