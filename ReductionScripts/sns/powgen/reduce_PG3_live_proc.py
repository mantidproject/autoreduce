import mantid
from mantid import simpleapi
import os

# get information from autoreduction
cal_dir = "/SNS/PG3/shared/CALIBRATION/2017_1_2_11A_CAL/"
cal_file  = os.path.join(cal_dir, 'PG3_PAC_d37861_2017_08_08_BANK1.h5')
char_backgrounds = os.path.join(cal_dir, "PG3_char_2017_08_08-HR-PAC.txt")
char_bank1 = os.path.join(cal_dir, "PG3_char_2017_08_08-HR-BANK1.txt")

mantid.logger.information('Number events = %d' % input.getNumberEvents())

simpleapi.PDLoadCharacterizations(Filename=char_backgrounds+','+char_bank1,
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
