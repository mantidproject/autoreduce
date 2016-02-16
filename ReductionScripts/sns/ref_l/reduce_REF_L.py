import sys
import os
import re
import math
import time
import json
import platform
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from matplotlib import *
use("agg")
import warnings
warnings.filterwarnings('ignore',module='matplotlib')
import matplotlib.pyplot as plt
import numpy
numpy.seterr(all='ignore')

if (os.environ.has_key("MANTIDPATH")):
    del os.environ["MANTIDPATH"]
#sys.path.insert(0,'/opt/Mantid/bin')
sys.path.insert(0,'/opt/mantidnightly/bin')

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
# The legacy format is REF_L_xyz_event.nxs
# The new format is REF_L_xyz.nxs.h5
runNumber = eventFile.split('_')[2]
runNumber = runNumber.replace('.nxs.h5', '')

import mantid
from mantid.simpleapi import *


#-------------------------------------
# Reduction options
WL_CUTOFF = 10.0  # Wavelength below which we don't need the absolute normalization

# Default primary fraction range to be used if it is not defined in the template
PRIMARY_FRACTION_RANGE = [118, 197] #[121,195] #[82,154]
NORMALIZE_TO_UNITY = True #False
#-------------------------------------


sys.path.append("/SNS/REF_L/shared/autoreduce/")


# Locate the template file
# If no template file is available, the automated reduction will generate one
template_dir = outputDir.replace('/autoreduce','')
template_file = ""
if os.path.isfile("template.xml"):
    template_file = "template.xml"
elif os.path.isfile(os.path.join(template_dir, "template.xml")):
    template_file = os.path.join(template_dir, "template.xml")
elif os.path.isfile("/SNS/REF_L/shared/autoreduce/template.xml"):
    template_file = "/SNS/REF_L/shared/autoreduce/template.xml"
    
LRAutoReduction(Filename=eventFileAbs,
                ScaleToUnity=NORMALIZE_TO_UNITY,
                ScalingWavelengthCutoff=WL_CUTOFF,
                PrimaryFractionRange=PRIMARY_FRACTION_RANGE,
                OutputDirectory=outputDir,
                TemplateFile=template_file, FindPeaks=False)




# Clean up the output and produce a nice plot for the web monitor

# Load data and save selection plots
data = LoadEventNexus(Filename=eventFileAbs, MetaDataOnly=True)    
#selection_plots(data, outputDir, runNumber)



meta_data_run = meta_data.getRun()
first_run_of_set = int(runNumber)
sequence_number = 1
title = meta_data_run.getProperty("run_title").value
try:
    m=re.search("Run:(\d+)-(\d+)\.",title)
    if m is not None:
        first_run_of_set = m.group(1)
        sequence_number = int(m.group(2))
    else:
        m=re.search("-(\d+)\.",title)
        if m is not None:
            sequence_number = int(m.group(1))
            first_run_of_set = int(runNumber)-int(sequence_number)+1
        else:
            # The legacy DAS often forgets to put the sequence
            # number for the seventh run. Just assume 7.
            sequence_number = 7 # -1
            first_run_of_set = int(runNumber)-int(sequence_number)+1
except:
    sequence_number = -1
    first_run_of_set = int(runNumber)-int(sequence_number)+1
    
default_file_name = 'REFL_%s_combined_data_auto.txt' % first_run_of_set
file_path = os.path.join(outputDir, default_file_name)

output_ws = 'output_auto'

Load(Filename=file_path, OutputWorkspace=output_ws)
ReplaceSpecialValues(InputWorkspace=output_ws, OutputWorkspace=output_ws,
                     NaNValue=0.0, NaNError=0.0,
                     InfinityValue=0.0, InfinityError=0.0)    
x_data = mtd[output_ws].dataX(0)
y_data = mtd[output_ws].dataY(0)
e_data = mtd[output_ws].dataE(0)
clean_x = []
clean_y = []
clean_e = []
qmin = min(x_data)*0.95
qmax = max(x_data)*1.1
for i in range(len(y_data)):
    if y_data[i]>0 and y_data[i]>e_data[i]:
        clean_y.append(y_data[i])
        clean_x.append(x_data[i])
        clean_e.append(e_data[i])
        
if len(clean_y)>0:
    # Update json data file for interactive plotting
    file_path = os.path.join(outputDir, "REF_L_%s_plot_data.dat" % runNumber)
    if os.path.isfile(file_path):
        fd = open(file_path, 'r')
        json_data = fd.read()
        fd.close()
        data = json.loads(json_data)
        data["main_output"] = {"x":clean_x, "y":clean_y, "e": clean_e}
        json_data = json.dumps(data)
        fd = open(file_path, 'w')
        fd.write(json_data)
        fd.close()
  
    # Create image
    plt.cla()
    plt.plot(clean_x, clean_y, '-')
    plt.title('Reflectivity')
    plt.xlabel('Q')
    plt.ylabel('Reflectivity')
    plt.yscale('log')
    plt.xscale('log')
    plt.xlim(xmin=qmin, xmax=qmax)
    plt.ylim(ymax=2.0)
    plt.savefig(os.path.join(outputDir,"REF_L_"+runNumber+'.png'))
else:
    logger.notice("Nothing to plot")

