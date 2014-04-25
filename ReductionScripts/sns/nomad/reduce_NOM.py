import os
import sys
import shutil 
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
import mantid
from matplotlib import *
use("agg")
import matplotlib.pyplot as plt

cal_dir = "/SNS/NOM/IPTS-11176/shared"
cal_file  = os.path.join(cal_dir, "NOM_calibrate_d26142_2014_04_22.cal")
char_file = "/SNS/NOM/shared/NOM_characterizations.txt" #os.path.join(cal_dir, "NOM_characterizations.txt")
sam_back =     26143
van      =     26144
van_back =     26145

#from mantidsimple import *

eventFileAbs=sys.argv[1]
outputDir=sys.argv[2]
maxChunkSize=0.
#if len(sys.argv)>3:
#    maxChunkSize=float(sys.argv[3])

eventFile = os.path.split(eventFileAbs)[-1]
nexusDir = eventFileAbs.replace(eventFile, '')
runNumber = eventFile.split('_')[1]
configService = mantid.config
dataSearchPath = configService.getDataSearchDirs()
dataSearchPath.append(nexusDir)
configService.setDataSearchDirs(";".join(dataSearchPath))

SNSPowderReduction(Instrument="NOM", RunNumber=runNumber, Extension="_event.nxs",
                   MaxChunkSize=maxChunkSize, PreserveEvents=True,PushDataPositive='AddMinimum',
                   CalibrationFile=cal_file, CharacterizationRunsFile=char_file,
                   BackgroundNumber=sam_back, VanadiumNumber=van,
                   VanadiumBackgroundNumber=van_back, RemovePromptPulseWidth=50,
                   ResampleX=-3000, BinInDspace=True, FilterBadPulses=True,
                   SaveAs="gsas and fullprof and pdfgetn", OutputDirectory=outputDir,
                   StripVanadiumPeaks=True, FinalDataUnits="MomentumTransfer")

# Create the S(Q) and G(r), save out the ascii files and generate pngs
CreateGroupingWorkspace(InstrumentName="NOMAD", GroupDetectorsBy="All", OutputWorkspace="NOM_group")
samName = "NOM_"+str(runNumber)
vanName = "NOM_"+str(van)
names = [(samName, "NOM_"+str(sam_back)), (vanName, "NOM_"+str(van_back))]
for (foreground, background) in names:
  for name in (foreground, background):
    Load(name, OutputWorkspace=name)
    NormaliseByCurrent(name, OutputWorkspace=name)
  foreground = mtd[foreground]
  foreground -= mtd[background]
  DeleteWorkspace(background)
  CompressEvents(foreground, OutputWorkspace=foreground, Tolerance=.01)
  if foreground == vanName:
  	SetSampleMaterial(InputWorkspace=foreground, ChemicalFormula="V", SampleNumberDensity=0.0721)
  	MultipleScatteringCylinderAbsorption(InputWorkspace=foreground, OutputWorkspace=foreground)

  # Reduce each dataset to a single spectrum
  AlignAndFocusPowder(foreground, CalFileName=cal_file,
                      ResampleX=-3000, RemovePromptPulseWidth=50, 
                      DMin=.13, Dmax=31.42, Tmin=300, Tmax=16666.67,
                      PrimaryFlightPath=19.5, SpectrumIDs=1, L2=2, Polar=90, Azimuthal=0,
                      OutputWorkspace=foreground)
# strip peaks and such
ConvertUnits(vanName, Target="dSpacing", EMode="Elastic", OutputWorkspace=vanName)
StripVanadiumPeaks(vanName, FWHM=7, PeakPositionTolerance=.05,
                   BackgroundType="Quadratic", HighBackground=True, OutputWorkspace=vanName) 
ConvertUnits(vanName, Target="TOF", OutputWorkspace=vanName)
FFTSmooth(vanName, Filter="Butterworth",
          Params="20,2",IgnoreXBins=True,AllSpectra=True, OutputWorkspace=vanName)
SetUncertainties(vanName, OutputWorkspace=vanName)

# convert to Q
for name in (samName, vanName):
  ConvertUnits(name, OutputWorkspace=name, Target="MomentumTransfer", EMode="Elastic")
  Rebin(name, OutputWorkspace=name, Params=.02, PreserveEvents=True)

# create modestly corrected S(Q)
Divide(LHSWorkspace=samName, RHSWorkspace=vanName, OutputWorkspace=samName)
DeleteWorkspace(vanName)

# Get the high-Q function to asymptote to 1
Fit(InputWorkspace=samName, Function="name=FlatBackground,A0=1", 
	  StartX=35, EndX=48, CreateOutput=True, Output="soq")
print "high-Q asymptote:", mtd["soq_Parameters"].row(0)['Value']

single = CreateSingleValuedWorkspace(DataValue=mtd["soq_Parameters"].row(0)['Value'], ErrorValue=0)
Divide(LHSWorkspace=samName, RHSWorkspace= "single", OutputWorkspace=samName)

gr = PDFFourierTransform(samName, Qmax=40, PDFType="G(r)", DeltaR=.02, RMax=20)

SaveNexusProcessed(samName, Filename=os.path.join(outputDir, samName+"_sq.nxs"))
SaveNexusProcessed(gr, Filename=os.path.join(outputDir, samName+"_gr.nxs"))

# plot the pdf version of the data and save for the monitor
plt.clf()
sq = mtd[samName]
for i,wksp in enumerate((sq,gr)):
  plt.subplot(2,1,i)
  for j in xrange(wksp.getNumberHistograms()):
    print wksp.name()
    x = wksp.readX(j)
    y = wksp.readY(j)
    if x.size == y.size +1:
      x=(x[:-1]+x[1:])*.5
    plt.plot(x,y)
    xlabel = wksp.getAxis(0).getUnit().caption() + " (" + wksp.getAxis(0).getUnit().label() +")"
    plt.xlabel(xlabel)
plt.show()
plt.savefig(os.path.join(outputDir, "NOM_"+runNumber+'.png'),bbox_inches='tight')
