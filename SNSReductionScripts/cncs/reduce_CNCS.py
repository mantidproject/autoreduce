import sys,os
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from string import *

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
             DetectorVanadiumInputFile="/SNS/CNCS/IPTS-4654/16/67155/NeXus/CNCS_67155_event.nxs",
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
