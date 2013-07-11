#!/bin/bash

if [ -z "$1" ]
  then
    echo "Enter an instrument path: e.g. /SNS/PG3"
    exit
fi

calDir="CAL"
dataDir="data"
sharedDir="shared"
for proposalDir in `find "$1" -maxdepth 1 -mindepth 1 -type d -mtime -180`; do
  if [[ ! "$proposalDir" =~ "$calDir" ]]; then  
    #echo "$proposalDir"
    for collectionDir in `find "$proposalDir" -maxdepth 1 -mindepth 1`; do
      if [[ ! "$collectionDir" =~ "$dataDir" ]] && [[ ! "$collectionDir" =~ "$sharedDir" ]]; then
        echo "$collectionDir"
        ./ingestBatchRuns.sh $collectionDir
      fi
    done
  fi
done

