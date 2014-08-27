#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
from numpy import *
numpy.seterr(all='ignore')

import warnings
warnings.filterwarnings('ignore',module='numpy')

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

    w=LoadEventNexus(filename, LoadMonitors=True, OutputWorkspace="USANS")

    # Produce ASCII data
    w=Rebin(InputWorkspace="USANS", Params="0,10,17000")
    summed = SumSpectra(InputWorkspace="USANS")
    file_path = os.path.join(outdir, "USANS_%s_detector.txt" % run_number)
    SaveAscii(InputWorkspace=summed,Filename=file_path, WriteSpectrumID=False)


    wi=Integration(w)
    data=wi.extractY().reshape(16,128)
    data2=data[[4,0,5,1,6,2,7,3, 12,8,13,9,14,10,15,11]]
    X,Y=meshgrid(arange(17), arange(129))
    Z=ma.masked_where(data2<.1,data2)
    pcolormesh(X,Y,log(Z.transpose()))
    ylim([0,128])
    xlim([0,16])
    xlabel('Tube')
    ylabel('Pixel')
    
    run_number = w.getRunNumber()
    if run_number==0:
        image_file = os.path.split(filename)[1].split('.')[0]
        image_file += "_autoreduced.png"
    else:
        image_file = "USANS_%s_autoreduced.png" % run_number
    image_path = os.path.join(outdir, image_file)
    savefig(str(image_path),bbox_inches='tight')
