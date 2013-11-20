#!/bin/bash

function createInstrumentHash() {
  iList["ARCS"]="ARCS"
  iList["BASIS"]="BSS"
  iList["CNCS"]="CNCS"
  iList["EQSANS"]="EQSANS"
  iList["HYSPEC"]="HYS"
  iList["NOMAD"]="NOM"
  iList["POWGEN"]="PG3"
  iList["SEQUOIA"]="SEQ"
  iList["SNAP"]="SNAP"
}

function diffScript() {
file1=$1
file2=$2
diff $file1 $file2 > /dev/null 2>&1
ret="$?"
if [ "$ret" -eq 2 ]; then
  echo "There was something wrong with the diff command"
elif [ "$ret" -eq 1 ]; then
  echo "$file1 and $file2 differ"
  cp $file2 $file1
  updateList[${#updateList[*]}]=$file1 
else
  echo "$file1 and $file2 are the same file"
fi
}

function process() {
  file=$1
  inst=$2
  scripts=(reduce sumRun sumRun sumBatchRuns) 
  exts=(py py cfg sh)
  for index in ${!scripts[*]}
  do
    script=${scripts[$index]}_$inst.${exts[$index]}
    echo $script
    file1="$file/$script"
    file2="/SNS/"$inst"/shared/autoreduce/$script"
    if [ ! -f $file1 ]; 
    then 
      echo "$file1 does not exist, nothing to do."
    else
      if [ ! -f $file2 ]; then
        echo "$file2 does not exist, nothing to do."
      else
        diffScript $file1 $file2
      fi
    fi
  done
}

declare -A iList 
createInstrumentHash

for file in /SNS/users/3qr/workspace/projects/autoreduce2/autoreduce/ReductionScripts/sns/*; do
  if [[ $file != *saved ]];
  then
    inst=`echo ${file##*/} |tr 'a-z' 'A-Z'`
    instrument=${iList[$inst]}
    process $file $instrument
  fi
done

echo
echo "Number of files to be updated in git: "${#updateList[*]}
if [[ ${#updateList[*]} -ne 0 ]]; then
  for file in ${updateList[@]}; do
    echo $file
    echo $file | mail -s "Auto reduce script has been modified" "3y9@ornl.gov 3qr@ornl.gov"
    git add $file
  done
  git commit -m 'Updated reduction script by cron job'
  git push
fi





