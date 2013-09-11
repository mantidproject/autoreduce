#!/bin/bash

module load mantid-mpi

#remove leading and ending single quote
inStr=$1
outStr=${inStr#"'"}
outStr=${outStr%"'"}

python /sw/fermi/autoreduce/scripts/PostProcessAdmin.py $outStr
