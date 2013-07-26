#!/bin/bash
#PBS -l walltime=1:00:00
#PBS -N AUTO_REDUCTION
#PBS -V

#pushd /tmp/work/3qr

#module load mantid-mpi/nightly
module load mantid-mpi
export OMP_NUM_THREADS=16

echo $data_file
echo $facility
echo $instrument
echo $out_dir
reduce_script="/"$facility"/"$instrument"/shared/autoreduce/reduce_"$instrument".py"

time mpirun python $reduce_script $data_file $out_dir

#popd
#echo "Working directory is $PWD"
