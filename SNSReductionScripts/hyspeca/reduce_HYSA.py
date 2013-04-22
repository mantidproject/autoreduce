#!/usr/bin/env python

import os, sys, traceback
from string import *
from numpy import *
#from MaskBTP import *

mantid_root = "/opt/mantidnightly"
mantid_bin = sys.path.append(os.path.join(mantid_root, "bin"))

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
      
      # Set the output log filename
      os.environ['MANTIDLOGPATH'] = os.path.join(self._output_directory, self._out_prefix + ".log")

      # Now we can import the Mantid  
      import mantid
      from mantid.simpleapi import mtd, logger, config
      from mantid.simpleapi import LoadEventNexus, DgsReduction, SaveNexus, SaveNXSPE, SuggestTibHYSPEC

      logger.notice("Starting AutoReduction for %s" % self._nexus_file)  
    
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
      tib = SuggestTibHYSPEC(Ei)
      #tib = self.SpurionPromptPulse2()
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
    #f.write(str(sys.path))
    f.close()

if __name__ == "__main__":
    #check number of arguments
    if (len(sys.argv) != 3):
        print "autoreduction code requires a filename and an output directory"
        sys.exit()
    if not(os.path.isfile(sys.argv[1])):
        print "data file ", sys.argv[1], " not found"
        sys.exit()
    else:
      print "reduce_HYSA main"
      path = sys.argv[1]
      out_dir = sys.argv[2]
      a = AutoReduction(path, out_dir)
      a.execute()










