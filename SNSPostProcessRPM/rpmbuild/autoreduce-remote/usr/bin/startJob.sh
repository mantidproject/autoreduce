#!/bin/bash

module load mantid-mpi/nightly

python /sw/fermi/autoreduction/scripts/PostProcessAdmin.py $1
