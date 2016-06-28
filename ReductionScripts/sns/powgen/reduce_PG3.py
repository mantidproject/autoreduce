import os
import sys
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid
cal_dir = "/SNS/PG3/shared/CALIBRATION/2016_1_11A_CAL/"
cal_file  = os.path.join(cal_dir, "PG3_OC_d28334_2016_05_25.h5")
char_file = os.path.join(cal_dir, "PG3_char_2016_05_24-HR-OC-10mm.txt")
#MODE = 0664

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]+'/'

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[-1].split('.')[0]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

SNSPowderReduction(Filename=eventFileAbs,
                   PreserveEvents=True,PushDataPositive="AddMinimum",
                   CalibrationFile=cal_file, CharacterizationRunsFile=char_file,
                   LowResRef=0, RemovePromptPulseWidth=50,
                   Binning=-0.0008, BinInDspace=True,
                   BackgroundSmoothParams="5,2",
                   FilterBadPulses=0.,  # TODO turned off for now
                   ScaleData =100,
                   SaveAs="gsas topas and fullprof", OutputDirectory=outputDir,
                   FinalDataUnits="dSpacing")

GeneratePythonScript(InputWorkspace="PG3_"+runNumber,
                     Filename=os.path.join(outputDir,"PG3_"+runNumber+'.py'))
ConvertUnits(InputWorkspace='PG3_'+runNumber, OutputWorkspace='PG3_'+runNumber,
    Target='dSpacing',
    EMode='Elastic')

# interactive plots
from plotly.offline import plot
import plotly.graph_objs as go
wksp = mtd['PG3_'+runNumber]
trace = go.Scatter(x=wksp.readX(0)[:-1], y=wksp.readY(0))
xunit = wksp.getAxis(0).getUnit()
#xlabel = '%s (%s)' % (xunit.caption(), xunit.symbol().utf8())
xlabel = 'd-spacing'
#xlabel = '%s ($%s$)' % (xunit.caption(), xunit.symbol().latex())
layout = go.Layout(yaxis=dict(title=wksp.YUnitLabel()),
                   xaxis=dict(title=xlabel))
fig = go.Figure(data=[trace], layout=layout)

post_image = True
if post_image:
    plotly_args = {'output_type':'div',
                   'include_plotlyjs':False}
else:
    plotly_args = {'filename':os.path.join(outputDir, 'PG3_%s.html' % runNumber)}

div = plot(fig, show_link=False, **plotly_args)
print "***** begin div"
print div
print "***** end div"
if post_image:  # post to the plot server
    from postprocessing.publish_plot import publish_plot
    request = publish_plot('PG3', runNumber, files={'file':div})
    print "post returned %d" % request.status_code
    print "resulting json:"
    print request.text()
