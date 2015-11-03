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
sys.path.insert(0,'/opt/Mantid/bin')
#sys.path.insert(0,'/opt/mantidnightly/bin')

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[2]

import mantid
from mantid.simpleapi import *


#-------------------------------------
# Reduction options
WL_CUTOFF = 10.0  # Wavelength below which we don't need the absolute normalization
PRIMARY_FRACTION_RANGE = [118, 197] #[121,195] #[82,154]
NORMALIZE_TO_UNITY = True #False #True
#-------------------------------------



#sys.path.append("/opt/mantidnightly/scripts/Interface/")
sys.path.append("/SNS/REF_L/shared/autoreduce/")
from reduction_gui.reduction.reflectometer.refl_data_series import DataSeries
from reduce_REF_L_utilities import autoreduction_stitching, selection_plots

