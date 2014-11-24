#!/usr/bin/env python

import sys,os
sys.path.append("/opt/mantidnightly/bin")

from mantid.simpleapi import *

nexus_file=sys.argv[1]
output_directory=sys.argv[2]
output_file=os.path.split(nexus_file)[-1].replace('.nxs.h5','')

w=Load(nexus_file)
LoadInstrument(w, MonitorList='-1,-2,-3', InstrumentName='CORELLI')
cc=CorelliCrossCorrelate(w,56000)
SaveNexus(cc, Filename=output_directory+output_file+'_cc.nxs')
