import sys,os
sys.path.append('/opt/mantidnightly/bin')
from mantid.simpleapi import *

nexus_file=sys.argv[1]
outputDir=sys.argv[2]
filename = os.path.split(nexus_file)[-1]
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number

folder = '/SNS/SNAP/IPTS-9084/shared/'

LoadMask(InputFile=folder+'mask_edges.xml',Instrument='SNAP',OutputWorkspace='mask_edges' )
CreateGroupingWorkspace(InstrumentName='SNAP',GroupDetectorsBy='Column',OutputWorkspace='column')

van_2 = LoadNexusProcessed(Filename=r'/SNS/SNAP/IPTS-9084/shared/backgrounds/SNAP_12959_Van_2.nxs')
van_64 = LoadNexusProcessed(Filename=r'/SNS/SNAP/IPTS-9084/shared/backgrounds/SNAP_12960_Van_64.nxs')


binning='0.4,-0.002,10'

iws=LoadEventNexus(Filename=nexus_file)
ows=NormaliseByCurrent(iws)
MaskDetectors(Workspace=ows, MaskedWorkspace= 'mask_edges' )
ows=ConvertUnits(InputWorkspace='ows',Target='dSpacing',AlignBins='1')
ows=DiffractionFocussing(InputWorkspace='ows',GroupingWorkspace='column',PreserveEvents='1')
ows=Rebin(InputWorkspace='ows',Params=binning,PreserveEvents='0')
SumSpectra(InputWorkspace = ows,OutputWorkspace = 'low_d', StartWorkspaceIndex = '0',EndWorkspaceIndex='3') 
SumSpectra(InputWorkspace = ows,OutputWorkspace = 'high_d',StartWorkspaceIndex = '4',EndWorkspaceIndex='5') 
ConjoinWorkspaces(InputWorkspace1='low_d',InputWorkspace2='high_d')
RenameWorkspace(InputWorkspace='low_d', OutputWorkspace='ows')
ows=Divide(LHSWorkspace='ows',RHSWorkspace = 'van_2')
ReplaceSpecialValues(InputWorkspace='ows',OutputWorkspace='ows',NaNValue='0',NaNError='0')
SaveAscii(InputWorkspace='ows',Filename = outputDir+'/'+out_prefix+'.dat')
SaveNexusProcessed(InputWorkspace='ows', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'.nxs')

