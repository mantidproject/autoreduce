#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
from numpy import *
numpy.seterr(all='ignore')

import warnings
warnings.filterwarnings('ignore',module='numpy')

peaks = [[10235,12460], [13230,14610], [8825,9450], [6700,7025]]

if __name__ == "__main__":    
    #check number of arguments
    if (len(sys.argv) != 3): 
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()
    else:
        filename = sys.argv[1]
        outdir = sys.argv[2]

    LoadEventNexus(filename, LoadMonitors=False, OutputWorkspace="DETECTOR")
    w=mtd["DETECTOR"]
    file_prefix = os.path.split(filename)[1].split('.')[0]

    nx = 304
    ny = 256
    wi=Integration(w)
    data=wi.extractY().reshape(nx,ny)
    X,Y=meshgrid(arange(nx+1), arange(ny+1))
    Z=ma.masked_where(data<.1,data)
    pcolormesh(X,Y,log(Z.transpose()))
    ylim([0,ny])
    xlim([0,nx])
    xlabel('Tube')
    ylabel('Pixel')
    

    image_file = "%s_autoreduced.png" % file_prefix
    image_path = os.path.join(outdir, image_file)
    savefig(str(image_path),bbox_inches='tight')
