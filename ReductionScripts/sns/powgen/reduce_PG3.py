from __future__ import (absolute_import, division, print_function)
import os
import sys
sys.path.append("/SNS/PG3/shared/autoreduce") # to get csv generation setup
from sumRun_PG3 import addLineToCsv
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid
cal_dir = '/SNS/PG3/shared/CALIBRATION/2020_1_11A_CAL/'
cal_file  = os.path.join(cal_dir,'PG3_char_2020_05_06-HighRes-PAC_1.4 MW.h5') # contains ALL grouping
char_backgrounds = os.path.join(cal_dir, "PG3_char_2020_01_04-HighRes-PAC_1.4 MW.txt")
char_inplane = os.path.join(cal_dir, "PG3_char_2020_01_04_PAC_limit_1.4MW.txt")

group_inplane = os.path.join(cal_dir, 'grouping', 'PG3_Grouping-IP.xml')
binning = -0.0008
QfitRange = [30.,50.]

eventFileAbs = sys.argv[1]
outputDir = sys.argv[2]+'/'

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
ipts = eventFileAbs.split('/')[3]
runNumber = eventFile.split('_')[1].split('.')[0]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

def clearmem(keepname=None):
    # clear out memory
    def isSpecialName(name):
        return name in ['characterizations', 'PG3_cal', 'PG3_mask']
    names = [name for name in mtd.getObjectNames()
             if not isSpecialName(name)]
    for name in names:
        if keepname is not None and name == keepname:
            continue
        DeleteWorkspace(name)

# get which guide is being used
LoadEventNexus(Filename=eventFileAbs, OutputWorkspace='PG3_'+runNumber+'_meta', MetaDataOnly=True)
guide = mtd['PG3_'+runNumber+'_meta'].run()['BL11A:Mot:Guides:Gantry.RBV'].timeAverageValue()
if abs(guide+54) < 1: # within 1mm of 54
    guide = "highresolution"
elif abs(guide-166) < 1: # within 1mm of 54
    guide = "highresolution"
else:
    guide = None
print(guide)

# second run with all pixels together - use calibration file grouping
SNSPowderReduction(Filename=eventFileAbs,
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file,
                   CharacterizationRunsFile=char_backgrounds+','+char_inplane,
                   #GroupingFile='/SNS/PG3/shared/CALIBRATION/2018_2_11A_CAL/grouping/PG3_Grouping-ALL-NoSF2.xml',
                   #OutputFilePrefix='ALL_',
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=binning, BinInDspace=True,
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=10,
                   ScaleData =100,
                   CacheDir='/tmp',
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")
GeneratePythonScript(InputWorkspace="PG3_"+runNumber,
                     Filename=os.path.join(outputDir,"PG3_"+runNumber+'.py'))

# create arbitrary normalized, correction-free S(Q)
# this is hard-coded to the wavelength log
createPDF = bool(abs(mtd['PG3_'+runNumber].run()['LambdaRequest'].value[0] - .7) < .1) or bool(abs(mtd['PG3_'+runNumber].run()['LambdaRequest'].value[0] - .8) < .1)

if createPDF:
    ConvertUnits(InputWorkspace='PG3_'+runNumber,
                 OutputWorkspace='PG3_'+runNumber+'_SQ',
                 Target='MomentumTransfer',
                 EMode='Elastic')
    mtd['PG3_'+runNumber+'_SQ'] /= 100. # should match ScaleDataParameter
    Rebin(InputWorkspace='PG3_'+runNumber+'_SQ', OutputWorkspace='PG3_'+runNumber+'_SQ',
          Params=.01)
    scale = Fit(InputWorkspace='PG3_'+runNumber+'_SQ',
                Function='name=FlatBackground,A0=1',
                StartX=QfitRange[0], EndX=QfitRange[1], Output='fittable').OutputParameters.column(1)[0]
    print('high-Q scale is', scale)
    mtd['PG3_'+runNumber+'_SQ'] /= scale
    SaveNexusProcessed(InputWorkspace='PG3_'+runNumber+'_SQ',
                       Filename=os.path.join(outputDir,'PG3_'+runNumber+'_SQ.nxs'))

    PDFFourierTransform(InputWorkspace='PG3_'+runNumber+'_SQ',
                        OutputWorkspace='PG3_'+runNumber+'_Gr',
                        Qmin=.9, QMax=30., DeltaR=.01, Rmax=100.)
    SavePDFGui(InputWorkspace='PG3_'+runNumber+'_Gr',
               Filename=os.path.join(outputDir,'PG3_'+runNumber+'.gr'))
else: 
    print('not creating S(Q)')

# interactive plots
try:
    post_image = True

    plotting_workspace_name = 'PG3_'+runNumber
    if createPDF:
        plotting_workspace_name = 'group_for_plotting'
        GroupWorkspaces(InputWorkspaces=('PG3_'+runNumber, 'PG3_'+runNumber+'_SQ', 'PG3_'+runNumber+'_Gr'),
                        OutputWorkspace=plotting_workspace_name)

    if post_image:
        html = ''
        if createPDF:
            for ws,xlabel in zip(mtd[plotting_workspace_name], ('d-spacing (A)','Q (A-1)', 'r (A)')):
                div = SavePlot1D(InputWorkspace=ws,
                                 OutputType='plotly', XLabel=xlabel)
                html += '<div>{}</div>'.format(div)
        else:
            html = SavePlot1D(InputWorkspace=plotting_workspace_name,
                             OutputType='plotly', XLabel='d-spacing (A)')
        from postprocessing.publish_plot import publish_plot
        request = publish_plot('PG3', runNumber, files={'file':html})
        print("post returned %d" % request.status_code)
        print("resulting document:")
        print(request.text)
    else:
        filename = os.path.join(outputDir, 'PG3_%s.html' % runNumber)
        SavePlot1D(InputWorkspace='PG3_'+runNumber, OutputType='plotly-full',
                   OutputFilename=filename, XLabel='d-spacing (A)')
        print('saved', filename)

    if createPDF:
        UnGroupWorkspace(InputWorkspace=plotting_workspace_name)

except ImportError:
    pass # don't worry

clearmem()

# add the line to the csv file last
addLineToCsv('PG3', eventFileAbs,
             os.path.join(outputDir, 'PG3_%s_runsummary.csv' % ipts))
