import sys,os
sys.path.append('/opt/mantidnightly/bin')
from mantid.simpleapi import *

nexus_file=sys.argv[1]
outputDir=sys.argv[2]
filename = os.path.split(nexus_file)[-1]
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number

IPTS = '9109'

folder = '/SNS/SNAP/IPTS-%s/shared/'%IPTS

#LoadMask(InputFile=folder+'mask_edges.xml',Instrument='SNAP',OutputWorkspace='mask_edges' )

grp = 'banks'
if  grp == 'all': real_name = 'All'
if  grp == 'column': real_name = 'Column'
if  grp == 'banks': real_name = 'Group'
if  grp == 'modules': real_name = 'bank'
CreateGroupingWorkspace(InstrumentName ='SNAP', GroupDetectorsBy=real_name, OutputWorkspace=grp)

binning='0.4,-0.002,3'

iws=LoadEventNexus(Filename=nexus_file)
CompressEvents(InputWorkspace='SNAP_%s'%run,OutputWorkspace='SNAP_%s'%run)
ows=NormaliseByCurrent(iws)
ows=CompressEvents(ows)
ows=ConvertUnits(InputWorkspace='ows_d',Target='dSpacing',AlignBins='0')
ows=Rebin(InputWorkspace='ows_d',Params=binning,PreserveEvents='0')
ows_grp=DiffractionFocussing(InputWorkspace='ows_d',GroupingWorkspace=grp,PreserveEvents='0')
ows_16 = SumNeighbours(InputWorkspace='ows_d',SumX='16',SumY='16')
ows_sum=SumSpectra(InputWorkspace='ows_d',IncludeMonitors='0')

SaveNexusProcessed(InputWorkspace='ows_grp', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_grp.nxs')
SaveNexusProcessed(InputWorkspace='ows_16', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_16.nxs')
SaveNexusProcessed(InputWorkspace='ows_sum', Title=out_prefix, Filename = outputDir+'/'+out_prefix+'_sum.nxs')

iws = LoadEventPreNexus(EventFilename=r'/SNS/SNAP/IPTS-%s/0/%s/preNeXus/SNAP_%s_neutron1_event.dat'%(IPTS,run_number, run_number),SpectrumList='0')
LoadNexusLogs(Workspace='iws',Filename=r'/SNS/SNAP/IPTS-%s/data/SNAP_%s_event.nxs'%(IPTS,run),OverwriteLogs='1')
ows = NormaliseByCurrent(InputWorkspace='iws')
ows = Rebin(InputWorkspace='ows',Params='40,20.0,17000 ')

