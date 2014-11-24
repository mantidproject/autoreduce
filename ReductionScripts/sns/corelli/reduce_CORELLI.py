#!/usr/bin/env python

import sys,os
sys.path.append("/opt/mantidnightly/bin")

from mantid.simpleapi import *

nexus_file=sys.argv[1]
output_directory=sys.argv[2]

nexus_file="CORELLI_2605"
w=Load(nexus_file)
LoadInstrument(w, MonitorList='-1,-2,-3', InstrumentName='CORELLI')
cc=CorelliCrossCorrelate(w,56000)
SaveNexus(cc, Filename=output_directory+nexus_file+"_cc.nxs")
