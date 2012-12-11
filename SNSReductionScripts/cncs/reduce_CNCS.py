import sys,os
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *

config['default.facility']="SNS"
nexus_file=sys.argv[1]
output_directory=sys.argv[2]

DgsReduction(
             SampleInputFile=nexus_file,
             OutputWorkspace="reduce",
             HardMaskFile="/SNS/CNCS/shared/autoreduce/mask8.xml",
             IncidentBeamNormalisation="ByCurrent",
             IncidentEnergyGuess=5.0,
             UseIncidentEnergyGuess=True,
             TimeZeroGuess=50.0,
             TimeIndepBackgroundSub=True,
             TibTofRangeStart=45000.0,
             TibTofRangeEnd=49000.0,
#             DetectorVanadiumInputFile="/SNS/CNCS/IPTS-6343/0/57514/NeXus/CNCS_57514_event.nxs",
#             UseBoundsForDetVan=True,
#             DetVanIntRangeLow=52000.0,
#             DetVanIntRangeHigh=53000.0,
#             DetVanIntRangeUnits="TOF"
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
