import os
import sys
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/mantidnightly/bin")
from mantid.simpleapi import *
import mantid
from matplotlib import *
cal_dir = "/SNS/PG3/shared/CALIBRATION/2016_1_11A_CAL/"
cal_file  = os.path.join(cal_dir, "PG3_OC_d28334_2016_05_25.h5")
char_file = os.path.join(cal_dir, "PG3_char_2016_05_24-HR-OC-10mm.txt")
#MODE = 0664

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]+'/'

eventFileAbs='/SNS/PG3/IPTS-15653/0/28395/NeXus/PG3_28395_event.nxs'
eventFileAbs='/SNS/PG3/IPTS-17223/nexus/PG3_29053.nxs.h5'
outputDir='/tmp'

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
import matplotlib.pyplot as plt
import plotly.offline as pltly
wksp = mtd['PG3_'+runNumber]
fig, ax = plt.subplots()
ax.plot(wksp.readX(0)[:-1], wksp.readY(0)
        #edgecolor=ec,
        #linewidth=ew*width_scale
)
ax.set_ylabel(wksp.YUnitLabel())
xunit = wksp.getAxis(0).getUnit()
ax.set_xlabel('%s (%s)' % (xunit.caption(), xunit.symbol().utf8()))
ax.grid()

if True:  # full html page
    pltly.plot_mpl(fig, show_link=False,
                   filename=os.path.join('/tmp','PG3_%s.html' % runNumber))
else:  # post to the plot server
    div = pltly.plot_mpl(fig, show_link=False,
                         output_type='div', include_plotlyjs=False)
    files = {'file':div}

    from postprocessing.publish_plot import publish_plot
    request = publish_plot('PG3', runNumber, files)
    print "post returned %d" % request.status_code
