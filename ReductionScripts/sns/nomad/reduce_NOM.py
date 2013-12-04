import osimport sysimport shutil sys.path.append("/opt/mantidnightly/bin")from mantid.simpleapi import *import mantidcal_dir = "/SNS/NOM/IPTS-10924/shared"cal_file  = os.path.join(cal_dir, "autoreduce", "NOM_calibrate_d22523_2013_12_04.cal")char_file = "/SNS/NOM/shared/NOM_characterizations.txt" #os.path.join(cal_dir, "NOM_characterizations.txt")sam_back =     22527van      =     22525van_back =     22526#from mantidsimple import *eventFileAbs=sys.argv[1]outputDir=sys.argv[2]maxChunkSize=0.if len(sys.argv)>3:    maxChunkSize=float(sys.argv[3])eventFile = os.path.split(eventFileAbs)[-1]nexusDir = eventFileAbs.replace(eventFile, '')runNumber = eventFile.split('_')[1]configService = mantid.configdataSearchPath = configService.getDataSearchDirs()dataSearchPath.append(nexusDir)configService.setDataSearchDirs(";".join(dataSearchPath))SNSPowderReduction(Instrument="NOM", RunNumber=runNumber, Extension="_event.nxs",                   MaxChunkSize=maxChunkSize, PreserveEvents=True,PushDataPositive='AddMinimum',                   CalibrationFile=cal_file, CharacterizationRunsFile=char_file,                   BackgroundNumber=sam_back, VanadiumNumber=van,                   VanadiumBackgroundNumber=van_back, RemovePromptPulseWidth=50,                   ResampleX=-3000, BinInDspace=True, FilterBadPulses=True,                   SaveAs="gsas and fullprof and pdfgetn", OutputDirectory=outputDir,                   StripVanadiumPeaks=True,                   NormalizeByCurrent=True, FinalDataUnits="MomentumTransfer")