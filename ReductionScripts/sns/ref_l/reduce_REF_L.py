import sys
import os
import warnings
warnings.simplefilter('ignore', RuntimeWarning)


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
template_file = ""
if os.path.isfile("template.xml"):
    template_file = "template.xml"
elif os.path.isfile(os.path.join(output_dir, "template.xml")):
    template_file = os.path.join(output_dir, "template.xml")
elif os.path.isfile("/SNS/REF_L/shared/autoreduce/template.xml"):
    template_file = "/SNS/REF_L/shared/autoreduce/template.xml"

# Run the auto-reduction
output = LRAutoReduction(Filename=event_file_path,
                         ScaleToUnity=NORMALIZE_TO_UNITY,
                         ScalingWavelengthCutoff=WL_CUTOFF,
                         PrimaryFractionRange=PRIMARY_FRACTION_RANGE,
                         OutputDirectory=output_dir,
                         SlitTolerance=0.06,
                         ReadSequenceFromFile=True,
                         TemplateFile=template_file, FindPeaks=False)
first_run_of_set=output[1]


#-------------------------------------------------------------------------
# Produce plot for the web monitor
default_file_name = 'REFL_%s_combined_data_auto.txt' % first_run_of_set
if os.path.isfile(default_file_name):
    reflectivity = LoadAscii(Filename=os.path.join(output_dir, default_file_name), Unit="MomentumTransfer")

    from postprocessing.publish_plot import plot1d
    x = reflectivity.readX(0)
    y = reflectivity.readY(0)
    dy = reflectivity.readE(0)
    dx = reflectivity.readDx(0)
    
    plot1d(run_number, [[x, y, dy, dx]], instrument='REF_L', 
           x_title=u"Q (1/\u212b)", x_log=True,
           y_title="Reflectivity", y_log=True, show_dx=False)


