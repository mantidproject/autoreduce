#!/usr/bin/env python

import sys,os
sys.path.append("/opt/mantidnightly/bin")

from mantid.simpleapi import *
from numpy import *

from matplotlib import *
use("agg")
from matplotlib.pyplot import *

nexus_file=sys.argv[1]
output_directory=sys.argv[2]
output_file=os.path.split(nexus_file)[-1].replace('.nxs.h5','')

w=Load(nexus_file)
LoadInstrument(w, MonitorList='-1,-2,-3', InstrumentName='CORELLI')

# Do the cross-correlation and save the file.
cc=CorelliCrossCorrelate(w,56000)
SaveNexus(cc, Filename=output_directory+output_file+"_elastic.nxs")

#Convert into Q-sample space for plotting.
MaskBTP(w,Pixel="1-10,247-256")
MaskBTP(w,Bank="49",Tube="1")
MaskBTP(w,Bank="1-9,14-30,62-71,75-91")
w=ConvertUnits(w,Target="Momentum",EMode="Elastic")
w=CropWorkspace(w,XMin=2.5,XMax=10)
SetGoniometer(w,Axis0="BL9:SampleRotation:phi,0,1,0,1") 
md=ConvertToMD(w,QDimensions="Q3D",dEAnalysisMode="Elastic",Q3DFrames="Q_sample",LorentzCorrection=1,MinValues="-20,-0.2,-20",MaxValues="20,0.2,20",Uproj='1,0,0',Vproj='0,1,0',Wproj='0,0,1')
bin=BinMD(md, AlignedDim0='Q_sample_x,-20,20,800', AlignedDim1='Q_sample_y,-0.2,0.2,1', AlignedDim2='Q_sample_z,-20,20,800')
ss=bin.getSignalArray()

#Trim array for non-zero values.
ss_where = argwhere(ss)
(ystart, xstart), (ystop,xstop) = ss_where.min(0), ss_where.max(0)+1
ss_trim = ss[ystart:ystop, xstart:xstop]

#Plot
x=arange(-20,20,0.05)
y=arange(-20,20,0.05)
X,Y=meshgrid(x[xstart:xstop],y[ystart:ystop])
Zm=ma.masked_where(ss_trim==0,ss_trim)
pcolormesh(X,Y,log(Zm),shading='gouraud')
xlabel('Qsample_x')
ylabel('Qsample_z')
savefig(output_directory+output_file+'.png',bbox_inches='tight')
clf()

#Do the same for the cross-correlated data.
"""
MaskBTP(cc,Pixel="1-10,247-256")
MaskBTP(cc,Bank="49",Tube="1")
MaskBTP(cc,Bank="1-9,14-30,62-71,75-91")
cc=ConvertUnits(cc,Target="Momentum",EMode="Elastic")
cc=CropWorkspace(cc,XMin=2.5,XMax=10)
SetGoniometer(cc,Axis0="BL9:SampleRotation:phi,0,1,0,1") 
md2=ConvertToMD(cc,QDimensions="Q3D",dEAnalysisMode="Elastic",Q3DFrames="Q_sample",LorentzCorrection=1,MinValues="-20,-0.2,-20",MaxValues="20,0.2,20",Uproj='1,0,0',Vproj='0,1,0',Wproj='0,0,1')
bin2=BinMD(md2, AlignedDim0='Q_sample_x,-20,20,800', AlignedDim1='Q_sample_y,-0.2,0.2,1', AlignedDim2='Q_sample_z,-20,20,800')
cc=bin2.getSignalArray()
cc_trim = cc[ystart:ystop, xstart:xstop]

Zm2=ma.masked_where(cc_trim<=0,cc_trim)
pcolormesh(X,Y,log(Zm2),shading='gouraud')
xlabel('Qsample_x')
ylabel('Qsample_z')
savefig(output_directory+output_file+'_elastic.png',bbox_inches='tight')
"""
