#!/usr/bin/env python

import os, sys, traceback
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from string import *
from numpy import *

import sys,os
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *

from matplotlib import *
use("agg")
from matplotlib.pyplot import *

config['default.facility']="SNS"
nexus_file=sys.argv[1]
output_directory=sys.argv[2]

w=Load(nexus_file)
Ei=w.getRun()['EnergyRequest'].firstValue()
tib=SuggestTibCNCS(Ei)
erange=str(-Ei)+','+str(0.01*Ei)+','+str(0.95*Ei)

DgsReduction(
             SampleInputFile=nexus_file,
             OutputWorkspace="reduce",
             HardMaskFile="/SNS/CNCS/shared/autoreduce/mask8bothsides.xml",
             GroupingFile='/SNS/CNCS/shared/autoreduce/CNCS_2x1.xml',
             EnergyTransferRange=erange,
             IncidentBeamNormalisation="ByCurrent",
             TimeIndepBackgroundSub=True,
             TibTofRangeStart=tib[0],
             TibTofRangeEnd=tib[1],
             DetectorVanadiumInputFile="/SNS/CNCS/IPTS-4654/18/71909/NeXus/CNCS_71909_event.nxs",
             UseBoundsForDetVan=True,
             DetVanIntRangeLow=52000.0,
             DetVanIntRangeHigh=53000.0,
             DetVanIntRangeUnits="TOF",
            )

filename = os.path.split(nexus_file)[-1]
#run_number = filename.split('_')[1]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
processed_filename = os.path.join(output_directory, "CNCS_" + run_number + "_spe.nxs")
nxspe_filename=os.path.join(output_directory, "CNCS_" + run_number + ".nxspe")
# Get Angle
s1=mtd["reduce"].getRun()['SERotator2'].value[0]
# Save a file
SaveNexus(Filename=processed_filename, InputWorkspace="reduce")
SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce", Psi=str(s1), KiOverKfScaling='1')


minvals,maxvals=ConvertToMDHelper('reduce','|Q|','Direct')
xmin=minvals[0]
xmax=maxvals[0]
xstep=(xmax-xmin)*0.01
ymin=minvals[1]
ymax=maxvals[1]
ystep=(ymax-ymin)*0.01
x=arange(xmin,xmax,xstep)
y=arange(ymin,ymax,ystep)
X,Y=meshgrid(x,y)


MD=ConvertToMD('reduce',QDimensions='|Q|',dEAnalysisMode='Direct',MinValues=minvals,MaxValues=maxvals)
ad0='|Q|,'+str(xmin)+','+str(xmax)+',100'
ad1='DeltaE,'+str(ymin)+','+str(ymax)+',100'
MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
d=MDH.getSignalArray()
ne=MDH.getNumEventsArray()
dne=d/ne

Zm=ma.masked_where(ne==0,dne)
pcolormesh(X,Y,log(Zm),shading='gouraud')
xlabel('|Q| ($\AA^{-1}$)')
ylabel('E (meV)')
savefig(processed_filename+'.png',bbox_inches='tight')

