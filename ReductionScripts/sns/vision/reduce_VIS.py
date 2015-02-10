######################################################################
# Python script for VISION data reduction
######################################################################
import sys
import os
import numpy
import csv
import string
import subprocess

sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
NexusFile = os.path.abspath(sys.argv[1])
FileName = NexusFile.split(os.sep)[-1]
IPTS = NexusFile.split(os.sep)[-3]
RunNumber = int(FileName.strip('VIS_').replace('.nxs.h5',''))
SaveDir = sys.argv[2]

config['defaultsave.directory'] = SaveDir
Root='/SNS/VIS/'+IPTS+'/nexus'  
config.setDataSearchDirs(Root) 


######################################################################
# Save Inelastic banks in a separate file
######################################################################
sliced_dir = os.path.join(SaveDir, "sliced_data")
if not os.path.exists(sliced_dir):
    os.umask(0002)
    os.makedirs(sliced_dir,0775)

from mantid.api import AnalysisDataService
for item in AnalysisDataService.getObjectNames():
    AnalysisDataService.remove(item)

bank_list = ["bank%d" % i for i in range(1, 15)]
bank_property = ",".join(bank_list)
LoadEventNexus(Filename=NexusFile, BankName=bank_property, OutputWorkspace="__inelastic_data", LoadMonitors=True)
inelastic_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_inelastic.nxs.h5'))
SaveNexus(InputWorkspace="__inelastic_data", Filename=inelastic_file)
Rebin(InputWorkspace='__inelastic_data_monitors',OutputWorkspace='__inelastic_data_monitors',Params="1,1,35000",PreserveEvents='0')
monitor_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_monitors.nxs.h5'))
SaveNexus(InputWorkspace="__inelastic_data_monitors", Filename=monitor_file)
AnalysisDataService.remove("__inelastic_data")
AnalysisDataService.remove("__inelastic_data_monitors")

#bank_list = ["bank%d" % i for i in range(15, 25)]
#bank_property = ",".join(bank_list)
#LoadEventNexus(Filename=NexusFile, BankName=bank_property, SingleBankPixelsOnly=False, OutputWorkspace="__elastic_back_data")
#Rebin(InputWorkspace='__elastic_back_data',OutputWorkspace='__elastic_back_data',Params="10,1,2000,-0.0005,35000",PreserveEvents='0')
#CropWorkspace(InputWorkspace='__elastic_back_data', OutputWorkspace='__elastic_back_data', StartWorkspaceIndex=14336, EndWorkspaceIndex=34815)
#elastic_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_elastic_backscattering.nxs.h5'))
#SaveNexus(InputWorkspace="__elastic_back_data", Filename=elastic_file)
#AnalysisDataService.remove("__elastic_back_data")

#bank_list = ["bank%d" % i for i in range(25, 31)]
#bank_property = ",".join(bank_list)
#LoadEventNexus(Filename=NexusFile, BankName=bank_property, SingleBankPixelsOnly=False, OutputWorkspace="__elastic_data")
#Rebin(InputWorkspace='__elastic_data',OutputWorkspace='__elastic_data',Params="10,1,2000,-0.0005,35000",PreserveEvents='0')
#elastic_file = os.path.join(sliced_dir, FileName.replace('.nxs.h5','_elastic.nxs.h5'))
#SaveNexus(InputWorkspace="__elastic_data", Filename=elastic_file)
#AnalysisDataService.remove("__elastic_data")
