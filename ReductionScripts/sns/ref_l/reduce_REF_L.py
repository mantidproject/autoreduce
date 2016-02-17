import sys
import os
import re
import json

if (os.environ.has_key("MANTIDPATH")):
    del os.environ["MANTIDPATH"]
#sys.path.insert(0,'/opt/Mantid/bin')
sys.path.insert(0,'/opt/mantidnightly/bin')
sys.path.append("/SNS/REF_L/shared/autoreduce/")

import mantid
from mantid.simpleapi import *

event_file_path=sys.argv[1]
output_dir=sys.argv[2]

event_file = os.path.split(event_file_path)[-1]
# The legacy format is REF_L_xyz_event.nxs
# The new format is REF_L_xyz.nxs.h5
run_number = event_file.split('_')[2]
run_number = run_number.replace('.nxs.h5', '')


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
template_dir = output_dir.replace('/autoreduce','')
template_file = ""
if os.path.isfile("template.xml"):
    template_file = "template.xml"
elif os.path.isfile(os.path.join(template_dir, "template.xml")):
    template_file = os.path.join(template_dir, "template.xml")
elif os.path.isfile("/SNS/REF_L/shared/autoreduce/template.xml"):
    template_file = "/SNS/REF_L/shared/autoreduce/template.xml"

# Run the auto-reduction
output = LRAutoReduction(Filename=event_file_path,
                         ScaleToUnity=NORMALIZE_TO_UNITY,
                         ScalingWavelengthCutoff=WL_CUTOFF,
                         PrimaryFractionRange=PRIMARY_FRACTION_RANGE,
                         OutputDirectory=output_dir,
                         TemplateFile=template_file, FindPeaks=False)
first_run_of_set=output[1]


#-------------------------------------------------------------------------
# Clean up the output and produce a nice plot for the web monitor

default_file_name = 'REFL_%s_combined_data_auto.txt' % first_run_of_set
file_path = os.path.join(output_dir, default_file_name)

output_ws = 'output_auto'
Load(Filename=file_path, OutputWorkspace=output_ws)
#ReplaceSpecialValues(InputWorkspace=output_ws, OutputWorkspace=output_ws,
#                     NaNValue=0.0, NaNError=0.0,
#                     InfinityValue=0.0, InfinityError=0.0)    
#x_data = mtd[output_ws].dataX(0)
#y_data = mtd[output_ws].dataY(0)
#e_data = mtd[output_ws].dataE(0)
clean_x = mtd[output_ws].readX(0)
clean_y = mtd[output_ws].readY(0)
clean_e = mtd[output_ws].readE(0)
#qmin = min(x_data)*0.95
#qmax = max(x_data)*1.1
#for i in range(len(y_data)):
#    if y_data[i]>0 and y_data[i]>e_data[i]:
#        clean_y.append(y_data[i])
#        clean_x.append(x_data[i])
#        clean_e.append(e_data[i])
        
# Update json data file for interactive plotting
file_path = os.path.join(output_dir, "REF_L_%s_plot_data.dat" % run_number)
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


