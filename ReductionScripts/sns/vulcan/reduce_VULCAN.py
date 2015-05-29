################################################################################
#
# Auto reduction script for VULCAN
# Version 3.0 for both auto reduction service and manual 
#
# Last version: reduce_VULCAN_141028.py
# 
# Input
# - Event file name with path
# - Output directory
# 
# New Features:
# 1. Universal version for auto reduction service and manual reduction
# 2. AutoRecord.txt will be written to 2 directories in auto reduction mode
# a) .../shared/autoreduce/ to be untouchable and owned by auto reduction service;
# b) .../shared/ for users to modify and manual reduction
#
# Output
# 1. Furnace log;
# 2. Generic DAQ log;
# 3. MTS log;
# 4. Experiment log record (AutoRecord.txt)
# 5. Reduce for GSAS 
#
# Test example: 
# 1. reduce_VULCAN.py /SNS/VULCAN/IPTS-11090/0/41703/NeXus/VULCAN_41703_event.nxs 
#                     /SNS/users/wzz/Projects/VULCAN/AutoReduction/autoreduce/Temp
#
# 2. reduce_VULCAN.py /SNS/VULCAN/IPTS-11090/0/41739/NeXus/VULCAN_41739_event.nxs 
#                     /SNS/users/wzz/Projects/VULCAN/AutoReduction/autoreduce/Temp
#
################################################################################

import sys
import getopt
import os
import stat
import shutil 
import xml.etree.ElementTree as ET


#sys.path.append("/opt/mantidnightly/bin")
sys.path.append('/opt/mantidunstable/bin/')
#sys.path.append("/opt/Mantid/bin")

#sys.path.append('/home/wzz/Mantid/Code/debug/bin/')
#sys.path.append('/Users/wzz/Mantid/Code/debug/bin')

from mantid.simpleapi import *
import mantid

refLogTofFilename = "/SNS/VULCAN/shared/autoreduce/vdrive_log_bin.dat"
calibrationfilename = "/SNS/VULCAN/shared/autoreduce/vulcan_foc_all_2bank_11p.cal"
characterfilename = "/SNS/VULCAN/shared/autoreduce/VULCAN_Characterization_2Banks_v2.txt"

TIMEZONE1 = 'America/New_York'
TIMEZONE2 = 'UTC'

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
    # Make a new name
    isnewfilename = False
    maxattempts = 10
    numattempts = 0
    while isnewfilename is False and numattempts < maxattempts: 
	if numattempts == 0: 
	    logfilename = os.path.join(outputDir, "furnace%d.txt" % (runNumber))
	else:
	    logfilename = os.path.join(outputDir, "furnace%d_%d.txt" % (runNumber, numattempts))
	if os.path.isfile(logfilename) is False:
	    isnewfilename = True
	else:
	    numattempts += 1
    # ENDWHILE

    # Raise exception
    if isnewfilename is False:
	raise NotImplementedError("Unable to find an unused log file name for run %d. " % (runNumber))
    else:
	print "Log file will be written to %s. " % (logfilename)
    
    try:    
        ExportSampleLogsToCSVFile(InputWorkspace = logwsname, 
            OutputFilename = logfilename, 
            SampleLogNames = ["furnace.temp1", "furnace.temp2", "furnace.power"],
	    TimeZone = TIMEZONE2)
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
    if runNumber >= 69214:
    for ilog in xrange(1, 17):
        vucanheaderlist.append( ("tc.user%d"%(ilog), "tc.user%d"%(ilog)) )
    
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
   
    # Make a new name
    isnewfilename = False
    maxattempts = 10
    numattempts = 0
    while isnewfilename is False and numattempts < maxattempts: 
	if numattempts == 0: 
	    outputfilename = "IPTS-%d-GenericDAQ-%d.txt" % (ipts, runNumber)
	else:
	    outputfilename = "IPTS-%d-GenericDAQ-%d_%d.txt" % (ipts, runNumber, numattempts)
	outputfilename = os.path.join(outputDir, outputfilename)
	if os.path.isfile(outputfilename) is False:
	    isnewfilename = True
	else:
	    numattempts += 1
    # ENDWHILE

    # Raise exception
    if isnewfilename is False:
	raise NotImplementedError("Unable to find an unused log file name for run %d. " % (runNumber))
    else:
	print "Log file will be written to %s. " % (outputfilename)

    # Export
    try:    
        ExportSampleLogsToCSVFile(
            InputWorkspace = logwsname,
            OutputFilename = outputfilename,
            SampleLogNames = samplelognames,
            WriteHeaderFile = True,
	    TimeZone = TIMEZONE2,
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
   
    # Make a new name
    isnewfilename = False
    maxattempts = 10
    numattempts = 0
    while isnewfilename is False and numattempts < maxattempts: 
	if numattempts == 0: 
	    outputfilename = "IPTS-%d-MTSLoadFrame-%d.txt" % (ipts, runnumber)
	else:
	    outputfilename = "IPTS-%d-MTSLoadFrame-%d_%d.txt" % (ipts, runnumber, numattempts)
	outputfilename = os.path.join(outputDir, outputfilename)
	if os.path.isfile(outputfilename) is False:
	    isnewfilename = True
	else:
	    numattempts += 1
    # ENDWHILE

    # Raise exception
    if isnewfilename is False:
	raise NotImplementedError("Unable to find an unused log file name for run %d. " % (runNumber))
    else:
	print "Log file will be written to %s. " % (outputfilename)
  
    ExportSampleLogsToCSVFile(
        InputWorkspace = logwsname,
        OutputFilename = outputfilename,
        SampleLogNames = samplelognames,
        WriteHeaderFile = True, 
	TimeZone = TIMEZONE2,
        Header = headstr)


    return
    
RecordBase = [ 
        ("RUN",             "run_number", None),
        ("IPTS",            "experiment_identifier", None),
        ("Title",           "run_title", None),
        ("Notes",           "file_notes", None),
        ("Sample",          "Sample", None), # stored on sample object
        ("StartTime",       "run_start", "time"),
        ("Duration",        "duration", None),
        ("ProtonCharge",    "proton_charge", "sum"),
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


    def exportPatch(self):
        """ Export patch as a list of strings
        """
        cvdict = self._readCvInfoFile()
        rundict = self._readRunInfoFile()
        
        patchdict = {}
        for title in cvdict.keys():
            patchdict[title] = cvdict[title]
        
        for title in rundict.keys():
            patchdict[title] = rundict[title]

        patchlist = []
        for key in patchdict:
            patchlist.append(str(key))
            patchlist.append(str(patchdict[key]))

        return patchlist

        
    def patchRecord(self, recordfilename):
        """ Patch record, including ITPS, ... 
        """
        raise NotImplementedError("Invalid!")
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
    

def writeRecord(wsname, instrument, ipts, run, rfilename1, rfilename2, mode):
    """ Write the run info to a record file
    """
    # Convert the record base to input arrays
    sampletitles, samplenames, sampleoperations = generateRecordFormat()
    
    # Patch for logs that do not exist in event NeXus yet
    testclass = PatchRecord(instrument, ipts, run)
    patchlist = testclass.exportPatch()

    # Auto reduction and manual reduction
    # Determine mode
    if os.path.exists(rfilename2) is True:
        filemode = "fastappend"
    else:
        filemode = "new"

    # Export
    ExportExperimentLog(InputWorkspace = wsname, 
        OutputFilename     = rfilename2, 
        FileMode           = filemode, 
        SampleLogNames     = samplenames, 
        SampleLogTitles    = sampletitles, 
        SampleLogOperation = sampleoperations, 
        TimeZone           = "America/New_York", 
        OverrideLogValue   = patchlist, 
        OrderByTitle       = 'RUN',
        RemoveDuplicateRecord = True)

    # Set up the mode 
    mode = oct(os.stat(rfilename2)[stat.ST_MODE])
    mode = mode[-3:]
    if mode != '666' and mode != '676':
        print "Current file %s's mode is %s." % (rfilename2, mode)
        os.chmod(rfilename2, 0666)
    
    # Auto reduction only 
    if mode == "auto": 
        # Check if it is necessary to copy AutoRecord.txt from rfilename2 to rfilename1
        if os.path.exists(rfilename1) is False and filemode == "fastappend":
            # File do not exist
	    shutil.copy(rfilename2, rfilename1)

        # Export
        ExportExperimentLog(InputWorkspace = wsname, 
            OutputFilename     = rfilename1, 
            FileMode           = filemode, 
            SampleLogNames     = samplenames, 
            SampleLogTitles    = sampletitles, 
            SampleLogOperation = sampleoperations, 
            TimeZone           = TIMEZONE1,
            OverrideLogValue   = patchlist, 
            OrderByTitle       = 'RUN', 
            RemoveDuplicateRecord = True)

    
    return True

def saveGSASFile(ipts, runnumber, outputdir):
    """ Save for Nexus file
    """
    import os
    
    outfilename = os.path.join(outputdir, "%s.gda" % (str(runnumber)))
    if os.path.isfile(outfilename) is True:
	print "GSAS file (%s) has been reduced for run %s already. " % (outfilename, str(runnumber))
	return outfilename
    
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

    SaveVulcanGSS(InputWorkspace=vulcanws, BinFilename=refLogTofFilename, 
    	        OutputWorkspace="Proto2Bank", GSSFilename=outfilename, 
    	        IPTS = ipts, GSSParmFilename="Vulcan.prm")
		

    return outfilename


def copyFile(sourcefilename, destdir):
    """ Copy one file to another directory
    """
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
    newfilename = os.path.join(destdir, os.path.basename(sourcefilename))
    if os.path.isfile(newfilename) is True:
	print "Destination GSAS file exists. "
	return
    else: 
	shutil.copy(sourcefilename, destdir)
	os.chmod(newfilename, 0664)

    return


def main(argv):
    """ Main
    1. Furnace log;
    2. Generic DAQ log;
    3. MTS log;
    4. Experiment log record (AutoRecord.txt)
    5. Reduce for GSAS 
    """
    try: 
        opts, args = getopt.getopt(argv,"hdi:o:l:g:G:r:R:",["help", "ifile=","ofile=", "log=", "gsas=", "gsas2=", "record=", "record2=", "dryrun"]) 
    except getopt.GetoptError: 
        print "Exception: %s" % (str(getopt.GetoptError))
        print 'test.py -i <inputfile> -o <outputfile>' 
	return

    # Initialize 
    eventFileAbs = None
    outputDir = None
    recordFileName = None
    record2FileName = None
    gsasDir = None
    gsas2Dir = None
    logDir = None
    dryRun = False

    # 2 modes: auto-reduction and manual reduction (options)
    if len(opts) == 0:
        # Default/auto reduction mode
        mode = "auto"

        if len(argv) < 2:
            print "Auto   reduction Inputs:   [1. File name with full length] [2. Output directory]"
            print "Manual reduction Inputs:   --help"
            return
        eventFileAbs = argv[0]
        outputDir = argv[1]

        logDir = changeOutputDir(outputDir)

        recordFileName = os.path.join(outputDir, "AutoRecord.txt")
        m1Dir = changeOutputDir(outputDir, "")
        record2FileName = os.path.join(m1Dir, "AutoRecord.txt")
    
        gsasDir = changeOutputDir(outputDir, "autoreduce/binned")
        gsas2Dir = changeOutputDir(outputDir, "binned_data")

    else:
        # Manual reduction mode
        mode = "manual"

        for opt, arg in opts:
            if opt in ("-h", "--help"):
                # Help
                print "%s -i <inputfile> -o <outputdirectory> ... ..." % (sys.argv[0])
                print "-i/ifile  : mandatory input NeXus file name. "
                print "-o/ofile  : mandatory directory for output files. "
                print "-l/log    : optional directory for sample log files. "
                print "-g/gsas   : optional directory for GSAS file owned by owner. "
                print "-G/gsas2  : optional directory to copy GSAS file to  with file mode 664."
                print "-r/record : optional experiment record file name (writable only to auot reduction service)." 
                print "-R/record2: experiment record file (can be modified by manual reduction)." 
                print "-d/dry    : dry run to check output status, file names and directories."
                return
            elif opt in ("-i", "--ifile"):
                # Input NeXus file
                eventFileAbs = arg
            elif opt in ("-o", "--ofile"):
                # Output directory
                outputDir = arg
            elif opt in ("-l", "--log"):
                # Log file 
                if arg == '0':
                    logDir = None
                else:
                    logDir = arg
            elif opt in ("-g", "--gsas"):
                # GSAS file
                if arg == '0':
                    gsasDir = None
                else:
                    gsasDir = arg
            elif opt in ("-G", "--gsas2"):
                # GSAS file
                if arg == '0':
                    gsas2Dir = None
                else:
                    gsas2Dir = arg
            elif opt in ("-r", "--record"):
                # AutoReduce.txt
                if arg == '0':
                    recordFileName = None
                else:
                    recordFileName = arg
            elif opt in ("-R", "--record2"):
                # AutoReduce.txt
                if arg == '0':
                    record2FileName = None
                else:
                    record2FileName = arg
            elif opt in ("-d", "--dryrun"):
                # Dry run 
                dryRun = True
            # ENDIFELSE
        # ENDFOR
    # ENDIFELSE

    # Check
    if eventFileAbs is None or outputDir is None:
        print "Input event Nexus file and output directory must be given!"
        return

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

    # 1D plot file name 
    pngfilename = os.path.join(outputDir, 'VULCAN_'+str(runNumber)+'.png')

    print "Input NeXus file    : %s" % (eventFileAbs)
    print "Output directory    : %s" % (outputDir)
    print "Log directory       : %s" % (str(logDir))
    print "GSAS  directory     : %s;  If it is None, no GSAS will be written." % (str(gsasDir))
    print "GSAS2 directory     : %s" % (str(gsas2Dir))
    print "Record file name    : %s" % (str(recordFileName))
    print "Record(2) file name : %s" % (str(record2FileName))
    print "1D plot file name   : %s" % (pngfilename)

    if dryRun is True:
        return

    #------------------------------------------------------
    # Generate logs and/or AutoRecord
    #------------------------------------------------------
    if logDir is not None or recordFileName is not None or record2FileName is not None:
        # Load file to generate the matrix workspace with some logs 
        logwsname = "VULCAN_%d_MetaDataOnly" % (runNumber)
        try:
            Load(Filename=eventFileAbs, OutputWorkspace=logwsname, MetaDataOnly = True, LoadLogs = True)
        except RuntimeError as err:
            print "Unable to load NeXus file %s. Error message: %s. " % (eventFileAbs, str(err))
            return 
            
        if logDir is not None:
            # Export furance log
            exportFurnaceLog(logwsname, logDir, runNumber)
    
            # Export Generic DAQ log
            exportGenericDAQLog(logwsname, logDir, ipts, runNumber)

            # Export loadframe /MTS log
            exportMTSLog(logwsname, logDir, ipts, runNumber)
        # ENDIF

        if recordFileName is not None or record2FileName is not None:
            # Append auto record file
            instrument="VULCAN"
            exportgood = writeRecord(logwsname, instrument, ipts, runNumber, recordFileName, record2FileName, mode)
        # ENDIF
    # ENDIF

    #------------------------------------------------------
    # Reduce to GSAS file
    #------------------------------------------------------
    if gsasDir is not None:
        # SNSPowderReduction
        gsasfilename = saveGSASFile(ipts, runNumber, gsasDir)

        # 2nd copy for Ke
        copyFile(gsasfilename, gsas2Dir)

        try: 
            SavePlot1D(InputWorkspace="Proto2Bank", OutputFilename=pngfilename,  YLabel='Intensity')
        except ValueError as err: 
            print "Unable to generate 1D plot for run %s caused by %s. " % (str(runNumber), str(err))
        except RuntimeError as err: 
            print "Unable to generate 1D plot for run %s caused by %s. " % (str(runNumber), str(err))
    # ENDIF
   
    return

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
