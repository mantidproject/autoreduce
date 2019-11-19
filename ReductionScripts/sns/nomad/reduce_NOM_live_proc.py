import mantid
from mantid import simpleapi
import os

cal_dir = '/SNS/NOM/shared/CALIBRATION/2017_1_1B_CAL/'
cal_file  = os.path.join(cal_dir, 'NOM_d89318_2017_03_04_cryostat.h5')
char_file = os.path.join(cal_dir, 'NOM_char_2016_12_13-rietveld.txt')
expiniFileDefault = "/SNS/NOM/IPTS-18316/shared/autoNOM/exp.ini"
expiniFilename = os.path.join('/SNS/NOM/IPTS-17982/', 'shared', 'autoNOM', 'exp.ini')
if not os.path.exists(expiniFilename):
    expiniFilename = expiniFileDefault


mantid.logger.information('Number events = %d' % input.getNumberEvents())

simpleapi.PDLoadCharacterizations(Filename=char_file,
                                  ExpIniFilename=expiniFilename,
                                  OutputWorkspace='characterizations')
simpleapi.PDDetermineCharacterizations(InputWorkspace=input,
                                       Characterizations='characterizations',
                                       ReductionProperties='__pd_reduction_properties')
manager = mantid.PropertyManagerDataService.retrieve('__pd_reduction_properties')
simpleapi.Rebin(InputWorkspace=input, OutputWorkspace=input,
                Params=(manager['tof_min'].value,100,manager['tof_max'].value))


if True: #input.getNumberEvents() > 0:
    simpleapi.AlignAndFocusPowder(InputWorkspace=input, OutputWorkspace=output,
                                  CalFilename=cal_file,
                                  ResampleX=-6000,
                                  RemovePromptPulseWidth=0, # should be 50
                                  ReductionProperties='__pd_reduction_properties')
    simpleapi.ConvertUnits(InputWorkspace=output, OutputWorkspace=output,
                           Target='dSpacing', EMode='Elastic')
