#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *
from numpy import *
numpy.seterr('ignore')

nexus_file=sys.argv[1]
outputDir=sys.argv[2]
filename = os.path.split(nexus_file)[-1]
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number

folder = '/SNS/SNAP/IPTS-9109/shared/'

mask_dac = LoadMask(InputFile=folder+'mask_dac.xml',Instrument='SNAP' )
van = LoadNexusProcessed(Filename=folder+'nor_nexus.nxs')

binning='0.4,-0.003,3'

#######################################33


iws=LoadEventNexus(Filename=nexus_file)
##############################################################3
## Making Detector Image for Diagnostic
##############################################################3

#MaskBTP(iws,Bank="2,3,14,13")
#iws=Integration(iws,10000,12000)
dets=iws.extractY()
banks=[11,14,17,2,5,8,10,13,16,1,4,7,9,12,15,0,3,6]
pix=256
d=dets.reshape(18,-1)[banks,:].reshape(3,-1,pix).swapaxes(1,2)[::-1,:,:].reshape(3*pix,-1)[::-1,:]
d[d<0.1]=0.1
imshow(log(d))
axis('off')
savefig(str(outputDir+'SNAP_'+str(iws.getRunNumber()) +"_autoreduced.png"),bbox_inches='tight')
##############################################################3



iws = NormaliseByCurrent(InputWorkspace='iws')
iws = CompressEvents(InputWorkspace='iws')
ows = ConvertUnits(InputWorkspace='iws',Target='dSpacing')
ows = Rebin(InputWorkspace='ows',Params=binning,PreserveEvents='0')
ows = MaskDetectors(Workspace='ows',MaskedWorkspace='mask_dac')
ows_4 = SumNeighbours(InputWorkspace='ows',SumX='4',SumY='4')
RemoveLogs(Workspace='ows_4')

ows = SumSpectra(InputWorkspace='ows')
#ows = Divide(LHSWorkspace = 'ows', RHSWorkspace = 'van')
#ows_tof = ConvertUnits(InputWorkspace='ows', Target='TOF')



#SaveNexusProcessed(InputWorkspace='ows_4', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_inst.nxs')
#SaveNexusProcessed(InputWorkspace='ows', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_nor.nxs')
#SaveAscii(InputWorkspace='ows',Filename = outputDir+'/'+out_prefix+'.dat')
#SaveGSS (InputWorkspace='ows_tof', Filename = outputDir+'/'+out_prefix+'.gsa',Format='SLOG', SplitFiles = False, Append=False, MultiplyByBinWidth='1')
##############################################################3


