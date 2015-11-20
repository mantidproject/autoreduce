######################################################################
# Python script for VISION data reduction
######################################################################
import sys
import os
import numpy
import csv
import string
import subprocess

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

fig = plt.gcf() # get current figure

plt.subplot(2,1,1)
plt.plot(ws.readX(1)[1:], ws.readY(1), "b-", label="Backwards")
plt.plot(ws.readX(2)[1:], ws.readY(2), "r-", label="Forwards")
plt.xlim(5.0, 200.0)
plt.ylabel('Intensity')
plt.legend()
plt.title(out_prefix)

ax1 = plt.subplot(2,1,2)
ax2 = ax1.twiny()
fig.subplots_adjust(bottom=0.1)

ax1.plot(ws.readX(1)[1:], ws.readY(1), "b-", label="Backwards")
ax1.set_xlim([200.0, 450.0])
ax1.set_xlabel('Energy Transfer (meV)')
ax1.set_ylabel('Intensity')

ax2.set_frame_on(True)
ax2.patch.set_visible(False)
# Move twinned axis ticks and label from top to bottom
ax2.xaxis.set_ticks_position("bottom")
ax2.xaxis.set_label_position("bottom")
ax2.spines["bottom"].set_position(("outward", 40))

ax2.plot(8.065*ws.readX(2)[1:], ws.readY(2), "r-", label="Forwards")
ax2.set_xlim([200.0*8.065, 450.0*8.065])
ax2.set_xlabel('Energy Transfer (cm-1)')

plt.tight_layout()
plt.show()

plt.savefig(img_filename)
plt.close()

