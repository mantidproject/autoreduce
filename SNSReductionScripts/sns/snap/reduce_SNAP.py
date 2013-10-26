import sys,os
sys.path.append('/opt/mantidnightly/bin')
from mantid.simpleapi import *

nexus_file=sys.argv[1]
outputDir=sys.argv[2]
filename = os.path.split(nexus_file)[-1]
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number

folder = '/SNS/SNAP/IPTS-9109/shared/'

mask_dac = LoadMask(InputFile=folder+'mask_dac.xml',Instrument='SNAP' )
van = LoadNexusProcessed(Filename=folder+'nor_nexus.nxs')

binning='0.4,-0.003,3'

#######################################33


iws=LoadEventNexus(Filename=nexus_file)
iws = NormaliseByCurrent(InputWorkspace='iws')
iws = CompressEvents(InputWorkspace='iws')
ows = ConvertUnits(InputWorkspace='iws',Target='dSpacing')
ows = Rebin(InputWorkspace='ows',Params=binning,PreserveEvents='0')
ows = MaskDetectors(Workspace='ows',MaskedWorkspace='mask_dac')
ows_4 = SumNeighbours(InputWorkspace='ows',SumX='4',SumY='4')
RemoveLogs(Workspace='ows_4')

ows = SumSpectra(InputWorkspace='ows')
ows = Divide(LHSWorkspace = 'ows', RHSWorkspace = 'van')
ows_tof = ConvertUnits(InputWorkspace='ows', Target='TOF')

##############################################################3

SaveNexusProcessed(InputWorkspace='ows_4', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_inst.nxs')
SaveNexusProcessed(InputWorkspace='ows', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_nor.nxs')
SaveAscii(InputWorkspace='ows',Filename = outputDir+'/'+out_prefix+'.dat')
SaveGSS (InputWorkspace='ows_tof', Filename = outputDir+'/'+out_prefix+'.gsa',Format='SLOG', SplitFiles = '0', Append='0', MultiplyByBinWidth='1')
