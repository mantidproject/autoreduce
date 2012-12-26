#!/bin/bash

function xmlParse()
{
  inputXml=`curl -s "$1"`
  lines=$(echo "$inputXml" | xmllint --format - | awk -F "#" 'match( $0, />.+</ ) { print substr( $0, RSTART + 1, RLENGTH - 2 ) }')

  for line in $lines; do
    xmlTokens+=(`echo $line | sed -e 's/,//g'`)
  done
}

function getDBRunList()
{
  for range in "${xmlTokens[@]}"; do
    startRun=`echo "$range" | cut -d - -f 1`
    endRun=`echo "$range" | cut -d - -f 2`
    run=$startRun
    while [[ "$run" -le "$endRun" ]]; do 
      dbRunList[${#dbRunList[*]}]=$run
      run=$((run + 1))
    done 
  done
}

function searchDBRunList()
{
  for dbRun in ${dbRunList[@]}; do
    if [[ "$1" -eq "$dbRun" ]]; then
      return 1 
    fi
  done
  return 0
}

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

function filterSpecifiedRunList()
{
  for specifiedRun in ${specifiedRunList[@]}; do
    if [[ "$1" -eq "$specifiedRun" ]]; then
      return 1 
    fi
  done
  return 0
}

function processRuns()
{
  for file in $1; do
    filename=$(echo $file | awk -F "/" '{print $6}')   
    runInfo=$(echo $filename | awk -F "." '{print $1}')
    run=$(echo $runInfo | awk -F "_" '{print $2}')
    if [[ ${#specifiedRunList[*]} -ne 0 ]]; then
      filterSpecifiedRunList $run
      return="$?"
      if [[ $return -eq 1 ]]; then
        runFlag=1
      else
        runFlag=0
      fi
    fi
    if [[ $runFlag -eq 1 ]]; then
      searchDBRunList $run
      return="$?"
      if [[ $return -eq 0 ]]; then
        echo "python /usr/bin/sendMessage.py "$file | sed "s/^/$(date)  /" >> $logfile
        /usr/bin/python /usr/bin/sendMessage.py $file
        sleep 20 
      fi
    fi
  done
}

logfile=/var/log/SNS_applications/processBatchRuns.log
echo 
echo "====Syncing up archive and catalog ADARA runs===="
echo "====Syncing up archive and catalog ADARA runs====" | sed "s/^/$(date)  /" >> $logfile

if [ -z "$1" ] 
  then
    echo "Enter a nexus path: e.g. /SNS/HYSA/IPTS-8809/nexus"
    exit
fi

path=$1
echo "PATH = "$path
echo "PATH = "$path | sed "s/^/$(date)  /" >> $logfile


if [ "$#" -eq 2 ]; then
  echo "run range = "$2
  getSpecifiedRunList $2
else
  echo "Run range is not specified"
fi

echo ${specifiedRunList[@]}

facility=$(echo $path | awk -F"/" '{print $2}')    
instrument=$(echo $path | awk -F"/" '{print $3}')    
proposal=$(echo $path | awk -F"/" '{print $4}')    

xmlTokens=()
dbRunList=()

urlBase=http://icat.sns.gov:8080/icat-rest-ws/experiment
url=$urlBase"/"$facility"/"$instrument"/"$proposal
echo "--Calling ICAT4 web service-- "$url | sed "s/^/$(date)  /" >> $logfile

xmlParse $url
getDBRunList
echo "Runs in ICAT:" | sed "s/^/$(date)  /" >> $logfile
echo ${dbRunList[@]} | sed "s/^/$(date)  /" >> $logfile

echo "--Sending POSTPROCESS.DATA_READY message--" | sed "s/^/$(date)  /" >> $logfile
processRuns $path"/*"

unset xmlTokens 
unset dbRunList
xmlParse $url 
getDBRunList
echo "Runs in ICAT after update:" | sed "s/^/$(date)  /" >> $logfile
echo ${dbRunList[@]} | sed "s/^/$(date)  /" >> $logfile

echo "====Done with sync runs===="
echo "====Done with sync runs====" | sed "s/^/$(date)  /" >> $logfile
echo >> $logfile
