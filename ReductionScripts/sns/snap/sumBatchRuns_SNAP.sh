#!/bin/bash

function getSpecifiedRunList()
{
  range=$1
  startRun=`echo "$range" | cut -d - -f 1`
  endRun=`echo "$range" | cut -d - -f 2`
  run=$startRun
  while [[ "$run" -le "$endRun" ]]; do
    specifiedRunList[${#specifiedRunList[*]}]=$run
    run=$((run + 1))
  done
}

echo "Usage: sumBatchRuns_SNAP.sh proposalDirectory outputDirectory runRange"
echo "       If runRange is not specified, the script will find all run numbers"
echo "Usage example: sumBatchRuns_SNAP.sh /SNS/SNAP/IPTS-9140/0 /tmp/shelly.csv 13381-13390"

instrument=SNAP
script=/SNS/$instrument/shared/autoreduce/sumRun_$instrument.py
echo "script: "$script
output=$2
echo "output: "$output

if [ "$#" -eq 3 ]; then
  echo "runRange: "$3
  getSpecifiedRunList $3
else
  echo "Run range is not specified"
fi

echo ${specifiedRunList[@]}

if [[ ${#specifiedRunList[*]} -eq 0 ]]; then
  for file in `find $1 -name "*_event.nxs" -print` 
  do
    echo $file 
    python $script $instrument $file $output
  done
else
  for specifiedRun in ${specifiedRunList[@]}; do
    path=$1/$specifiedRun
    for file in `find $path -name "*_event.nxs" -print`; do
      echo $file 
      python $script $instrument $file $output
    done
  done
fi

