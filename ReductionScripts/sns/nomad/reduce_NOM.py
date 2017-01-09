import os
import sys
import shutil
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid

########## user defined parameters
resamplex=-6000
vanradius=0.58
#wavelengthMin=0.1
#wavelengthMax=2.9
calFile="/SNS/NOM/IPTS-18316/shared/NOM_calibrate_d87646_2016_12_14.h5"
charFile="/SNS/NOM/shared/CALIBRATION/2016_2_1B_CAL/NOM_char_2016_08_18-rietveld.txt"
expiniFileDefault="/SNS/lustre/NOM/IPTS-18316/shared/autoNOM/exp.ini"
# 0 means use the runs specified in the exp.ini
# -1 means turn off the correction
# specify files to be summed as a tuple or list
sampleBackRun=0
vanRun=0
vanBackRun=0
########## end of user defined parameters

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]
maxChunkSize=8.
if len(sys.argv)>3:
    maxChunkSize=float(sys.argv[3])

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
cacheDir = "/tmp" # local disk to (hopefully) reduce issues
runNumber = eventFile.split('_')[1].split('.')[0]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

# setup for MPI
if AlgorithmFactory.exists('GatherWorkspaces'):
     from mpi4py import MPI
     mpiRank = MPI.COMM_WORLD.Get_rank()
else:
     mpiRank = 0

# uncomment next line to delete cache files
#if mpiRank == 0: CleanFileCache(CacheDir=cacheDir, AgeInDays=0)

proposalDir = '/' + '/'.join(nexusDir.split('/')[1:4])
expiniFilename=os.path.join(proposalDir, 'shared', 'autoNOM', 'exp.ini')
if not os.path.exists(expiniFilename):
    expiniFilename=expiniFileDefault
print "Using", expiniFilename

# determine information for caching
wksp=LoadEventNexus(Filename=eventFileAbs, MetaDataOnly=True)
PDLoadCharacterizations(Filename=charFile,
                        ExpIniFilename=expiniFilename,
                        OutputWorkspace="characterizations")
PDDetermineCharacterizations(InputWorkspace=wksp,
                             Characterizations="characterizations",
                             BackRun=sampleBackRun,
                             NormRun=vanRun,
                             NormBackRun=vanBackRun)
DeleteWorkspace(str(wksp))
DeleteWorkspace("characterizations")
charPM = mantid.PropertyManagerDataService.retrieve('__pd_reduction_properties')

# get back the runs to use so they can be explicit in the generated python script
sampleBackRun = charPM['container'].value[0]
vanRun        = charPM['vanadium'].value[0]
vanBackRun    = charPM['vanadium_background'].value[0]

# work on container cache file
if sampleBackRun > 0:
    canWkspName="NOM_"+str(sampleBackRun)
    canProcessingProperties = ['container', 'd_min', 'd_max',
                               'tof_min', 'tof_max']
    canProcessingOtherProperties = ["ResampleX="+str(resamplex),
                                    "BackgroundSmoothParams="+str(''),
                                    "CalibrationFile="+calFile]

    (canCacheName, _) = CreateCacheFilename(Prefix=canWkspName, CacheDir=cacheDir,
                                            PropertyManager='__pd_reduction_properties',
                                            Properties=canProcessingProperties,
                                            OtherProperties=canProcessingOtherProperties)
    print "Container cache file:", canCacheName

    if os.path.exists(canCacheName):
        print "Loading container cache file '%s'" % canCacheName
        Load(Filename=canCacheName, OutputWorkspace=canWkspName)

# work on vanadium cache file
if vanRun > 0:
    vanWkspName="NOM_"+str(vanRun)
    vanProcessingProperties = ['vanadium', 'vanadium_background', 'd_min', 'd_max',
                               'tof_min', 'tof_max']
    vanProcessingOtherProperties = ["ResampleX="+str(resamplex),
                                    "VanadiumRadius="+str(vanradius),
                                    "CalibrationFile="+calFile]

    (vanCacheName, _) =  CreateCacheFilename(Prefix=vanWkspName, CacheDir=cacheDir,
                                             PropertyManager='__pd_reduction_properties',
                                             Properties=vanProcessingProperties,
                                             OtherProperties=vanProcessingOtherProperties)
    print "Vanadium cache file:", vanCacheName

    if os.path.exists(vanCacheName):
        print "Loading vanadium cache file '%s'" % vanCacheName
        Load(Filename=vanCacheName, OutputWorkspace=vanWkspName)

# process the run
SNSPowderReduction(Filename=eventFile,
                   MaxChunkSize=maxChunkSize, PreserveEvents=True,PushDataPositive='AddMinimum',
                   CalibrationFile=calFile,
                   CharacterizationRunsFile=charFile,
                   BackgroundNumber=str(sampleBackRun),
                   VanadiumNumber=str(vanRun),
                   VanadiumBackgroundNumber=str(vanBackRun),
                   ExpIniFilename=expiniFilename,
                   RemovePromptPulseWidth=50,
                   ResampleX=resamplex,
                   BinInDspace=True,
                   FilterBadPulses=25.,
                   SaveAs="gsas fullprof topas",
                   OutputDirectory=outputDir,
                   StripVanadiumPeaks=True,
                   VanadiumRadius=vanradius,
                   NormalizeByCurrent=True, FinalDataUnits="dSpacing")

# only write out thing on control job
if mpiRank == 0:
    # save out the container cache file
    if sampleBackRun > 0 and not os.path.exists(canCacheName):
        ConvertUnits(InputWorkspace=canWkspName, OutputWorkspace=canWkspName, Target="TOF")
        SaveNexusProcessed(InputWorkspace=canWkspName, Filename=canCacheName)

    # save out the vanadium cache file
    if vanRun > 0 and not os.path.exists(vanCacheName):
        ConvertUnits(InputWorkspace=vanWkspName, OutputWorkspace=vanWkspName, Target="TOF")
        SaveNexusProcessed(InputWorkspace=vanWkspName, Filename=vanCacheName)

    wksp_name = "NOM_"+runNumber

    # save the processing script
    GeneratePythonScript(InputWorkspace=wksp_name,
                     Filename=os.path.join(outputDir,wksp_name+'.py'))

    ConvertUnits(InputWorkspace=wksp_name, OutputWorkspace=wksp_name, Target="dSpacing")

    # save a picture of the normalized ritveld data
    from plotly.offline import plot
    import plotly.graph_objs as go

    banklabels = {1 : 'bank 1 - 15 deg',
                  2 : 'bank 2 - 31 deg',
                  3 : 'bank 3 - 67 deg',
                  4 : 'bank 4 - 122 deg',
                  5 : 'bank 5 - 154 deg',
                  6 : 'bank 6 - 7 deg',}
    data = []
    wksp = mtd[wksp_name]
    for i in xrange(wksp.getNumberHistograms()):
         specNum = wksp.getSpectrum(i).getSpectrumNo()
         visible = True
         if specNum in [1,6]:
             visible = 'legendonly'
         data.append(go.Scatter(x=wksp.readX(i)[:-1], y=wksp.readY(i),
                                name=banklabels[specNum], visible=visible))

    xunit = wksp.getAxis(0).getUnit()
    xlabel = '%s (%s)' % (xunit.caption(), xunit.symbol().utf8())
    layout = go.Layout(yaxis=dict(title=wksp.YUnitLabel()),
                       xaxis=dict(title=xlabel))
    fig = go.Figure(data=data, layout=layout)

    post_image = True
    if post_image:
         plotly_args = {'output_type':'div',
                        'include_plotlyjs':False}
    else:
         plotly_args = {'filename':os.path.join(outputDir, wksp_name+'.html')}

    div = plot(fig, show_link=False, **plotly_args)
    #print div
    if post_image:  # post to the plot server
         from postprocessing.publish_plot import publish_plot
         request = publish_plot('NOM', runNumber, files={'file':div})
         print "post returned %d" % request.status_code
         print "resulting document:"
         print request.text
