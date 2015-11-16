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


#total_ws = ExtractSingleSpectrum(InputWorkspace=output_ws, WorkspaceIndex=0)
#SavePlot1DAsJson(InputWorkspace=total_ws, JsonFilename=json_filename, 
#                 PlotName=out_prefix + ' - Total Inelastic')


# Plotting 
import matplotlib
matplotlib=sys.modules['matplotlib']
matplotlib.use("agg")
import matplotlib.pyplot as plt  

fig = plt.gcf() # get current figure
plt.subplot(2,1,1)
plt.plot(ws.readX(1)[1:], ws.readY(1), "r-", label="Forwards")
plt.plot(ws.readX(2)[1:], ws.readY(2), "r-", label="Backwards")
plt.xlim(2.0, 200.0)
#plt.xlabel('Energy (meV)')
plt.ylabel('Intensity')
plt.legend()
plt.title(out_prefix)

plt.subplot(2,1,2)
plt.plot(ws.readX(1)[1:], ws.readY(1), "r-", label="Forwards")
plt.plot(ws.readX(2)[1:], ws.readY(2), "b-", label="Backwards")
plt.xlim(200.0, 450.0)
plt.xlabel('Energy (meV)')
plt.ylabel('Intensity')
plt.show()

plt.savefig(img_filename, bbox_inches='tight')
plt.close()

# Crop the workspace for a better looking plot
#low_energy_ws=ExtractSpectra(ws, Xmin=4.0, XMax=200.0, StartWorkspaceIndex=1, EndWorkspaceIndex=2)
#high_energy_ws=ExtractSpectra(ws, Xmin=200.0, XMax=450.0, StartWorkspaceIndex=1, EndWorkspaceIndex=2)

#plot_ws=GroupWorkspaces(low_energy_ws,high_energy_ws)

#SavePlot1D(InputWorkspace=plot_ws, 
#       	   OutputFilename=img_filename,
#       	   YLabel='Intensity')

