#!/bin/bash

function diffScript() {
file1=$1
file2=$2
echo $file1
echo $file2
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

for file in /SNS/users/3qr/workspace/projects/autoreduce/autoreduce/SNSReductionScripts/*; do
  echo $file
  instrument=`echo ${file##*/} |tr 'a-z' 'A-Z'`
  if [ $instrument == "BASIS" ]; then
    instrument="BSS"
  elif [ $instrument == "HYSPEC" ]; then
    instrument="HYS"
  elif [ $instrument == "POWGEN" ]; then
    instrument="PG3"
  elif [ $instrument == "SEQUOIA" ]; then
    instrument="SEQ"
  fi
  echo $instrument
  reduceScript="reduce_$instrument.py"
  #echo $reduceScript
  file1="$file/$reduceScript"
  file2="/SNS/"$instrument"/shared/autoreduce/$reduceScript"
  if [ ! -f $file1 ]; then
    echo "$file1 does not exist, nothing to do."
  else
    if [ ! -f $file2 ]; then
      echo "$file2 does not exist, nothing to do."
    else
      diffScript $file1 $file2
    fi
  fi
done

echo
echo "List of files to be updated in git:"${updateList[@]}
if [[ ${#updateList[*]} -ne 0 ]]; then
  for file in ${updateList[@]}; do
    echo $file
    git add $file
  done
fi

git commit -m 'Updated reduction script"
git push




