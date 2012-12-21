#!/bin/bash

function createInstrumentHash() {
  iList["ARCS"]="ARCS"
  iList["BASIS"]="BSS"
  iList["CNCS"]="CNCS"
  iList["HYSPEC"]="HYS"
  iList["NOMAD"]="NOM"
  iList["POWGEN"]="PG3"
  iList["REF_L"]="REF_L"
  iList["REF_M"]="REF_M"
  iList["SEQUOIA"]="SEQ"
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


declare -A iList 
createInstrumentHash

for file in /SNS/users/3qr/workspace/projects/autoreduce/autoreduce/SNSReductionScripts/*; do
  #echo $file
  inst=`echo ${file##*/} |tr 'a-z' 'A-Z'`
  instrument=${iList[$inst]}
  reduceScript="reduce_$instrument.py"
  echo $reduceScript
  file1="$file/$reduceScript"
  file2="/SNS/"$instrument"/shared/autoreduce/$reduceScript"
  if [ ! -f $file1 ]; then echo "$file1 does not exist, nothing to do."
  else
    if [ ! -f $file2 ]; then
      echo "$file2 does not exist, nothing to do."
    else
      diffScript $file1 $file2
    fi
  fi
done

echo
echo "Number of files to be updated in git: "${#updateList[*]}
if [[ ${#updateList[*]} -ne 0 ]]; then
  for file in ${updateList[@]}; do
    echo $file
    git add $file
  done
  git commit -m 'Updated reduction script by cron job'
  git push
fi





