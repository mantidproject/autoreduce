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




def make_grp(wrk_spc_cols, low_d_mod,high_d_mod):

	low_d = SumSpectra(InputWorkspace = wrk_spc_cols,StartWorkspaceIndex = '0',EndWorkspaceIndex=str(low_d_mod-1)) 
	high_d = SumSpectra(InputWorkspace = wrk_spc_cols,StartWorkspaceIndex = str(low_d_mod),EndWorkspaceIndex=str(low_d_mod+1)) 
	output = ConjoinWorkspaces(low_d,high_d)
#	RenameWorkspace(InputWorkspace='low_d', OutputWorkspace=wrk_spc_cols.replace('_col','_grp'))
	
	return output




iws=LoadEventNexus(Filename=nexus_file)
ows=NormaliseByCurrent(iws)
MaskDetectors(Workspace=ows, MaskedWorkspace= 'mask_edges' )
ows=ConvertUnits(InputWorkspace=ows,Target='dSpacing',AlignBins='1')
ows=DiffractionFocussing(InputWorkspace=ows,GroupingWorkspace='column',PreserveEvents='0')
ows=Rebin(InputWorkspace=ows,Params=binning,PreserveEvents='0')
ows = make_grp (ows, 4,2)
# ows=Divide(LHSWorkspace=ows,RHSWorkspace = van_2)
SaveAscii(InputWorkspace=ows, Filename= outputDir+out_prefix+'.dat')
