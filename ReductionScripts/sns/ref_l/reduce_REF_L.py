import sys
import os
import re
import json

if (os.environ.has_key("MANTIDPATH")):
    del os.environ["MANTIDPATH"]
#sys.path.insert(0,'/opt/Mantid/bin')
sys.path.insert(0,'/opt/mantidnightly/bin')
sys.path.append("/SNS/REF_L/shared/autoreduce/")

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

# Reduction options
#-------------------------------------------------------------------------
# Wavelength below which we don't need the absolute normalization
WL_CUTOFF = 10.0  

# Default primary fraction range to be used if it is not defined in the template
PRIMARY_FRACTION_RANGE = [116, 197]

NORMALIZE_TO_UNITY = True
#-------------------------------------------------------------------------


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


_, first_run_of_set, sequence_number = LRAutoReduction(Filename=eventFileAbs,
                                                       ScaleToUnity=NORMALIZE_TO_UNITY,
                                                       ScalingWavelengthCutoff=WL_CUTOFF,
                                                       PrimaryFractionRange=PRIMARY_FRACTION_RANGE,
                                                       OutputDirectory=outputDir,
                                                       TemplateFile=template_file, FindPeaks=False)


#-------------------------------------------------------------------------
# Clean up the output and produce a nice plot for the web monitor

# Load data and save selection plots
#data = LoadEventNexus(Filename=eventFileAbs, MetaDataOnly=True)
#from reduce_REF_L_utilities import selection_plots 
#selection_plots(data, outputDir, runNumber)
    
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


