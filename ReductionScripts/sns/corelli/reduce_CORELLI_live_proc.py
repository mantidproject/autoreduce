from mantid.simpleapi import Integration
Integration(InputWorkspace=input,OutputWorkspace=output,RangeLower=1000,RangeUpper=16666)
