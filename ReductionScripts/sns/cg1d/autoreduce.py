#!/SNS/software/miniconda2/envs/py2-cg1d/bin/python

import os, sys, socket
#check number of arguments
if (len(sys.argv) != 3):
    print "autoreduction code requires a filename and an output directory"
    sys.exit()
if not(os.path.isfile(sys.argv[1])):
    print "data file ", sys.argv[1], " not found"
    sys.exit()
else:
    filename = os.path.abspath(sys.argv[1])
    outdir = os.path.abspath(sys.argv[2])
    if not os.path.exists(outdir): os.makedirs(outdir)

import logging
FORMAT = '%(asctime)s %(message)s'
# log = open(os.path.join(outdir, 'log.autoreduce'), 'wt')
# log = sys.stdout
logging.basicConfig(format=FORMAT, level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger('autoreduce')
logger.info('python:   %s' % sys.executable)
logger.info('hostname: %s' % socket.gethostname())
logger.info('filename: %s' % filename)
logger.info('outdir:   %s' % outdir)

tokens = filename.split('/')
if 'ct_scans' not in tokens:
    raise NotImplementedError("Not a ct scan: %s" % filename)

staging_dir = os.path.join(outdir, 'autoreduce.CT.staging-%s' % os.path.basename(filename))
if not os.path.exists(staging_dir):
    os.makedirs(staging_dir)
os.chdir(staging_dir)

from imars3d.CT_from_TIFF_metadata import autoreduce
autoreduce(filename, local_disk_partition=outdir, parallel_nodes=16)
