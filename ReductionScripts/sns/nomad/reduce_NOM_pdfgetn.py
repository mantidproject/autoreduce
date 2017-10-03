import os
import sys
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *  # noqa: E402
import mantid  # noqa: E402

########## user defined parameters
# these should be options that are filled in by the calling script
resamplex = -6000
wavelengthMin = 0.
wavelengthMax = 0.
calFile = "/SNS/NOM/shared/CALIBRATION/2017_2_1B_CAL/NOM_d94214_2017_07_14_shifter.h5"
charFile = "/SNS/NOM/shared/CALIBRATION/2017_1_1B_CAL/NOM_char_2017_04_15-pdf.txt"
########## end of user defined parameters

eventFileAbs = sys.argv[1]
outputDir = sys.argv[2]
maxChunkSize = 8.
if len(sys.argv) > 3:
    maxChunkSize = float(sys.argv[3])

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[1].split('.')[0]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

wksp_name = "NOM_" + str(runNumber)
PDToPDFgetN(Filename=eventFile, MaxChunkSize=maxChunkSize,
            FilterBadPulses=0.,  # TODO should change back to 25.
            CalibrationFile=calFile,
            CharacterizationRunsFile=charFile,
            RemovePromptPulseWidth=50.,
            CropWavelengthMin=wavelengthMin,
            CropWavelengthMax=wavelengthMax,
            ResampleX=resamplex,
            OutputWorkspace=wksp_name,
            PDFgetNFile=os.path.join(outputDir, wksp_name+".getn"))
