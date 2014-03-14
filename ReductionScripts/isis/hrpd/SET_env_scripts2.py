from mantidsimple import *
import sys
import os
# Sets search path for scripts
sys.path.append('/britannic/gem/MantidPowderFocus/scripts2') 
#sys.path.append(os.path.join(os.path.dirname(__file__),'scripts2'))

# Sets here the path for the default Analysis-Directory
import CRY_ini  
import CRY_load 
import CRY_focus
import CRY_vana 
#CRY_ini.EnvAnalysisdir='C:/AZIZWORK/HRPD/Analysis/'
from CRY_simplefocus import * 
CRY_load.oldversion=False
print 'was here!'
