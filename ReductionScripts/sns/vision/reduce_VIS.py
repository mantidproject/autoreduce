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

#sys.path.append("/opt/mantidnightly/bin")
sys.path.insert(0,'/opt/Mantid/bin')

nexus_file=sys.argv[1]
output_directory=sys.argv[2]

import mantid
from mantid.simpleapi import *

filename = os.path.split(nexus_file)[-1]
nexus_directory = nexus_file.replace(filename, '')
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number

img_filename = os.path.join(output_directory, out_prefix + ".png")
#json_filename = os.path.join(output_directory, out_prefix + ".json")
output_nexus = os.path.join(output_directory, "testing/" + out_prefix + "_inelastic-testing.nxs")

configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexus_directory)
configService.setDataSearchDirs(";".join(dataSearchPath))

# Actually do the reduction
ws = VisionReduction(nexus_file)

SaveNexusProcessed(InputWorkspace=ws,Filename=output_nexus)

########## Plotting 

# Just for testing
#ws=Load("/SNS/VIS/IPTS-14560/shared/autoreduce/testing/VIS_20942_inelastic-testing.nxs")

# Let's get rid of the elastic line for plotting purposes
ws=CropWorkspace(ws, XMin=5.0, XMax=450.0)

import matplotlib
matplotlib=sys.modules['matplotlib']
matplotlib.use("agg")
import matplotlib.pyplot as plt  

plot1_limits=[5.0,200.0]
plot2_limits=[200.0,450.0]

back_x = ws.readX(1)[1:]
back_y = ws.readY(1)
front_x = ws.readX(2)[1:]
front_y = ws.readY(2)

fig = plt.gcf() # get current figure
fig.subplots_adjust(bottom=0.1)
fig.set_size_inches(8.0,10.0)
plt.figtext(0.5,0.99,out_prefix,horizontalalignment='center')
plot1=plt.subplot(2,1,1)
plot1.xaxis.set_ticks(numpy.arange(0.0,201,25.0))
plot_dualenergy(plot1,back_x,back_y,front_x,front_y,plot1_limits)
plot1.legend()

plot2=plt.subplot(2,1,2)
plot2.xaxis.set_ticks(numpy.arange(200,451,25.0))
plot_dualenergy(plot2,back_x,back_y,front_x,front_y,plot2_limits)

plt.subplots_adjust(hspace=0.4)

plt.tight_layout()
plt.show()

plt.savefig(img_filename, bbox_inches='tight')
plt.close()

