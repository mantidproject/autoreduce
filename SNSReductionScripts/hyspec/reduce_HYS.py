#!/usr/bin/env python

import os
import sys
from numpy import *

mantid_root = "/opt/Mantid"
mantid_bin = sys.path.append(os.path.join(mantid_root, "bin"))

from mantid.simpleapi import *

def E2V(E):
# for energy in mev returns velocity in m/s
    return sqrt(E/5.227e-6)
def SpurionPromptPulse2(Ei_meV,msd=1800.0,tail_length_us = 3000.0,talk=False):
    #More sophisticated
    dist_mm = 39000.0 + msd + 4500.0
#    T0_moderator = 4.0 + 107.0 / (1.0 + (Ei_meV / 31.0)*(Ei_meV / 31.0)*(Ei_meV / 31.0))
    T0_moderator = 0.0 
    t_focEle_us = 39000.0 / E2V(Ei_meV) * 1000.0 + T0_moderator
    t_samp_us = (dist_mm - 4500.0) / E2V(Ei_meV) * 1000.0 + T0_moderator
    t_det_us = dist_mm / E2V(Ei_meV) * 1000 + T0_moderator
    frame_start_us = t_det_us - 16667/2
    frame_end_us = t_det_us + 16667/2
    index_under_frame = divide(int(t_det_us),16667)
    pre_lead_us = 16667 * index_under_frame
    pre_tail_us = pre_lead_us + tail_length_us
    post_lead_us = 16667 * (1+ index_under_frame)
    post_tail_us = post_lead_us + tail_length_us
    E_final_meV = -1
    E_transfer_meV = -1
    # finding an ok TIB range
    MinTIB_us = 2000.0
    slop_frac = 0.2
    #print t_focEle_us,pre_lead_us,frame_start_us,MinTIB_us,slop_frac
    if (t_focEle_us < pre_lead_us) and (t_focEle_us-frame_start_us > MinTIB_us * (slop_frac + 1.0)):
        if talk:
            print 'choosing TIB just before focus element-1'
        TIB_high_us = t_focEle_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    elif (frame_start_us>pre_tail_us) and (t_focEle_us-frame_start_us > MinTIB_us * (slop_frac + 1.0)):
        if talk:
            print 'choosing TIB just before focus element-2'
        TIB_high_us = t_focEle_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    elif t_focEle_us-pre_tail_us > MinTIB_us * (slop_frac + 1.0) and (t_focEle_us-frame_start_us > MinTIB_us * (slop_frac + 1.0)):
        if talk:
            print 'choosing TIB just before focus element-3'
        TIB_high_us = t_focEle_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    elif t_samp_us-pre_tail_us > MinTIB_us * (slop_frac + 1.0) and (t_samp_us-frame_start_us > MinTIB_us * (slop_frac + 1.0)):
        if talk:
            print 'choosing TIB just before sample-1'
        TIB_high_us = t_samp_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    elif t_samp_us-pre_tail_us > MinTIB_us / 1.5 * (slop_frac + 1.0) and (t_samp_us-frame_start_us > MinTIB_us * (slop_frac + 1.0)):
        if talk:
            print 'choosing TIB just before sample-2'
        TIB_high_us = t_samp_us - MinTIB_us / 1.5 * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us / 1.5
    elif t_samp_us-pre_tail_us > MinTIB_us / 2.0 * (slop_frac + 1.0) and (t_samp_us-frame_start_us > MinTIB_us * (slop_frac + 1.0)):
        if talk:
            print 'choosing TIB just before sample-3'
        TIB_high_us = t_samp_us - MinTIB_us / 2.0 * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us / 2.0
    elif (pre_lead_us - frame_start_us > MinTIB_us * (slop_frac + 1.0)) and (t_focEle_us > pre_lead_us):
        if talk:
            print 'choosing TIB just before leading edge before elastic-1'
        TIB_high_us = pre_lead_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    elif (pre_lead_us - frame_start_us > MinTIB_us / 1.5 * (slop_frac + 1.0)) and (t_focEle_us > pre_lead_us):
        if talk:
            print 'choosing TIB just before leading edge before elastic-2'
        TIB_high_us = pre_lead_us - MinTIB_us / 1.5 * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us / 1.5
    elif (pre_lead_us - frame_start_us > MinTIB_us / 2.0 * (slop_frac + 1.0)) and (t_focEle_us > pre_lead_us):
        if talk:
            print 'choosing TIB just before leading edge before elastic-3'
        TIB_high_us = pre_lead_us - MinTIB_us / 2.0 * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us / 2.0
#    elif (pre_tail_us > frame_start_us) and (t_focEle_us - pre_tail_us > MinTIB_us * (slop_frac + 1.0)):
#        if talk:
#            print 'choosing TIB just before focus element'
#            print pre_tail_us, MinTIB_us, slop_frac
#        TIB_low_us = pre_tail_us + MinTIB_us * slop_frac / 2.0
#        TIB_high_us = TIB_low_us + MinTIB_us
    elif post_lead_us > frame_end_us:
        if talk:
            print 'choosing TIB at end of frame'
        TIB_high_us = frame_end_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    elif post_lead_us - t_det_us > MinTIB_us * (slop_frac + 1.0):
        if talk:
            print 'choosing TIB between elastic peak and later prompt pulse leading edge'
        TIB_high_us = post_lead_us - MinTIB_us * slop_frac / 2.0
        TIB_low_us = TIB_high_us - MinTIB_us
    else:
        if talk:
            print 'I cannot find a good TIB range'
        TIB_low_us = 0.0
        TIB_high_us = 0.0
    return [TIB_low_us, TIB_high_us]





nexus_file=sys.argv[1]
output_directory=sys.argv[2]




## For testing
#nexus_file="/SNS/HYS/IPTS-8018/data/HYS_11331_event.nxs"
#output_directory="/SNS/HYS/shared/autoreduce/testoutput/"

filename = os.path.split(nexus_file)[-1]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]

autows = "__auto_ws"

processed_filename = os.path.join(output_directory, "HYS_" + run_number + "_spe.nxs")
nxspe_filename=os.path.join(output_directory, "HYS_" + run_number + ".nxspe")

# Load the data
LoadEventNexus(Filename=nexus_file, OutputWorkspace=autows)
# Get Ei
Ei=mtd[autows].getRun()['EnergyRequest'].getStatistics().mean
# Get Angle
s1=mtd[autows].getRun()['s1'].getStatistics().mean

# Work out some energy bins
emin = -(2.0*Ei)
emax = Ei*0.9
estep = 0.1
energy_bins = "%f,%f,%f" % (emin,estep,emax)

#TIB limits
tib=SpurionPromptPulse2(Ei)


#reduction command
DgsReduction(SampleInputWorkspace=autows,IncidentEnergyGuess=Ei,EnergyTransferRange=energy_bins,
		GroupingFile='/SNS/HYS/IPTS-8004/shared/4x1pixels.xml', IncidentBeamNormalisation='ByCurrent',
		TimeIndepBackgroundSub='1',TibTofRangeStart=tib[0],TibTofRangeEnd=tib[1],OutputWorkspace="out")



# Save files
SaveNexus(Filename=processed_filename, InputWorkspace="out")
SaveNXSPE(Filename=nxspe_filename, InputWorkspace="out", Psi=str(s1), KiOverKfScaling='1')



