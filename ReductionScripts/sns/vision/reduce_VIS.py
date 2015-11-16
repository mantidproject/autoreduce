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


# Plotting 

# Let's get rid of the elastic line for plotting purposes
ws=CropWorkspace(ws, XMin=5.0)

import matplotlib
matplotlib=sys.modules['matplotlib']
matplotlib.use("agg")
import matplotlib.pyplot as plt  

fig = plt.gcf() # get current figure
plt.subplot(2,1,1)
plt.plot(ws.readX(1)[1:], ws.readY(1), "b-", label="Backwards")
plt.plot(ws.readX(2)[1:], ws.readY(2), "r-", label="Forwards")
plt.xlim(5.0, 200.0)
plt.ylim(0.0, ws.readY(1).max())
#plt.xlabel('Energy (meV)')
plt.ylabel('Intensity')
plt.legend()
plt.title(out_prefix)

plt.subplot(2,1,2)
plt.plot(ws.readX(1)[1:], ws.readY(1), "b-", label="Backwards")
plt.plot(ws.readX(2)[1:], ws.readY(2), "r-", label="Forwards")
plt.xlim(200.0, 450.0)
plt.xlabel('Energy (meV)')
plt.ylabel('Intensity')
plt.show()

plt.savefig(img_filename, bbox_inches='tight')
plt.close()

