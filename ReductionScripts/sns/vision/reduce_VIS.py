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
output_nexus = os.path.join(output_directory, "testing/" + out_prefix + "_inelastic-testing.nxs")

configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexus_directory)
configService.setDataSearchDirs(";".join(dataSearchPath))

# Actually do the reduction
output_ws = VisionReduction(nexus_file)

SaveNexusProcessed(InputWorkspace=output_ws,Filename=output_nexus)

# Crop the workspace for a better looking plot
CropWorkspace(InputWorkspace=output_ws, OutputWorkspace=output_ws, XMin=4.0, XMax=400.0)

SavePlot1D(InputWorkspace=output_ws, 
           OutputFilename=img_filename,
           YLabel='Intensity')

