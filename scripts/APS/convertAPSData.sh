#!/bin/bash

#set temp archival directory
APSRoot="/SNS/users/3qr/data/APS"
instrument="11-ID-B"
proposal="PUP-1234"
archDir=$APSRoot"/"$instrument"/"$proposal
echo "archival directory = "$archDir
tifDir=$archDir"/tif"
echo "tif directory = "$tifDir
if [ ! -d $tifDir ]; then
  mkdir "$tifDir"
  echo $tifDir" is created"
fi
reducedDir=$archDir"/reduced"
echo "reduced directory = "$reducedDir
if [ ! -d $reducedDir ]; then
  mkdir "$reducedDir"
  echo $reducedDir" is created"
fi

#set run number
IN=$1
arrIN=(${IN//\// })
aLen=${#arrIN[@]}
if [[ $aLen == "6" ]]; then
  runNumber=${arrIN[$aLen-3]}"_"${arrIN[$aLen-2]}"_"${arrIN[$aLen-1]}
  echo "run number = "$runNumber
fi
#metaFile=$archDir"/"$instrument"_"$runNumber"_metadata.cfg" 
metaFile=$archDir"/"$runNumber"_metadata.cfg" 
echo "metaFile= "$metaFile

#filter junk and dark frames
#create unique tif file names, and move tif files to archival directory 
file=$1"/*"
for tifFile in `find $file -name "*.tif" -print`; do
  if [[ "$tifFile" != "$1/"junk* ]] && [[ "$tifFile" != *dark* ]]; then
    arr=(${tifFile//\// })
    aLen=${#arr[@]}
    fileName=$instrument"_"$runNumber"_"${arr[$aLen-1]}
    cp $tifFile $tifDir"/"$fileName
    echo $tifDir"/"$fileName
    meta=$tifFile".metadata" 
    if [ -f $meta ]; then
      fileBase=`awk -F "=" '/fileBase/ { print $2 }' $meta`
      echo "["$runNumber"_"$(echo "$fileBase" | tr -d $'\r')"]" >> $metaFile
      width=`awk -F "=" '/width/ { print $2 }' $meta`
      echo "width="$width >> $metaFile
      height=`awk -F "=" '/height/ { print $2 }' $meta`
      echo "height="$height >> $metaFile
      exposureTime=`awk -F "=" '/exposureTime/ { print $2 }' $meta`
      echo "exposureTime="$exposureTime >> $metaFile
      summedExposures=`awk -F "=" '/summedExposures/ { print $2 }' $meta`
      echo "summedExposures="$summedExposures >> $metaFile
      imageNumber=`awk -F "=" '/imageNumber/ { print $2 }' $meta`
      echo "imageNumber="$imageNumber >> $metaFile
      phaseNumber=`awk -F "=" '/phaseNumber/ { print $2 }' $meta`
      echo "phaseNumber="$phaseNumber >> $metaFile
      nPhases=`awk -F "=" '/nPhases/ { print $2 }' $meta`
      echo "nPhases="$nPhases >> $metaFile
      dateString=`awk -F "=" '/dateString/ { print $2 }' $meta`
      echo "dateString="$dateString >> $metaFile
    fi
  fi
done

#create unique chi file names, and move chi files to archival directory 
file=$1"/*"
for chiFile in `find $file -name "*.chi" -print`; do
  arr=(${chiFile//\// })
  aLen=${#arr[@]}
  fileName=$instrument"_"$runNumber"_"${arr[$aLen-1]}
  cp $chiFile $reducedDir"/"$fileName 
  echo $reducedDir"/"$fileName
done
