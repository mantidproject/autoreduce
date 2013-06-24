#!/usr/bin/env python

import os, sys, traceback
from string import *
from numpy import *

mantid_root = "/opt/Mantid"
mantid_bin = sys.path.append(os.path.join(mantid_root, "bin"))
from mantid.simpleapi import *

class AutoReduction():
  def __init__(self, nexus_file, output_directory):
    print nexus_file, output_directory
    self._nexus_file = nexus_file
    self._output_directory = output_directory 

  def execute(self):
    try:
      filename = os.path.split(self._nexus_file)[-1]
      instrument = filename.split('_')[0]
      run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
      out_prefix = instrument + "_" + run_number
      self._out_prefix = out_prefix
      
      config['default.facility'] = "SNS"
      autows = "__auto_ws"
      
      processed_filename1 = os.path.join(self._output_directory, "msk_tube/" + out_prefix + "_msk_tube_spe.nxs")
      nxspe_filename1=os.path.join(self._output_directory, "msk_tube/" + out_prefix + "_msk_tube.nxspe")
      print(nxspe_filename1)

      processed_filename3 = os.path.join(self._output_directory, "4pixel/" + out_prefix + "_4pixel_spe.nxs")
      nxspe_filename3=os.path.join(self._output_directory, "4pixel/" + out_prefix + "_4pixel.nxspe")
      
      # Load the data
      LoadEventNexus(Filename=self._nexus_file, OutputWorkspace=autows)
    
      # Check for sample logs
      checkResult = CheckForSampleLogs(Workspace=autows, LogNames='s1, s2, msd, EnergyRequest') 
      #print "checkResult: %s" % checkResult 
      if len(checkResult):
        raise ValueError(checkResult)

      run = mtd[autows].getRun()

      # Get Ei
      Ei = run['EnergyRequest'].getStatistics().mean
      self._Ei = Ei
      
      # Get Angle
      s1 = run['s1'].getStatistics().mean

      # Work out some energy bins
      emin = -(2.0 * Ei)
      emax = Ei * 0.9
      estep = 0.1
      energy_bins = "%f,%f,%f" % (emin, estep, emax)
    
      #TIB limits
      tib = SuggestTibHYSPEC(Ei)
      #tib = self.SpurionPromptPulse2()
      #reduction command
      DgsReduction(SampleInputWorkspace=autows, IncidentEnergyGuess=Ei, EnergyTransferRange=energy_bins,
		GroupingFile='/SNS/HYS/shared/autoreduce/128x1pixels.xml', IncidentBeamNormalisation='ByCurrent', HardMaskFile='/SNS/HYS/shared/autoreduce/MonsterMask.xml',
              TimeIndepBackgroundSub='1', TibTofRangeStart=tib[0], TibTofRangeEnd=tib[1], OutputWorkspace="out1")
      
      DgsReduction(SampleInputWorkspace=autows,IncidentEnergyGuess=Ei,EnergyTransferRange=energy_bins,
		GroupingFile='/SNS/HYS/shared/autoreduce/4x1pixels.xml',       
      IncidentBeamNormalisation='ByCurrent',
                HardMaskFile='/SNS/HYS/shared/autoreduce/TubeTipMask.xml',
		TimeIndepBackgroundSub='1',TibTofRangeStart=tib[0],TibTofRangeEnd=tib[1],OutputWorkspace="out3")

      # Save files
      SaveNexus(Filename=processed_filename1, InputWorkspace="out1")
      SaveNXSPE(Filename=nxspe_filename1, InputWorkspace="out1", Psi=str(s1), KiOverKfScaling='1') 

      SaveNexus(Filename=processed_filename3, InputWorkspace="out3")
      SaveNXSPE(Filename=nxspe_filename3, InputWorkspace="out3", Psi=str(s1), KiOverKfScaling='1')
      
    except Exception, e:
      raise e
        
if __name__ == "__main__":
    #check number of arguments
    if (len(sys.argv) != 3):
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()
    else:
      path = sys.argv[1]
      out_dir = sys.argv[2]
      a = AutoReduction(path, out_dir)
      a.execute()










