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

echo "Usage: sumBatchRuns_PG3.sh proposalDirectory outputDirectory runRange"
echo "       If runRange is not specified, the script will find all run numbers"
echo "Usage example: sumBatchRuns_PG3.sh /SNS/PG3/IPTS-9142/0 /tmp/shelly.csv 16043-16051"

if [ "$#" -lt 2 ]; then
  echo "Please provide at least proposalDirectory and outputDirectory"
  exit 0
fi

instrument=PG3
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
  for file in `find $1 -name "$specifiedRun.nxs.h5" -print` 
  do
    echo $file 
    python $script $instrument $file $output
  done
else
  for specifiedRun in ${specifiedRunList[@]}; do
    path=$1
    echo "find $path -name "\\*$specifiedRun.nxs.h5" -print"
    for file in `find $path -name "\\\*$specifiedRun.nxs.h5" -print`; do
      echo $file 
      python $script $instrument $file $output
    done
  done
fi

