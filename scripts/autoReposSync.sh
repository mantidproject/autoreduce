#!/bin/bash

function createInstrumentHash() {
  iList["ARCS"]="ARCS"
  iList["BASIS"]="BSS"
  iList["CNCS"]="CNCS"
  iList["EQSANS"]="EQSANS"
  iList["USANS"]="USANS"
  iList["CORELLI"]="CORELLI"
  iList["HYSPEC"]="HYS"
  iList["NOMAD"]="NOM"
  iList["POWGEN"]="PG3"
  iList["SEQUOIA"]="SEQ"
  iList["SNAP"]="SNAP"
  iList["VISION"]="VIS"
  iList["VULCAN"]="VULCAN"
  iList["MANDI"]="MANDI"
  iList["REF_L"]="REF_L"
  iList["REF_M"]="REF_M"
  iList["TOPAZ"]="TOPAZ"
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
    if [ -f $file1 ]; then 
      if [ -f $file2 ]; then
        diffScript $file1 $file2
      fi
    fi
  done
  specific_files = (template.xml)
  for index in ${!specific_files[*]}
  do
    script=${specific_files[$index]}
    echo $script
    file1="$file/$script"
    file2="/SNS/"$inst"/shared/autoreduce/$script"
    if [ -f $file1 ]; then 
      if [ -f $file2 ]; then
        diffScript $file1 $file2
      fi
    fi
  done
}

# Update the local copy of the code
rm -rf /tmp/autoreduction
test -d /tmp/autoreduction || mkdir -m 0755 -p /tmp/autoreduction
cd /tmp/autoreduction
test -d /tmp/autoreduction/autoreduce || ssh-agent bash -c 'ssh-add ~/.ssh/autoreduce.rsa; git clone git@github.com:mantidproject/autoreduce.git'
cd /tmp/autoreduction/autoreduce
git config user.name "mantid-publisher"
git config user.email "mantid-developers@mantidproject.org"

declare -A iList 
createInstrumentHash

# Identify files to be pushed to git
for file in /tmp/autoreduction/autoreduce/ReductionScripts/sns/*; do
  if [[ $file != *saved ]];
  then
    inst=`echo ${file##*/} |tr 'a-z' 'A-Z'`
    instrument=${iList[$inst]}
    process $file $instrument
  fi
done

echo
echo "Number of files to be updated in git: "${#updateList[*]}

# Push the files to git
if [[ ${#updateList[*]} -ne 0 ]]; then
  for file in ${updateList[@]}; do
    echo $file
    git add $file
  done
  git commit -m 'Updated reduction script by cron job'
  git push
fi





