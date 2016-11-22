import os
import sys
import shutil
import numpy

sys.path.append("/opt/mantidnightly/bin")

sys.path.insert(0,"/mnt/software/lib/python2.6/site-packages/matplotlib-1.2.0-py2.6-linux-x86_64.egg/")
from matplotlib import *                                                                                      
use("agg")                                                                                                    
import matplotlib.pyplot as plt                                                                           
numpy.seterr(all='ignore')                                                                                    
import warnings
warnings.filterwarnings('ignore',module='numpy') 

from mantid.simpleapi import *

DEFAULT_MASK_GROUP_DIR="/SNS/BSS/shared/autoreduce/new_masks_08_12_2015"
REFLECTIONS_DICT = {"silicon111": {"name": "silicon111",
                                   "energy_bins": [-120, 0.4, 120],  # micro-eV
                                   "q_bins": [0.2, 0.2, 2.0],  # inverse Angstroms
                                   "mask_file": "BASIS_Mask_default_111.xml",
                                   "parameter_file": "BASIS_silicon_111_Parameters.xml",
                                   "default_energy": 2.0826,  # mili-eV
                                   },
                    "silicon311": {"name": "silicon311",
                                   "energy_bins": [-740, 1.6, 740],
                                   "q_bins": [0.4, 0.2, 3.8],
                                   "mask_file": "BASIS_Mask_default_311.xml",
                                   "parameter_file": "BASIS_silicon_311_Parameters.xml",
                                   "default_energy": 7.6368,  # mili-eV
                                   }
                    }

nexus_file=sys.argv[1]
output_directory=sys.argv[2]

# Set up workspace names, load Event file, access handle to detector intensities
filename = os.path.split(nexus_file)[-1]
run_number = filename.split('_')[1]
autows = "__auto_ws"
autows_monitor = autows + "_monitor"
Load(Filename=nexus_file, OutputWorkspace=autows)
data=mtd[autows].extractY()[0:2520*4]
run=mtd[autows].getRun()

# Find out the appropriate reflection.
# LambdaRequest values typical of the 311 reflection are 2.95, and 3.35,
# and 6.15 and 6.4 of the 111 reflection
reflection=REFLECTIONS_DICT["silicon111"] # default
middle_gap=4.75
logname="LambdaRequest"
if run.hasProperty(logname):
    if run.getProperty(logname).value < middle_gap:
        reflection=REFLECTIONS_DICT["silicon311"]


LoadMask(Instrument='BASIS', OutputWorkspace='BASIS_MASK',
         InputFile=os.path.join(DEFAULT_MASK_GROUP_DIR, reflection["mask_file"]))
MaskDetectors(Workspace=autows, MaskedWorkspace='BASIS_MASK')
ModeratorTzeroLinear(InputWorkspace=autows,OutputWorkspace=autows)
LoadParameterFile(Workspace=autows, Filename=reflection["parameter_file"])
LoadNexusMonitors(Filename=nexus_file, OutputWorkspace=autows_monitor)
MonTemp=CloneWorkspace(autows_monitor)
ModeratorTzeroLinear(InputWorkspace=autows_monitor, OutputWorkspace=autows_monitor)
Rebin(InputWorkspace=autows_monitor,OutputWorkspace=autows_monitor,Params='10')
ConvertUnits(InputWorkspace=autows_monitor, OutputWorkspace=autows_monitor, Target='Wavelength')
OneMinusExponentialCor(InputWorkspace=autows_monitor, OutputWorkspace=autows_monitor, C='0.20749999999999999', C1='0.001276')
Scale(InputWorkspace=autows_monitor, OutputWorkspace=autows_monitor, Factor='9.9999999999999995e-07')
ConvertUnits(InputWorkspace=autows, OutputWorkspace=autows, Target='Wavelength', EMode='Indirect')
RebinToWorkspace(WorkspaceToRebin=autows, WorkspaceToMatch=autows_monitor, OutputWorkspace=autows)
Divide(LHSWorkspace=autows, RHSWorkspace=autows_monitor,  OutputWorkspace=autows)
ConvertUnits(InputWorkspace=autows, OutputWorkspace=autows, Target='DeltaE', EMode='Indirect')
CorrectKiKf(InputWorkspace=autows, OutputWorkspace=autows,EMode='Indirect')

# Save NXSPE file
logname="Ox2WeldRot"  # Discriminating property for the PSI angle
if run.hasProperty(logname):
    angle = numpy.average(run.getProperty(logname).value)
    nxspe_filename = os.path.join(output_directory, "BASIS_" + run_number + "_sqw.nxspe")
    SaveNXSPE(InputWorkspace=autows, Filename=nxspe_filename, Efixed=reflection["default_energy"],
              Psi=angle, KiOverKfScaling=1)

Rebin(InputWorkspace=autows, OutputWorkspace=autows, Params=reflection["energy_bins"])
QAxisBinning=reflection["q_bins"]
SofQW3(InputWorkspace=autows, OutputWorkspace=autows+'_sqw', QAxisBinning=QAxisBinning,
       EMode='Indirect', EFixed=reflection["default_energy"])
ClearMaskFlag(Workspace=autows+'_sqw')

# Save reduced files
dave_grp_filename = os.path.join(output_directory, "BASIS_" + run_number + "_sqw.dat")
processed_filename = os.path.join(output_directory, "BASIS_" + run_number + "_sqw.nxs")
SaveDaveGrp(Filename=dave_grp_filename, InputWorkspace=autows+'_sqw', ToMicroEV=True)
SaveNexus(Filename=processed_filename, InputWorkspace=autows+'_sqw')

# Save experiment log file
logfilename = os.path.join(output_directory, 'experiment_log.csv')
filemode = 'new'
if os.path.exists(logfilename):
    filemode = 'fastappend'
comment = mtd[autows].getComment()
AddSampleLog(autows, LogName='Comment', LogText=comment, LogType='String')
ExportExperimentLog(InputWorkspace=autows, OutputFilename=logfilename, FileMode=filemode,
                    SampleLogTitles = 'Run number,Title,Comment,StartTime,EndTime,Duration,ProtonCharge,Mean Sensor A, Min Sensor A, Max Sensor A,  Mean Sensor B, Min Sensor B, Max Sensor B, Wavelength, Chopper 1, Chopper 2, Chopper 3, Slit S1t, Slit S1b, Slit S1l, Slit S1r',
                    SampleLogNames = 'run_number,run_title,Comment,start_time,end_time,duration,gd_prtn_chrg,SensorA,SensorA,SensorA,SensorB,SensorB,SensorB,LambdaRequest,Speed1,Speed2,Speed3,s1t,s1b,s1l,s1r',
                    SampleLogOperation = '0,0,0,0,0,0,0,average,min,max,average,min,max,0,0,0,0,0,0,0,0',
                    FileFormat = 'comma (csv)',
)

# Make Figures
fig = plt.gcf()
fig.set_size_inches(8.0,16.0)

# Instrument Figure
ax1 = plt.subplot2grid((7,2), (0,0), colspan=2, rowspan=2)
bss=numpy.zeros((91,113))
try:
    b1=data[0:2520].reshape(56,45).transpose()[::-1,::-1]
    bss[0:45,0:56]=b1
    b2=data[2520:5040].reshape(56,45).transpose()[::-1,::-1]
    bss[46:91,0:56]=b2
    b3=data[5040:7560].reshape(56,45).transpose()[::-1,::-1]
    bss[0:45,57:113]=b3
    b4=data[7560:10080].reshape(56,45).transpose()[::-1,::-1]
    bss[46:91,57:113]=b4
except:
    pass
plt.imshow(numpy.log(bss))
plt.axis('off')

# Monitor Figure
ax1 = plt.subplot2grid((7,2), (2,0))
ax1.ticklabel_format(style = 'sci', axis='x',scilimits=(0,0))
#mon = mtd[autows_monitor]
x = MonTemp.readX(0)
y = MonTemp.readY(0)                                                                                          
plt.plot(x[1:],y)
plt.xlabel('TOF ($\mu$s)')
plt.ylabel('Intensity')
plt.title('Monitor')
plt.axis('on')

# Spectra Figures
autows_sqw=mtd[autows+'_sqw']
Qm,dQ,QM = [float(x) for x in QAxisBinning.split(',')]
nQ = int( (QM-Qm)/dQ )
for i in range(nQ):
    if max(autows_sqw.readY(i))<=0:
        continue
    irow=(i+1)/2+2
    icol=(i+1)%2
    ax1 = plt.subplot2grid((7,2), (irow,icol) )
    ax1.ticklabel_format(style = 'sci', axis='x',scilimits=(0,0)) 
    x = autows_sqw.readX(i)
    y = autows_sqw.readY(i)                                                                                          
    plt.plot(x[1:],y)
    plt.xlabel('Energy (meV)')
    plt.ylabel('Intensity')
    plt.yscale('log')
    plt.title('Q={0} '.format(Qm + dQ/2 + i*dQ)+"$\AA^{-1}$")

plt.tight_layout(1.08)
plt.show()
plt.savefig(processed_filename+'.png', bbox_inches='tight')
plt.close()
