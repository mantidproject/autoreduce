import os
import shutil
import re

from SET_env_scripts2 import *

# preference file - here assumed to be in the same directory as this file
preferenceFile = "mtd-VNb_30-130ms.pref"

# first argument is full path (also called absolute path) or the data file 
# second argument is the output directory
dataFile = sys.argv[1]
outputDir = sys.argv[2]

# extract information from dataFile path and filename
dataFileName = os.path.split(dataFile)[-1]
dataFilePath = dataFile.replace(dataFileName, '')
cycle = dataFilePath.split('/')[-2]
dataFileNameMinuxExt = dataFileName.split('.')[0]
runNumber = re.findall('\d+', dataFileNameMinuxExt)[0]
instrument = dataFilePath.lower().split('/')[-5].split('ndx')[1]

# copy preference file to expected location
whereCopyPrefFileTo = os.path.join(outputDir, cycle, runNumber)
if not os.path.exists(whereCopyPrefFileTo):
  os.makedirs(whereCopyPrefFileTo)
shutil.copyfile(os.path.join(os.path.dirname(__file__),preferenceFile), os.path.join(whereCopyPrefFileTo,preferenceFile))

# copy grouping directory into outputDir
if not os.path.exists(os.path.join(outputDir, "GrpOff")):
  shutil.copytree(os.path.join(os.path.dirname(__file__),"GrpOff"), os.path.join(outputDir, "GrpOff")) 

CRY_ini.EnvAnalysisdir = outputDir
expt=CRY_ini.files(instrument, RawDir=dataFilePath)

#expt.initialize(cycle,'Noriki',prefFile="mtd-VNb_30-130ms.pref")
expt.initialize(cycle, runNumber, prefFile=preferenceFile)

# Here try to overwrite pref setting to avoid entering absolute path in pref file
#expt.VanDir = dataFilePath.replace(cycle, 'cycle_12_4')   
#expt.VEmptyFile = dataFilePath.replace(cycle, 'cycle_12_4')
#expt.SEmptyFile = []

#------------------------------------
# 1) process single runs, given as 
#     a list of mubers OR ranges (raw):
# eg: "1000 1005 1250-1260" 
#    AND/OR process a range of runs merging data every n runs 
#    (checks for 0 uamps data)
# eg: "1300-1200-5"
# The two options can be used together
# 3) XOR: process several instermediate saves
# eg: s42356 1-3 5
# Optional : 
# Skip Normalization & user-defined scale, e.g:
#CRY_focus.FocusAll(expt,"1000 1005 1250-1260" , scale=100, Norm=False)
#------------------------------------
#CRY_focus.FocusAll(expt,"51806-51812 51864-51888")
#CRY_focus.FocusAll(expt,"s51805 1")

CRY_focus.FocusAll(expt, runNumber)





