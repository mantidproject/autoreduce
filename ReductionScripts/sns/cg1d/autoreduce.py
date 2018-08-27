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
    filename = sys.argv[1]
    outdir = sys.argv[2]+'/'
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
