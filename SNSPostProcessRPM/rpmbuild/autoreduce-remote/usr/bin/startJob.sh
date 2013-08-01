#!/bin/bash

module load mantid-mpi/nightly

echo "Shelly0:"$1":"$2":"$3":"$4":"$5
python /sw/fermi/autoreduction/scripts/doJob.py $1 $2 $3 $4 $5
