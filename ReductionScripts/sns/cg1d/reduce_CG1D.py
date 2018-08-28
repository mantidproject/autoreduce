#!/SNS/software/miniconda2/envs/py2-cg1d/bin/python

# This script is called by monitor. but it does not seem to know to use
# the correct python executable

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


# log = open(os.path.join(outdir, 'log.autoreduce'), 'wt')
log = sys.stdout
log.write('python: %s\n' % sys.executable)
log.write('hostname: %s\n' % socket.gethostname())
log.write('filename" %s\n' % filename)

here = os.path.dirname(__file__)
cmd = os.path.join(here, 'launch_autoreduce.sh')
cmd = ['bash', cmd, filename, outdir]
cmd = ' '.join(cmd)
log.write("Starting %r\n" % cmd)
import subprocess as sp, shlex
# os.system(cmd)
args = shlex.split(cmd)
sp.check_call(args, stdout=sys.stdout, stderr=sys.stdout)
