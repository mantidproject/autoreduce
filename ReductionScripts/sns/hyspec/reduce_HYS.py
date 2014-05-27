#!/usr/bin/env python

import os, sys, traceback
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from string import *
from numpy import *

mantid_root = "/opt/Mantid"
mantid_bin = sys.path.append(os.path.join(mantid_root, "bin"))
from mantid.simpleapi import *
from ARLibrary import *
from matplotlib import *
use("agg")
from matplotlib.pyplot import *

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
      if len(CheckForSampleLogs(Workspace=autows, LogNames='pause'))==0:
        FilterByLogValue(InputWorkspace=autows,OutputWorkspace=autows,LogName='pause',MinimumValue='-1',MaximumValue='0.5')

      # Check for sample logs
      checkResult = CheckForSampleLogs(Workspace=autows, LogNames='s1, s2, msd, EnergyRequest') 
      #print "checkResult: %s" % checkResult 
      if len(checkResult):
        raise ValueError(checkResult)
      elog=ExperimentLog()
      elog.setLogList('s2,Speed4,EnergyRequest,a1b,a1t,a1r,a1l,a2b,a2t,a2r,a2l')
      elog.setSimpleLogList('s2,Speed4,EnergyRequest,a1b,a1t,a1r,a1l,a2b,a2t,a2r,a2l')
      elog.setSERotOptions('s1')
      elog.setSETempOptions('SampleTemp, sampletemp, SensorB,SensorB340')
      elog.setFilename(self._output_directory+'experiment_log.csv')
      elog.save_line(autows)  
      
      run = mtd[autows].getRun()

      # Get Ei
      Ei = run['EnergyRequest'].getStatistics().mean
      self._Ei = Ei

  
      # Get Angle
      s1 = run['s1'].getStatistics().mean

      # Work out some energy bins
      emin = -(2.0 * Ei)
      emax = Ei * 0.9
      estep = 0.05
      if int(run_number)>38844 and int(run_number)<38904:
        Ei=24.142
        emin=-48.
        emax=0.9*24.

      energy_bins = "%f,%f,%f" % (emin, estep, emax)
      
      #get msd
      msd = run['msd'].getStatistics().mean
      #get tofmin and tofmax, and filter out anything else
      tel=(39000+msd+4500)*1000/sqrt(Ei/5.227e-6)
      tofmin=tel-1e6/120-470
      tofmax=tel+1e6/120+470
      CropWorkspace(InputWorkspace=autows,OutputWorkspace=autows,XMin=tofmin,XMax=tofmax)
      
      # Overwrite the parameters - will cause TIB to be calculated as histogram, so the output from DgsReduction is histogram
      #LoadParameterFile(Workspace=autows, Filename='/SNS/HYS/shared/autoreduce/HYSPEC_TIBasHist_Parameters.xml')
 
      #TIB limits
      tib = SuggestTibHYSPEC(Ei)
      #tib = self.SpurionPromptPulse2()
      #reduction command
      DgsReduction(SampleInputWorkspace=autows, IncidentEnergyGuess=Ei, EnergyTransferRange=energy_bins,
		SampleInputMonitorWorkspace=autows,
		GroupingFile='/SNS/HYS/shared/autoreduce/128x1pixels.xml',
		IncidentBeamNormalisation='ByCurrent', 
                HardMaskFile='/SNS/HYS/shared/autoreduce/MonsterMask.xml',
              TimeIndepBackgroundSub='1', TibTofRangeStart=tib[0], TibTofRangeEnd=tib[1], OutputWorkspace="out1")
      
      DgsReduction(SampleInputWorkspace=autows,IncidentEnergyGuess=Ei,EnergyTransferRange=energy_bins,
		SampleInputMonitorWorkspace=autows,
		GroupingFile='/SNS/HYS/shared/autoreduce/4x1pixels.xml',  
		IncidentBeamNormalisation='ByCurrent',
                #HardMaskFile='/SNS/HYS/shared/autoreduce/TubeTipMask.xml',
		TimeIndepBackgroundSub='1',TibTofRangeStart=tib[0],TibTofRangeEnd=tib[1],OutputWorkspace="out3")


      if run_number>38844 and run_number<38904:
         AddSampleLog('out1','Ei',24.,'Number')
         AddSampleLog('out3','Ei',24.,'Number')
      # Save files
      SaveNexus(Filename=processed_filename1, InputWorkspace="out1")
      SaveNXSPE(Filename=nxspe_filename1, InputWorkspace="out1", Psi=str(s1), KiOverKfScaling='1') 

      minvals,maxvals=ConvertToMDHelper('out1','|Q|','Direct')
      xmin=minvals[0]
      xmax=maxvals[0]
      xstep=(xmax-xmin)*0.01
      ymin=minvals[1]
      ymax=maxvals[1]
      ystep=(ymax-ymin)*0.01
      x=arange(xmin,xmax,xstep)
      y=arange(ymin,ymax,ystep)
      X,Y=meshgrid(x,y)


      MD=ConvertToMD('out1',QDimensions='|Q|',dEAnalysisMode='Direct',MinValues=minvals,MaxValues=maxvals)
      ad0='|Q|,'+str(xmin)+','+str(xmax)+',100'
      ad1='DeltaE,'+str(ymin)+','+str(ymax)+',100'
      MDH=BinMD(InputWorkspace=MD,AlignedDim0=ad0,AlignedDim1=ad1)
      d=MDH.getSignalArray()
      ne=MDH.getNumEventsArray()
      dne=d/ne

      Zm=ma.masked_where(ne==0,dne)
      pcolormesh(X,Y,log(Zm),shading='gouraud')
      xlabel('|Q| ($\AA^{-1}$)')
      ylabel('E (meV)')
      #imshow(log(dne[::-1]))
      #axis('off')

      savefig(processed_filename1+'.png',bbox_inches='tight')
      
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
      seterr("ignore") #ignore division by 0 warning in plots
      a = AutoReduction(path, out_dir)
      a.execute()










