#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
from numpy import *

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
        
    w=Load(filename)
    wi=Integration(w)
    data=wi.extractY().reshape(-1,8,256).T
    data2=data[:,[0,4,1,5,2,6,3,7],:]
    data2=data2.transpose().reshape(-1,256)
    X,Y=meshgrid(arange(192)+1,arange(256)+1)
    Z=ma.masked_where(data2<1,data2)
    pcolormesh(X,Y,log(Z.transpose()))
    ylim([0,256])
    xlim([0,192])
    xlabel('Tube')
    ylabel('Pixel')
    savefig(str(outdir+'EQSANS_'+str(w.getRunNumber()) +"_autoreduced.png"),bbox_inches='tight')
    
