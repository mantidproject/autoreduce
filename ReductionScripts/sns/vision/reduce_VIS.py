######################################################################
# Python script for VISION data reduction
######################################################################
import sys
import os
import numpy
import csv
import string
import subprocess

def mev2invcm(E):
    """convert energy in meV to Energy in cm^-1"""
    return E*8.065

def plot_dualenergy(ax,x1,y1,x2,y2,xlim):
   """ """
   ax.plot(x1,y1,"b-",label="Backwards")
   ax.plot(x2,y2,"r-",label="Forwards")
   ax2=ax.twiny()
   ax.set_xlim(xlim)
   ax2xlim=mev2invcm(numpy.array(xlim))
   x2tcks=mev2invcm(ax.get_xticks())
   ax2.set_xticks(x2tcks)
   ax2xlim=mev2invcm(numpy.array(xlim))
   ax2.set_xlim(list(ax2xlim))
   ax.set_xlabel('$\omega(meV)$')
   ax2.set_xlabel('$\omega(cm^{-1})$')
   ax.set_ylabel('Intensity')
   #ax.legend()

sys.path.append("/opt/mantidnightly/bin")
#sys.path.insert(0,'/opt/Mantid/bin')

nexus_file=sys.argv[1]
output_directory=sys.argv[2]

import mantid
from mantid.simpleapi import *

MonFile = '/SNS/VIS/shared/autoreduce/VIS_5447-5450_MonitorL-corrected-hist.nxs'

filename = os.path.split(nexus_file)[-1]
nexus_directory = nexus_file.replace(filename, '')
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number

img_filename = os.path.join(output_directory, out_prefix + ".png")
#json_filename = os.path.join(output_directory, out_prefix + ".json")
output_nexus = os.path.join(output_directory, out_prefix + "_inelastic.nxs")
output_nexus_diffraction = os.path.join(output_directory, out_prefix + "_diffraction.nxs")
output_fullprof = os.path.join(output_directory, out_prefix + "_diffraction.dat")
output_gsas = os.path.join(output_directory, out_prefix + "_diffraction.gsa")

configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexus_directory)
configService.setDataSearchDirs(";".join(dataSearchPath))

# Actually do the inelastic reduction
ws = VisionReduction(nexus_file)
# Save the Inelastic results
SaveNexusProcessed(InputWorkspace=ws,Filename=output_nexus)
# Just for testing
#ws=Load("/SNS/VIS/IPTS-14560/shared/autoreduce/testing/VIS_20942_inelastic-testing.nxs")


### Plotting 

# Let's get rid of the elastic line for plotting purposes
ws=CropWorkspace(ws, XMin=5.0, XMax=450.0)

import matplotlib
matplotlib=sys.modules['matplotlib']
matplotlib.use("agg")
import matplotlib.pyplot as plt  

plot1_limits=[5.0,200.0]
plot2_limits=[200.0,450.0]

back_x = ws.readX(0)[1:]
back_y = ws.readY(0)
front_x = ws.readX(1)[1:]
front_y = ws.readY(1)

fig = plt.gcf() # get current figure
fig.subplots_adjust(bottom=0.1)
fig.set_size_inches(8.0,10.0)
plt.figtext(0.5,0.99,out_prefix,horizontalalignment='center')
plot1=plt.subplot(3,1,1)
plot1.xaxis.set_ticks(numpy.arange(0.0,201,25.0))
plot_dualenergy(plot1,back_x,back_y,front_x,front_y,plot1_limits)
plot1.legend()

plot2=plt.subplot(3,1,2)
plot2.xaxis.set_ticks(numpy.arange(200,451,25.0))
plot_dualenergy(plot2,back_x,back_y,front_x,front_y,plot2_limits)


plt.subplots_adjust(hspace=0.4)

plt.tight_layout()
plt.show()

plt.savefig(img_filename, bbox_inches='tight')

### Diffraction Processing

dspace_binning = '0.15,-0.001,4.0'
plot3_limits=[0.15, 4.0]
monitor = Load(MonFile)
wd = LoadVisionElasticBS(nexus_file)
# Just for testing
#wd = LoadVisionElasticBS(nexus_file, banks='bank15')
AlignAndFocusPowder(InputWorkspace='wd', OutputWorkspace='wd', Params=dspace_binning, PreserveEvents=False)
ConvertUnits(InputWorkspace='wd', OutputWorkspace='wd', Target='dSpacing')
Rebin(InputWorkspace='wd', OutputWorkspace='wd', Params=dspace_binning, PreserveEvents=False)
SumSpectra(InputWorkspace='wd', OutputWorkspace='wd', IncludeMonitors=False)
ConvertUnits(InputWorkspace='wd', OutputWorkspace='wd', Target='Wavelength')

# Divide to put on flat background
Load(Filename=MonFile, OutputWorkspace='monitor')
RebinToWorkspace(WorkspaceToRebin='monitor', WorkspaceToMatch='wd', OutputWorkspace='monitor', PreserveEvents=False)
Divide(LHSWorkspace='wd', RHSWorkspace='monitor', OutputWorkspace='wd')

ConvertUnits(InputWorkspace='wd', OutputWorkspace='wd', Target='TOF')
SaveGSS(InputWorkspace='wd', Filename=output_gsas, SplitFiles=False, Append=False,\
        Format="SLOG", ExtendedHeader=True)
SaveFocusedXYE(InputWorkspace='wd', Filename=output_fullprof)

# Put final output in d-spacing
ConvertUnits(InputWorkspace='wd', OutputWorkspace='wd', Target='dSpacing')
SaveNexusProcessed(InputWorkspace='wd',Filename=output_nexus_diffraction)
wd=mtd['wd']

### Plot the Diffraction

plot3=plt.subplot(3,1,3)
plot3.plot(wd.readX(0)[1:], wd.readY(0), "g-",label="Backscattering")
plot3.set_xlabel('d-spacing (A)')
plot3.set_ylabel('Intensity')
plot3.set_xlim(plot3_limits)

plt.subplots_adjust(hspace=0.4)

plt.tight_layout()
plt.show()

plt.savefig(img_filename, bbox_inches='tight')
plt.close()

