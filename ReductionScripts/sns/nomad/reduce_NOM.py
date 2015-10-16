import hashlib
import os
import sys
import shutil
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]
maxChunkSize=8.
if len(sys.argv)>3:
    maxChunkSize=float(sys.argv[3])

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[1]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

# these should be options that are filled in by the calling script
resamplex=-6000
vanradius=0.58
wavelengthMin=0.
wavelengthMax=0.

# determine information for vanadium caching
wksp=LoadEventNexus(Filename=eventFileAbs, MetaDataOnly=True)
PDLoadCharacterizations(Filename="/SNS/NOM/shared/NOM_characterizations.txt",
                        ExpIniFilename="/SNS/NOM/IPTS-14098/shared/autoNOM2/exp.ini",
                        OutputWorkspace="characterizations")
PDDetermineCharacterizations(InputWorkspace=wksp,
                             Characterizations="characterizations")
DeleteWorkspace(str(wksp))
DeleteWorkspace("characterizations")
charPM = mantid.PropertyManagerDataService.retrieve('__pd_reduction_properties')
van_run=charPM['vanadium'].value[0]

vanProcessingProperties=['vanadium',
                         'empty',
                         'd_min',
                         'd_max',
                         'tof_min',
                         'tof_max']
vanProcessingProperties=[key+"="+charPM[key].valueAsStr for key in vanProcessingProperties]
vanProcessingProperties.append("ResampleX="+str(resamplex))
vanProcessingProperties.append("VanadiumRadius="+str(vanradius))
vanProcessingProperties.append("CropWavelengthMin="+str(wavelengthMin))
vanProcessingProperties.append("CropWavelengthMax="+str(wavelengthMax))
vanProcessingProperties=','.join(vanProcessingProperties)
print vanProcessingProperties
vanProcessingProperties=hashlib.sha1(vanProcessingProperties).hexdigest()
vanCacheName="NOM_%d_%s.nxs" % (van_run, vanProcessingProperties)
vanCacheName=os.path.join(outputDir,vanCacheName)
vanWkspName="NOM_"+str(van_run)

if os.path.exists(vanCacheName):
    print "Loading vanadium cache file '%s'" % vanCacheName
    Load(Filename=vanCacheName, OutputWorkspace=vanWkspName)

# process the run
SNSPowderReduction(Instrument="NOM", RunNumber=runNumber, Extension="_event.nxs",
                   MaxChunkSize=maxChunkSize, PreserveEvents=True,PushDataPositive='AddMinimum',
                   CalibrationFile="/SNS/NOM/IPTS-14098/shared/NOM_calibrate_d59380_2015_10_16.h5",
                   CharacterizationRunsFile="/SNS/NOM/shared/NOM_characterizations.txt",
                   ExpIniFilename="/SNS/NOM/IPTS-14098/shared/autoNOM2/exp.ini",
                   RemovePromptPulseWidth=50,
                   ResampleX=resamplex, BinInDspace=True, FilterBadPulses=25.,
                   CropWavelengthMin=wavelengthMin,
                   CropWavelengthMax=wavelengthMax,
                   SaveAs="gsas fullprof topas pdfgetn",
                   OutputDirectory=outputDir,
                   StripVanadiumPeaks=True,
                   VanadiumRadius=vanradius,
                   NormalizeByCurrent=True, FinalDataUnits="MomentumTransfer")

# save out the vanadium cache file
if not os.path.exists(vanCacheName):
    SaveNexusProcessed(InputWorkspace=vanWkspName, Filename=vanCacheName)

# save a picture of the normalized ritveld data
wksp_name="NOM_"+runNumber
SavePlot1D(InputWorkspace=wksp_name,
           OutputFilename=os.path.join(outputDir,wksp_name+'.png'),
           YLabel='Intensity')
