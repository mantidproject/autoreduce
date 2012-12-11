#!/bin/bash

#
#post_process.sh 
#

function process {
# Initialize Overall Return Code, define logfile
export NEXUSLIB=/usr/lib64/libNeXus.so
status=0
logfile=/var/log/SNS_applications/autoreduce.log

nexusFile=$1
# Pass input data
echo 
echo "=========Post Processing========="
echo "nexusFile =" $nexusFile | sed "s/^/$(date)  /" >> $logfile

# Parse nexus file path to get facility, instrument...
var=$(echo $nexusFile | awk -F"/" '{print $1,$2,$3,$4,$5,$6}')                    
set -- $var
facility=$1
instrument=$2
proposal=$3
visit=$4
runNumber=$5
echo "facility="$facility",instrument="$instrument",proposal="$proposal",visit="$visit",runNumber="$runNumber | sed "s/^/$(date)  /" >> $logfile

icatConfig=/etc/autoreduce/icatclient.properties
if [ -f $icatConfig ]; then
  hostAndPort=`awk -F "=" '/hostAndPort/ { print $2 }' $icatConfig`
  password=`awk -F "=" '/password/ { print $2 }' $icatConfig`
else 
  hostAndPort=icat-testing.sns.gov:8181
  password=password
fi

plugin=db

# Accumulate any non-zero return code
status=$(( $status + $? ))
#echo "status=$status"


# Catalog raw metadata
echo "--------Catalogging raw data--------"
ingestNexus=/usr/bin/ingestNexus
echo $ingestNexus $nexusFile
echo "--------Catalogging raw data--------" | sed "s/^/$(date)  /" >> $logfile
echo $ingestNexus $nexusFile | sed "s/^/$(date)  /" >> $logfile
start=`date +%x-%T`
$ingestNexus $nexusFile $plugin $hostAndPort $password | sed "s/^/$(date)  /" >> $logfile
end=`date +%x-%T`
echo "Started at $start --- Ended at $end"

# Reduce raw data
echo "--------Reducing data--------"
sharedDir="/"$facility"/"$instrument"/"$proposal"/shared/"
redOutDir="/"$facility"/"$instrument"/"$proposal"/shared/autoreduce/"
echo "redOutDir= "$redOutDir | sed "s/^/$(date) /" >> $logfile
if [ ! -d $redOutDir ]; then
  mkdir "$redOutDir"
  echo $redOutDir" is created" | sed "s/^/$(date) /" >> $logfile
fi

reduce_script="/SNS/"$instrument"/shared/autoreduce/reduce_"$instrument".py"
if [ ! -f $reduce_script ];
then
  echo "$reduce_script does not exist, exiting..."
  return 
fi
redCommand="python $reduce_script"
echo $redCommand $nexusFile $redOutDir
echo $redCommand $nexusFile $redOutDir  | sed "s/^/$(date)  /" >> $logfile
start=`date +%x-%T`
$redCommand $nexusFile $redOutDir &>> $logfile
end=`date +%x-%T`
echo "Started at $start --- Ended at $end"

# Catalog reduced metadata
echo "--------Catalogging reduced data--------"
ingestReduced=/usr/bin/ingestReduced
echo $ingestReduced $facility $instrument $proposal $runNumber
echo $ingestReduced $facility $instrument $proposal $runNumber | sed "s/^/$(date)  /" >> $logfile
start=`date +%x-%T`
$ingestReduced $facility $instrument $proposal $runNumber $plugin $hostAndPort $password | sed "s/^/$(date)  /" >> $logfile
end=`date +%x-%T`
echo "Started at $start --- Ended at $end"
echo

# Accumulate any non-zero return code
status=$(( $status + $? ))
#echo "status="$status
}

if [ -n "$1" ]; then
  if ! [ -d $1 ] && [ -e $1 ]  && ! [ -h $1 ]; then
    echo "Got nexus file: " $1
    process "$1"
  else
    for nexusFile in `find $1 -name "*event.nxs" -print`
    do
      if [ -e $nexusFile ] && ! [ -h $nexusFile ]; then
        process "$nexusFile"
      fi
    done
  fi
else
  # null argument
  echo "--------processRun.sh takes one argument: an archived directory--------"
  echo "You may try one of the followings:"
  echo "./post_process.sh /SNS/PG3/IPTS-6804/"
  echo "./post_process.sh /SNS/PG3/IPTS-6804/0/6160"
  echo "./post_process.sh /SNS/PG3/IPTS-6804/0/6160/NeXus/PG3_6160_event.nxs"
fi
