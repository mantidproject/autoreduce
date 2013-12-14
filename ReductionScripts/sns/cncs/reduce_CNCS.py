import sys,os
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from string import *

config['default.facility']="SNS"
nexus_file=sys.argv[1]
output_directory=sys.argv[2]

w=Load(nexus_file)
Ei=w.getRun()['EnergyRequest'].firstValue()
erange=str(-Ei)+','+str(0.01*Ei)+','+str(0.95*Ei)

DgsReduction(
             SampleInputFile=nexus_file,
             OutputWorkspace="reduce",
             HardMaskFile="/SNS/CNCS/shared/autoreduce/mask8bothsides.xml",
             GroupingFile='/SNS/CNCS/shared/autoreduce/CNCS_2x1.xml',
             EnergyTransferRange=erange,
             IncidentBeamNormalisation="ByCurrent",
             TimeIndepBackgroundSub=True,
             TibTofRangeStart=12000.0,
             TibTofRangeEnd=16500.0,
             DetectorVanadiumInputFile="/SNS/CNCS/IPTS-4654/18/NeXus/CNCS_71909_event.nxs",
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
s1=mtd["reduce"].getRun()['SEHOT09'].value[0]
# Save a file
SaveNexus(Filename=processed_filename, InputWorkspace="reduce")
SaveNXSPE(Filename=nxspe_filename, InputWorkspace="reduce", Psi=str(s1), KiOverKfScaling='1')
