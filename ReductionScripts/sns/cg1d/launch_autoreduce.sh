export PATH=/SNS/software/miniconda2/bin:$PATH
source activate py2-cg1d
python /HFIR/CG1D/shared/autoreduce/autoreduce.py $1 $2
