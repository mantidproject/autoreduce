#!/bin/bash
#PBS -l nodes=2:ppn=16
#PBS -l walltime=1:00:00
#PBS -N AUTO_REDUCTION
#PBS -V

module load mantid-mpi/nightly

echo $data_file
echo $facility
echo $instrument
echo $out_dir
reduce_script="/"$facility"/"$instrument"/shared/autoreduce/reduce_"$instrument".py"

time mpirun -np 1 python $reduce_script $data_file $out_dir

#time mpirun -np 32 python reduce_NOM.py $data_file /SNS/users/3qr/testParaReduction/

#time mpirun -np 32 python reduce_NOM.py /SNS/NOM/IPTS-7169/0/8570/NeXus/NOM_8570_event.nxs /SNS/users/3qr/testParaReduction/logs

#echo "Working directory is $PWD"
