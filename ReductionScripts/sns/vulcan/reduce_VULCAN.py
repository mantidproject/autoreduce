################################################################################
#
# Auto reduction script for VULCAN
# Input
# - Event file name with path
# - Output directory
#
# Test example: 
# 1. reduce_VULCAN.py /SNS/VULCAN/IPTS-11090/0/41703/NeXus/VULCAN_41703_event.nxs 
#                     /SNS/users/wzz/Projects/VULCAN/AutoReduction/autoreduce/Temp
#
# 2. reduce_VULCAN.py /SNS/VULCAN/IPTS-11090/0/41739/NeXus/VULCAN_41739_event.nxs 
#                     /SNS/users/wzz/Projects/VULCAN/AutoReduction/autoreduce/Temp
#
################################################################################

import os
import sys
import shutil 
import xml.etree.ElementTree as ET

#sys.path.append('/opt/mantidunstable/bin/')
sys.path.append("/opt/mantidnightly/bin")
#sys.path.append("/opt/Mantid/bin")

from mantid.simpleapi import *
import mantid

refLogTofFilename = "/SNS/VULCAN/shared/autoreduce/vdrive_log_bin.dat"
calibrationfilename = "/SNS/VULCAN/shared/autoreduce/vulcan_foc_all_2bank_11p.cal"
characterfilename = "/SNS/VULCAN/shared/autoreduce/VULCAN_Characterization_2Banks_v2.txt"

def changeOutputDir(outputdir, newsubpath=None):
    """ Change the output direction from ..../autoreduce/ to ..../logs/ 
    If the new directory does not exist, make it
    """
    # Change path from ..../autoreduce/ ... to .../logs/ 
    if outputdir.endswith("/"):
        outputdir = os.path.split(outputdir)[0]
    lastdir = os.path.split(outputdir)[-1]
    # print "Furance: last dir of output dir = %s. " % (lastdir)

    if lastdir == "autoreduce":
        if newsubpath is None: 
            modoutputdir = os.path.join(os.path.split(outputdir)[0], "logs")
        else:
            modoutputdir = os.path.join(os.path.split(outputdir)[0], str(newsubpath))
        print "Log file will be written to directory %s. " % (modoutputdir)
    else:
        modoutputdir = outputdir
        print "Log file will be written to directory %s as auto reduction service specified. " % (modoutputdir)
    
    # Create path 
    if os.path.exists(modoutputdir) is False:
        # create 
        os.mkdir(modoutputdir)

    return modoutputdir


def exportFurnaceLog(logwsname, outputDir, runNumber):
    """ Export the furnace log
    """
    logfilename = os.path.join(outputDir, "furnace%d.txt" % (runNumber))
    
    try:    
        ExportSampleLogsToCSVFile(InputWorkspace = logwsname, 
            OutputFilename = logfilename, 
            SampleLogNames = ["furnace.temp1", "furnace.temp2", "furnace.power"])
    except RuntimeError:
        raise NotImplementedError("Add an error message and skip if it happens.")

    return

def exportGenericDAQLog(logwsname, outputDir, ipts, runNumber):
    """ Export the furnace log
    """
    # Organzied by dictionary
    vulcanheaderlist = []
    vulcanheaderlist.append( ("TimeStamp"           , "")       )
    vulcanheaderlist.append( ("Time [sec]"          , "")       )
    vulcanheaderlist.append( ("Current"             , "Current"))
    vulcanheaderlist.append( ("Voltage"             , "Voltage"))
    
    # Format to lists for input
    samplelognames = []
    header = []
    for i in xrange(len(vulcanheaderlist)):
        title = vulcanheaderlist[i][0]
        logname = vulcanheaderlist[i][1]
        
        header.append(title)
        if len(logname) > 0:
            samplelognames.append(logname)
    
    headstr = ""
    for title in header: 
        headstr += "%s\t" % (title)
   
    # File name
    outputfilename = "IPTS-%d-GenericDAQ-%d.txt" % (ipts, runNumber)
    outputfilename = os.path.join(outputDir, outputfilename)
    try:    
        ExportSampleLogsToCSVFile(
            InputWorkspace = logwsname,
            OutputFilename = outputfilename,
            SampleLogNames = samplelognames,
            WriteHeaderFile = True,
            Header = headstr)
    except RuntimeError:
        print "Error in exporting Generic DAQ log for run %s. " % (str(runNumber))

    return


def exportMTSLog(logwsname, outputDir, ipts, runnumber):
    """ Export MTS log 
    List of MTS Log: 
        X       Y       Z       O       HROT    
        MTSDisplacement MTSForce        MTSStrain       MTSStress      MTSAngle      
        MTSTorque       MTSLaser        MTSlaserstrain  MTSDisplaceoffset       MTSAngleceoffset        
        MTST1   MTST2   MTST3   MTST4   FurnaceT        
        FurnaceOT       FurnacePower    VacT    VacOT
    """
    # Organzied by dictionary
    vulcanheaderlist = []
    vulcanheaderlist.append( ("TimeStamp"           , "")       )
    vulcanheaderlist.append( ("Time [sec]"          , "")       )
    vulcanheaderlist.append( ("MPTIndex"            , "loadframe.MPTIndex")     )
    vulcanheaderlist.append( ("X"                   , "X")      )
    vulcanheaderlist.append( ("Y"                   , "Y")      )
    vulcanheaderlist.append( ("Z"                   , "Z")      )
    vulcanheaderlist.append( ("O"                   , "OMEGA")  )
    vulcanheaderlist.append( ("HROT"                , "HROT")   )
    vulcanheaderlist.append( ("MTSDisplacement"     , "loadframe.displacement") )
    vulcanheaderlist.append( ("MTSForce"            , "loadframe.force")        )
    vulcanheaderlist.append( ("MTSStrain"           , "loadframe.strain")       )
    vulcanheaderlist.append( ("MTSStress"           , "loadframe.stress")       )
    vulcanheaderlist.append( ("MTSAngle"            , "loadframe.rot_angle")    )
    vulcanheaderlist.append( ("MTSTorque"           , "loadframe.torque")       )
    vulcanheaderlist.append( ("MTSLaser"            , "loadframe.laser")        )
    vulcanheaderlist.append( ("MTSlaserstrain"      , "loadframe.laserstrain")  )
    vulcanheaderlist.append( ("MTSDisplaceoffset"   , "loadframe.x_offset")     )
    vulcanheaderlist.append( ("MTSAngleceoffset"    , "loadframe.rot_offset")   )
    vulcanheaderlist.append( ("MTS1"                , "loadframe.furnace1") )
    vulcanheaderlist.append( ("MTS2"                , "loadframe.furnace2") )
    vulcanheaderlist.append( ("MTS3"                , "loadframe.extTC3") )
    vulcanheaderlist.append( ("MTS4"                , "loadframe.extTC4") )
    vulcanheaderlist.append( ("FurnaceT"            , "furnace.temp1") )
    vulcanheaderlist.append( ("FurnaceOT"           , "furnace.temp2") )
    vulcanheaderlist.append( ("FurnacePower"        , "furnace.power") )
    vulcanheaderlist.append( ("VacT"                , "partlow1.temp") )
    vulcanheaderlist.append( ("VacOT"               , "partlow2.temp") )

    # Format to lists for input
    samplelognames = []
    header = []
    for i in xrange(len(vulcanheaderlist)):
        title = vulcanheaderlist[i][0]
        logname = vulcanheaderlist[i][1]
        
        header.append(title)
        if len(logname) > 0:
            samplelognames.append(logname)
    
    headstr = ""
    for title in header: 
        headstr += "%s\t" % (title)
   
    """
    print header 
    print samplelognames
    print headstr
    """
    
    outputfilename = "IPTS-%d-MTSLoadFrame-%d.txt" % (ipts, runnumber)
    outputfilename = os.path.join(outputDir, outputfilename)
    # print "Loadframe output filename: %s" % (outputfilename)
  
    ExportSampleLogsToCSVFile(
        InputWorkspace = logwsname,
        OutputFilename = outputfilename,
        SampleLogNames = samplelognames,
        WriteHeaderFile = True,
        Header = headstr)


    return
    
RecordBase = [ 
        ("RUN",             "run_number", None),
        ("IPTS",            "IPTS", None),
        ("Title",           "run_title", None),
        ("Notes",           "Notes", None),
        ("Sample",          "Sample", None),
        ("StartTime",       "run_start", "localtime"),
        ("Duration",        "duration", None),
        ("ProtonCharge",    "protoncharge", "sum"),
        ("TotalCounts",     "das.counts", "sum"),
        ("Monitor1",        "das.monitor2counts", "sum"),
        ("Monitor2",        "das.monitor3counts", "sum"),
        ("X",               "X", "0"),
        ("Y",               "Y", "0"),
        ("Z",               "Z", "0"),
        ("O",               "Omega", "0"),       
        ("HROT",            "HROT", "0"),
        ("BandCentre",      "lambda", "0"),
        ("BandWidth",       "bandwidth", "0"),
        ("Frequency",       "skf1.speed", "0"),
        ("Guide",           "Guide", "0"),
        ("IX",              "IX", "0"),
        ("IY",              "IY", "0"),
        ("IZ",              "IZ", "0"),
        ("IHA",             "IHA", "0"),
        ("IVA",             "IVA", "0"),
        ("Collimator",      "Vcollimator", None),
        ("MTSDisplacement", "loadframe.displacement", "0"),
        ("MTSForce",        "loadframe.force", "0"),
        ("MTSStrain",       "loadframe.strain", "0"),
        ("MTSStress",       "loadframe.stress", "0"),
        ("MTSAngle",        "loadframe.rot_angle", "0"),
        ("MTSTorque",       "loadframe.torque", "0"),
        ("MTSLaser",        "loadframe.laser", "0"),
        ("MTSlaserstrain",  "loadframe.laserstrain", "0"),
        ("MTSDisplaceoffset","loadframe.x_offset", "0"),
        ("MTSAngleceoffset", "loadframe.rot_offset", "0"),
        ("MTST1",           "loadframe.furnace1", "0"),
        ("MTST2",           "loadframe.furnace2", "0"),
        ("MTST3",           "loadframe.extTC3", "0"),
        ("MTST4",           "loadframe.extTC4", "0"),
        ("FurnaceT",        "furnace.temp1", "0"),
        ("FurnaceOT",       "furnace.temp2", "0"),
        ("FurnacePower",    "furnace.power", "0"),
        ("VacT",            "partlow1.temp", "0"),
        ("VacOT",           "partlow2.temp", "0") 
        ]
        
    
class PatchRecord:
    """ A class whose task is to make patch to Record.txt generated from
    Mantid.simpleapi.ExportExperimentLog(), which may not be able to retrieve
    all information from NeXus file.  
    
    This class will not be used after all the required information/logs are 
    added to NeXus file or exported to Mantid workspace
    """
    def __init__(self, instrument, ipts, run):
        """ Init
        """
        # Generate run_info and cv_info files
        self._cvinfofname = "/SNS/%s/IPTS-%d/0/%d/preNeXus/%s_%d_cvinfo.xml" % (
            instrument, ipts, run, instrument, run)
            
        self._runinfofname = "/SNS/%s/IPTS-%d/0/%d/preNeXus/%s_%d_runinfo.xml" % (
            instrument, ipts, run, instrument, run)
            
        self._beaminfofname = "/SNS/%s/IPTS-%d/0/%d/preNeXus/%s_beamtimeinfo.xml" % (
            instrument, ipts, run, instrument)
            
        # Verify whether these 2 files are accessible
        if os.path.exists(self._cvinfofname) is False or os.path.exists(self._runinfofname) is False or os.path.exists(self._beaminfofname) is False:
            raise NotImplementedError("PreNexus log file %s and/or %s cannot be accessed. " % (
                self._cvinfofname, self._runinfofname))

        return
        
    def patchRecord(self, recordfilename):
        """ Patch record
        """
        # Get last line
        titleline, lastline = self._getLastLine(recordfilename)

        # print "First line: ", titleline
        # print "Last line: ", lastline
        
        # Parse last line and first line
        rtitles = titleline.split("\t")
        titles = []
        for title in rtitles:
            title = title.strip()
            titles.append(title)
        
        values = lastline.split("\t")
        
        valuedict = {}
        if len(titles) != len(values):
            raise NotImplementedError("Number of tiles are different than number of values.")
        for itit in xrange(len(titles)):
            valuedict[titles[itit]] = values[itit]
            
        # Substitute
        ipts = self._getIPTS()
        cvdict = self._readCvInfoFile()
        rundict = self._readRunInfoFile()
        
        valuedict["IPTS"] = "%s" % (str(ipts))
        for title in cvdict.keys():
            valuedict[title] = cvdict[title]
        
        # print valuedict.keys()
        
        for title in rundict.keys():
            valuedict[title] = rundict[title]
        
        # Form the line again: with 7 spaces in front
        newline = "       "
        for i in xrange(len(titles)):
            title = titles[i]
            if i > 0:
                newline += "\t"
            newline += "%s" % (str(valuedict[title]))
        
        # Remove last line and append the patched line
        self._removeLastLine(recordfilename)
        
        with open(recordfilename, "a") as myfile:
            myfile.write("\n"+newline)
        
        return
        
    
    def _getLastLine(self, filename):
        """ Get the last line of a (possibly long) file
        """
        with open(filename, 'rb') as fh:
            # Determine a rougly size of a line
            firstline = next(fh).decode().strip()
            secondline = next(fh).decode().strip()
            linesize = len(secondline)
            
            # print "Title line:  ", firstline 
            # print "Second line: ", secondline 
           
	    try: 
		fh.seek(-2*linesize, 2)
            	lastline = fh.readlines()[-1].decode().strip()
		fh.close()
	    except IOError as err:
                # File is short
		fh.close()
		fh = open(filename, 'rb')
                lines = fh.readlines()
                lastline = lines[-1] 

        #print lastline 
        return (firstline, lastline)
    
    def _removeLastLine(self, filename):
        """ Remove last line
        """
        import sys
        import os

        #ifile = open(sys.argv[1], "r+", encoding = "utf-8")
        ifile = open(filename, "r+")

        ifile.seek(0, os.SEEK_END)
        pos = ifile.tell() - 1
        while pos > 0 and ifile.read(1) != "\n":
            pos -= 1
            ifile.seek(pos, os.SEEK_SET)

        if pos > 0:
            ifile.seek(pos, os.SEEK_SET)
            ifile.truncate()

        ifile.close()
    
        return
        
    def _getIPTS(self):
        """ Get IPTS 
        """
        tree = ET.parse(self._beaminfofname)

        root = tree.getroot()
        if root.tag != 'Instrument':
            raise NotImplementedError("Not an instrument")

        proposal = None
        for child in root:
            if child.tag == "Proposal":
                proposal = child
                break
        if proposal is None:
            raise NotImplementedError("Not have proposal")

        id = None
        for child in proposal:
            if child.tag == "ID":
                id = child
                break
        if id is None:
            raise NotImplementedError("No ID")
            
        ipts = id.text
            
        return ipts
        
    def _readCvInfoFile(self):
        """ read CV info
        """
        cvinfodict = {}
        
        # Parse the XML file to tree    
        tree = ET.parse(self._cvinfofname)
        root = tree.getroot()

        # Find "DAS_process"
        das_process = None
        for child in root:
            if child.tag == "DAS_process":
                das_process = child
        if das_process is None:
            raise NotImplementedError("DAS_process is not in cv_info.")    

        # Parse all the entries to a dictionary
        attribdict = {}
        for child in das_process:
            attrib = child.attrib
            name = attrib['name']
            value = attrib['value']
            attribdict[name] = value

        name = "das.neutrons"
        if attribdict.has_key(name): 
            cvinfodict["TotalCounts"] = attribdict[name]
            
        name = "das.protoncharge"
        if attribdict.has_key(name): 
            cvinfodict["ProtonCharge"] = attribdict[name]
            
        name = "das.runtime"
        if attribdict.has_key(name): 
            cvinfodict["Duration(sec)"] = attribdict[name]
            
        name = "das.monitor2counts"
        if attribdict.has_key(name): 
            cvinfodict["Monitor1"] = attribdict[name]
            
        name = "das.monitor3counts"
        if attribdict.has_key(name): 
            cvinfodict["Monitor2"] = attribdict[name]
        
        return cvinfodict
        
    def _readRunInfoFile(self):
        """ Read Run info file
        """
        runinfodict = {}
        
        tree = ET.parse(self._runinfofname)
        root = tree.getroot()

        # Get SampleInfo and GenerateInfo node
        sampleinfo = None
        generalinfo = None
        for child in root:
            if child.tag == "SampleInfo":
                sampleinfo = child
            elif child.tag == "GeneralInfo":
                generalinfo = child
        
        if sampleinfo is None:
            raise NotImplementedError("SampleInfo is missing.")
        if generalinfo is None:
            raise NotImplementedError("GeneralInfo is missing.")

        for child in sampleinfo:
            if child.tag == "SampleDescription":
                sampledes = child
                runinfodict["Sample"] = sampledes.text.replace("\n", " ")
                break

        for child in generalinfo:
            if child.tag == "Notes":
                origtext = child.text
                if origtext is None:
                    runinfodict["Notes"] = "(No Notes)"
                else: 
                    runinfodict["Notes"] = child.text.replace("\n", " ")
                break
                
        return runinfodict
        
# ENDCLASS


def generateRecordFormat():
    """
    """
    sampletitles = []
    samplenames = []
    sampleoperations = []
    for ib in xrange(len(RecordBase)):
        sampletitles.append(RecordBase[ib][0])
        samplenames.append(RecordBase[ib][1])
        sampleoperations.append(RecordBase[ib][2])
    
    return (sampletitles, samplenames, sampleoperations)
    

def write_record(wsname, instrument, ipts, run, rfilename):
    """ Write the run info to a record file
    """
    # Convert the record base to input arrays
    sampletitles, samplenames, sampleoperations = generateRecordFormat()
    
    # Load NeXus file
    # eventnexus = "/SNS/%s/IPTS-%d/0/%d/NeXus/%s_%d_event.nxs" % (instrument, ipts, run, instrument, run)


    """
    try:
        Load(Filename = eventnexus, OutputWorkspace = wsname, 
                LoadLogs = True, MetaDataOnly = True)
    except RuntimeError as err:
        print "Unable to load NeXus file %s. Error message: %s. " % (eventnexus, str(err))
        return False
    """

    # Determine mode
    if os.path.exists(rfilename) is True:
        filemode = "fastappend"
    else:
        filemode = "new"

    print "Output record file will be written to %s. " % (rfilename)

    # Write log
    ExportExperimentLog(InputWorkspace = wsname, 
            OutputFilename     = rfilename, 
            FileMode           = filemode, 
            SampleLogNames     = samplenames, 
            SampleLogTitles    = sampletitles, 
            SampleLogOperation = sampleoperations, 
            TimeZone           = "America/New_York")
    
    # Patch for logs that do not exist in event NeXus yet
    testclass = PatchRecord(instrument, ipts, run)
    testclass.patchRecord(rfilename)
    
    return True

def saveGSASFile(ipts, runnumber, outputdir):
    """ Save for Nexus file
    """
    import os
    
    SNSPowderReduction( 
            Instrument  = "VULCAN",
            RunNumber   = runnumber,
            Extension   = "_event.nxs",
            PreserveEvents  = True,
            CalibrationFile = calibrationfilename,
            CharacterizationRunsFile = characterfilename,
            Binning = "-0.001",
            SaveAS  = "",
            OutputDirectory = outputdir, 
            NormalizeByCurrent = False,
            FilterBadPulses=0,
            CompressTOFTolerance = 0.,
            FrequencyLogNames="skf1.speed",
            WaveLengthLogNames="skf12.lambda")

    vulcanws = ConvertUnits(InputWorkspace="VULCAN_%d"%(runnumber), OutputWorkspace="VULCAN_%d_SNSReduc"%(runnumber), 
            Target="TOF", EMode="Elastic", AlignBins=False)

    outfilename = os.path.join(outputdir, "%s.gda" % (str(runnumber)))
    SaveVulcanGSS(InputWorkspace=vulcanws, BinFilename=refLogTofFilename, 
            OutputWorkspace="Proto2Bank", GSSFilename=outfilename, 
            IPTS = ipts, GSSParmFilename="Vulcan.prm")

    return outfilename


def copyFile(sourcefilename, destdir):
    """ Copy one file to another directory
    """
    import os
    import shutil
   
    # Verify input  
    if os.path.exists(sourcefilename) is False:
	print "Warning.  Input file wrong"
	return
    elif os.path.isdir(sourcefilename) is True:
	print "Warning.  Input file is not file but directory."
	return
    if os.path.isabs(sourcefilename) is not True:
	print "Warning"
	return

    # Create directory if it does not exist
    if os.path.isdir(destdir) is not True:
	os.makedirs(destdir)
   
    # Copy
    shutil.copy(sourcefilename, destdir)
    newfilename = os.path.join(destdir, os.path.basename(sourcefilename))
    os.chmod(newfilename, 0676)

    return


def main(argv):
    """ Main
    """
    if len(argv) < 3:
        print "Inputs: [1. File name with full length] [2. Output directory]"
        return
    
    eventFileAbs = argv[1]
    outputDir = argv[2]
   
    # Obtain information from input file name and path
    eventFile = os.path.split(eventFileAbs)[-1]
    nexusDir = eventFileAbs.replace(eventFile, '')
    runNumber = int(eventFile.split('_')[1])
    configService = mantid.config
    dataSearchPath = configService.getDataSearchDirs()
    dataSearchPath.append(nexusDir)
    configService.setDataSearchDirs(";".join(dataSearchPath))
    
    # Check file's existence
    if os.path.exists(eventFileAbs) is False:
        print "NeXus file %s is not accessible or does not exist. " % (eventFileAbs)
        return 
    
    # Find out IPTS 
    if eventFileAbs.count("IPTS") == 1:
        terms = eventFileAbs.split("/")
        for t in terms:
            if t.count("IPTS") == 1:
                iptsstr = t
                break
        ipts = int(iptsstr.split("-")[1])
    else:
        ipts = 0

    # Change the input 'OutputDir' to .../logs/ as instrument scientist requests
    origOutputDir = outputDir
    # FIXMENOT
    outputDir = changeOutputDir(origOutputDir)
    
    # Load file to generate the matrix workspace with some logs
    logwsname = "VULCAN_%d_MetaDataOnly" % (runNumber)

    try:
        Load(Filename=eventFileAbs, OutputWorkspace=logwsname, MetaDataOnly = True, LoadLogs = True)
    except RuntimeError as err:
        print "Unable to load NeXus file %s. Error message: %s. " % (eventFileAbs, str(err))
        return 
            
    # Convert Furnace"/tmp/furnace41703.txt"
    exportFurnaceLog(logwsname, outputDir, runNumber)
    
    # Convert Generic DAQ log
    exportGenericDAQLog(logwsname, outputDir, ipts, runNumber)

    # Write out loadframe /MTS log
    exportMTSLog(logwsname, outputDir, ipts, runNumber)
   
    # FIXMENOT
    # Write experiment log (Record.txt)
    rfilename = "/SNS/VULCAN/IPTS-%d/shared/AutoRecord.txt" % (ipts)
    #rfilename = "/home/wzz/Projects/MantidTests/Vulcan_Reduction/AutoRecord.txt"
    #rfilename = "/SNS/VULCAN/IPTS-%d/shared/auto_test/AutoRecord.txt" % (ipts)
    instrument="VULCAN"
    exportgood = write_record(logwsname, instrument, ipts, runNumber, rfilename)
   
    # Reduce GSAS file
    # FIXMENOT
    outputDir = changeOutputDir(origOutputDir, "autoreduce/binned")
    #outputDir = changeOutputDir(origOutputDir, "auto_test/binned")
    gsasfilename = saveGSASFile(ipts, runNumber, outputDir)
    saveDir2 = changeOutputDir(origOutputDir, "binned_data")
    copyFile(gsasfilename, saveDir2)
    

    # FIXMENOT
    outputDir = origOutputDir
    #outputDir = changeOutputDir(origOutputDir, "auto_test")
    SavePlot1D(InputWorkspace="Proto2Bank", OutputFilename=outputDir+"VULCAN_"+str(runNumber)+'.png',  
        YLabel='Intensity')
    
    return

if __name__ == "__main__":
    import sys
    main(sys.argv)
