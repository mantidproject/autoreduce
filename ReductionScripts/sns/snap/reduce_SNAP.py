#!/usr/bin/env python
import sys,os
sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
sys.path.append("/opt/Mantid/bin")
from mantid.simpleapi import *
from matplotlib import *
# auto_Reduce_Funcs are special functions for normalization from data written by  Antonio dos Santos
from auto_Reduce_Funcs import *

use("agg")
from matplotlib.pyplot import *
from numpy import *
numpy.seterr('ignore')

nexus_file=sys.argv[1]
outputDir=sys.argv[2]
filename = os.path.split(nexus_file)[-1]
instrument = filename.split('_')[0]
run_number = os.path.splitext(os.path.splitext(filename.split('_')[1])[0])[0]
out_prefix = instrument + "_" + run_number



#in the final version folder should be obtained from the outputdir
#folder = outputDir.replace('autoreduce/','')

folder = '/SNS/SNAP/IPTS-15429/shared/'

#Masking should be one of the following strings :
# 'None' ## 'Horizontal' 
# 'Vertical' ## 'Custom mask - xml file'

Masking = "None"


#Calibration  should be one of the following strings :
# 'Convert Units' or  'Calibration File' 

Calibration = 'Convert Units'
calib_File = 'SNAP_calibrate_d30628_2016_02_19.cal'

#Grouping  should be one of the following strings :
# '2_4 Grouping' # 'All' # 'Banks' # 'Column' # 'Modules' 

Grouping = '2_4 Grouping' 

#Normalization  should be one of the following strings :
# 'None' # 'Processed Nexus' # 'Extract from Data' 

Normalization = 'Extract from Data' 
norm_file = 'nor_nexus.nxs'



binning='1.0,-0.002,16.0'

#######################################33


iws=LoadEventNexus(Filename=nexus_file)
##############################################################3
## Making Detector Image for Diagnostic
##############################################################3

##MaskBTP(iws,Bank="2,3,14,13")
##iws=Integration(iws,10000,12000)

#dets=iws.extractY()
#banks=[11,14,17,2,5,8,10,13,16,1,4,7,9,12,15,0,3,6]
#pix=256
#d=dets.reshape(18,-1)[banks,:].reshape(3,-1,pix).swapaxes(1,2)[::-1,:,:].reshape(3*pix,-1)[::-1,:]
#d[d<0.1]=0.1
#imshow(log(d))
#axis('off')
#savefig(str(outputDir+'SNAP_'+str(iws.getRunNumber()) +"_autoreduced.png"),bbox_inches='tight')
##############################################################3



iws = NormaliseByCurrent(InputWorkspace='iws')
iws = CompressEvents(InputWorkspace='iws')
iws = CropWorkspace(InputWorkspace='iws', XMax=50000)

if Calibration == 'Convert Units':
    ows = ConvertUnits(InputWorkspace='iws',Target='dSpacing')
if Calibration == 'Calibration File':
    ows = AlignDetectors(InputWorkspace='iws', CalibrationFile = folder + calib_File)

if Masking != 'None':
	
	if Masking == "Custom - xml masking file" : 
		mask_file = folder + 'mask_dac.xml'
		Mask= LoadMask(InputFile = mask_file, Instrument ='SNAP', OutputWorkspace = 'Mask')
	if Masking == "Horizontal" : 
		Mask = LoadMask(InputFile = '/SNS/SNAP/shared/libs/Horizontal_Mask.xml', Instrument ='SNAP', OutputWorkspace = 'Mask')
	if Masking == "Vertical" : 
		Mask = LoadMask(InputFile = '/SNS/SNAP/shared/libs/Vertical_Mask.xml', Instrument ='SNAP', OutputWorkspace = 'Mask')
	
	ows = MaskDetectors(Workspace='ows',MaskedWorkspace='Mask')

ows = Rebin(InputWorkspace='ows',Params=binning,PreserveEvents='0')

ows_4 = SumNeighbours(InputWorkspace='ows',SumX='4',SumY='4')
RemoveLogs(Workspace='ows_4')

grp  =  group(Grouping)
ows = DiffractionFocussing(InputWorkspace = 'ows', GroupingWorkspace= 'grp', PreserveEvents=False)


if Normalization == "Processed Nexus" :  
	norm = LoadNexusProcessed(Filename=folder+norm_file)
	ows = Divide(LHSWorkspace = 'ows', RHSWorkspace = 'norm')

if Normalization == "Extract from Data" : 
		
	window = 10 
	smooth_range = 5
				
	peak_clip_WS = CloneWorkspace('ows')
	n_histo = peak_clip_WS.getNumberHistograms()
	
	x = peak_clip_WS.extractX() 
	y = peak_clip_WS.extractY() 
	e = peak_clip_WS.extractE()

	for h in range(n_histo):

		peak_clip_WS.setX(h,x[h])
		peak_clip_WS.setY(h,peak_clip(y[h], win=window, decrese= True, LLS =True, smooth_window = smooth_range ))
		peak_clip_WS.setE(h,e[h])

	ows = Divide(LHSWorkspace = 'ows', RHSWorkspace='peak_clip_WS')



SaveNexusProcessed(InputWorkspace='ows_4', Title=out_prefix, Filename = outputDir+'/NEXUS/'+out_prefix+'_inst.nxs')
SaveNexusProcessed(InputWorkspace='ows', Title=out_prefix, Filename = outputDir+'/NEXUS/'+out_prefix+'_nor.nxs')

ows_tof = ConvertUnits(InputWorkspace='ows', Target='TOF')

print 

SaveFocusedXYE(InputWorkspace = 'ows_tof', Filename = outputDir+'/Fullprof/'+out_prefix+'.dat' , SplitFiles = True, Append=False)

SaveGSS (InputWorkspace='ows_tof', Filename = outputDir+'/GSAS/'+out_prefix+'.gsa', Format='SLOG', SplitFiles = False, Append=False, MultiplyByBinWidth='1')


##############################################################3


