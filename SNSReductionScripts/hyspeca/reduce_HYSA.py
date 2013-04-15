#!/usr/bin/env python

import os, sys, traceback
from numpy import *
#from MaskBTP import *

mantid_root = "/opt/mantidnightly"
mantid_bin = sys.path.append(os.path.join(mantid_root, "bin"))

class AutoReduction():
  def __init__(self, nexus_file, output_directory):
    print nexus_file, output_directory
    self._nexus_file = nexus_file
    self._output_directory = output_directory 

  def E2V(self):
     # for energy in mev returns velocity in m/s
    return sqrt(self._Ei/5.227e-6)

  def SpurionPromptPulse2(self, msd = 1800.0, tail_length_us = 3000.0, talk = False):
    #More sophisticated
    dist_mm = 39000.0 + msd + 4500.0
#    T0_moderator = 4.0 + 107.0 / (1.0 + (self._Ei / 31.0)*(self._Ei / 31.0)*(self._Ei / 31.0))
    T0_moderator = 0.0 
    t_focEle_us = 39000.0 / self.E2V() * 1000.0 + T0_moderator
    t_samp_us = (dist_mm - 4500.0) / self.E2V() * 1000.0 + T0_moderator
    t_det_us = dist_mm / self.E2V() * 1000 + T0_moderator
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


  def execute(self):
    try:
      filename = os.path.split(self._nexus_file)[-1]
      instrument = filename.split('_')[0]
      run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
      out_prefix = instrument + "_" + run_number
      self._out_prefix = out_prefix
      
      # Set the output log filename
      os.environ['MANTIDLOGPATH'] = os.path.join(self._output_directory, self._out_prefix + ".log")

      # Now we can import the Mantid  
      import mantid
      from mantid.simpleapi import mtd, logger, config
      from mantid.simpleapi import LoadEventNexus, DgsReduction, SaveNexus, SaveNXSPE

      config['default.facility'] = "SNS"
      autows = "__auto_ws"
      
      processed_filename1 = os.path.join(self._output_directory, "msk_tube/" + out_prefix + "_msk_tube_spe.nxs")
      nxspe_filename1=os.path.join(self._output_directory, "msk_tube/" + out_prefix + "_msk_tube.nxspe")
      print(nxspe_filename1)

      processed_filename3 = os.path.join(self._output_directory, "4pixel/" + out_prefix + "_4pixel_spe.nxs")
      nxspe_filename3=os.path.join(self._output_directory, "4pixel/" + out_prefix + "_4pixel.nxspe")
      
      # Load the data
      LoadEventNexus(Filename=self._nexus_file, OutputWorkspace=autows)
      
      # Get Ei
      run = mtd[autows].getRun()
      if not run.hasProperty('EnergyRequest'):
        raise ValueError("EnergyRequest was not found")
      
      Ei = run['EnergyRequest'].getStatistics().mean
      self._Ei = Ei
      
      # Get Angle
      if not run.hasProperty('s1'):
        raise ValueError("s1 was not found")
      
      s1 = run['s1'].getStatistics().mean
      
      # Work out some energy bins
      emin = -(2.0 * Ei)
      emax = Ei * 0.9
      estep = 0.1
      energy_bins = "%f,%f,%f" % (emin, estep, emax)
    
      #TIB limits
      tib = self.SpurionPromptPulse2()
      
      #reduction command
      DgsReduction(SampleInputWorkspace=autows, IncidentEnergyGuess=Ei, EnergyTransferRange=energy_bins,
		GroupingFile='/SNS/HYSA/shared/autoreduce/128x1pixels.xml', IncidentBeamNormalisation='ByCurrent', HardMaskFile='/SNS/HYSA/shared/autoreduce/MonsterMask.xml',
              TimeIndepBackgroundSub='1', TibTofRangeStart=tib[0], TibTofRangeEnd=tib[1], OutputWorkspace="out1")
      
      DgsReduction(SampleInputWorkspace=autows,IncidentEnergyGuess=Ei,EnergyTransferRange=energy_bins,
		GroupingFile='/SNS/HYSA/shared/autoreduce/4x1pixels.xml',       
      IncidentBeamNormalisation='ByCurrent',
                HardMaskFile='/SNS/HYSA/shared/autoreduce/TubeTipMask.xml',
		TimeIndepBackgroundSub='1',TibTofRangeStart=tib[0],TibTofRangeEnd=tib[1],OutputWorkspace="out3")

      # Save files
      SaveNexus(Filename=processed_filename1, InputWorkspace="out1")
      SaveNXSPE(Filename=nxspe_filename1, InputWorkspace="out1", Psi=str(s1), KiOverKfScaling='1') 

      SaveNexus(Filename=processed_filename3, InputWorkspace="out3")
      SaveNXSPE(Filename=nxspe_filename3, InputWorkspace="out3", Psi=str(s1), KiOverKfScaling='1')
      
      # Clear the log filename 
      os.unsetenv('MANTIDLOGPATH')

    except RuntimeError, e:
      self.writeError()
      raise e
    except KeyError, e:
      self.writeError()
      raise e                    
    except Exception, e:
      self.writeError()
      raise e
        
  def writeError(self):
    f = open(self._output_directory + self._out_prefix + ".error", 'w')
    f.write(traceback.format_exc())
    f.close()









