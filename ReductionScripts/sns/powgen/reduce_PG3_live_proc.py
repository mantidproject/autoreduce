import mantid
from mantid import simpleapi
import os

# get information from autoreduction
cal_dir = '/SNS/PG3/shared/CALIBRATION/2018_2_11A_CAL/'
cal_file  = os.path.join(cal_dir,'PG3_PAC_d40481_2018_06_13.h5') # contains ALL grouping
char_backgrounds = os.path.join(cal_dir, "PG3_char_2018_06_11-HighInt.txt")
char_inplane = os.path.join(cal_dir, "PG3_char_2018_05_26.txt")

mantid.logger.information('Number events = %d' % input.getNumberEvents())

simpleapi.PDLoadCharacterizations(Filename=char_backgrounds+','+char_inplane,
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
                                  Params=-0.0008,
                                  RemovePromptPulseWidth=0, # should be 50
                                  ReductionProperties='__pd_reduction_properties')
    simpleapi.ConvertUnits(InputWorkspace=output, OutputWorkspace=output,
                           Target='dSpacing', EMode='Elastic')
