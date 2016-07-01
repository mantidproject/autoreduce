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
# Notes:
# * 15.12.04:
#   1. Modify 'FileMode' of ExportExperimentLog to 'append' mode.
#   2. items.id (ITEM) to AutoRecord.txt
#   3. Operations to all loadframe logs are changed to 'average'
# * 16.02.08
#   1. In 'auto' mode, the AutoRecord file will be written to .../logs/ and then
#      copied to .../autoreduce/
#
################################################################################

import sys
import getopt
import os
import stat
import shutil
import xml.etree.ElementTree as ET


sys.path.append("/opt/mantidnightly/bin")
#sys.path.append('/opt/mantidunstable/bin/')
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


def change_output_directory(original_directory, user_specified_dir=None):
    """ Purpose:
      Change the output direction from
      * .../autoreduce/ to .../logs/
      * .../autoreduce/ to .../<user_specified>
    :param original_directory: if it is not ends with /autoreduce/, then the target directory will be the same,
            while if the directory does not exist, the method will create ethe directory.
    :param user_specified_dir: if it is not specified, change to .../logs/ as default
    """
    # Check validity
    assert isinstance(original_directory, str)

    # Change path from ..../autoreduce/ to .../logs/
    if original_directory.endswith("/"):
        original_directory = os.path.split(original_directory)[0]
    parent_dir, last_sub_dir = os.path.split(original_directory)

    if last_sub_dir == "autoreduce":
        # original directory ends with 'autoreduce'
        if user_specified_dir is None:
            # from .../autoreduce/ to .../logs/
            new_output_dir = os.path.join(parent_dir, "logs")
        else:
            # from .../autoreduce/ to .../<user_specified>/
            new_output_dir = os.path.join(parent_dir, user_specified_dir)
        print "Log file will be written to directory %s. " % new_output_dir
    else:
        # non-auto reduction mode.
        new_output_dir = original_directory
        print "Log file will be written to the original directory %s. " % new_output_dir

    # Create path
    if os.path.exists(new_output_dir) is False:
        # create
        os.mkdir(new_output_dir)

    return new_output_dir


def exportFurnaceLog(logwsname, outputDir, runNumber):
    """ Export the furnace log
    """
    # Make a new name
    isnewfilename = False
    maxattempts = 10
    numattempts = 0
    logfilename = ''
    while isnewfilename is False and numattempts < maxattempts:
        if numattempts == 0:
            logfilename = os.path.join(outputDir, "furnace%d.txt" % (runNumber))
        else:
            logfilename = os.path.join(outputDir, "furnace%d_%d.txt" % (runNumber, numattempts))

        if os.path.isfile(logfilename) is False:
            isnewfilename = True
        else:
            numattempts += 1
    # END- WHILE

    # Raise exception
    if isnewfilename is False:
        raise NotImplementedError("Unable to find an unused log file name for run %d. " % (runNumber))
    else:
        print "Log file will be written to %s. " % logfilename

    try:
        ExportSampleLogsToCSVFile(InputWorkspace=logwsname,
                                  OutputFilename=logfilename,
                                  SampleLogNames=["furnace.temp1", "furnace.temp2", "furnace.power"],
                                  TimeZone=TIMEZONE2)
    except RuntimeError:
        raise NotImplementedError("Add an error message and skip if it happens.")

    return


def exportGenericDAQLog(logwsname, outputDir, ipts, runNumber):
    """ Export the furnace log
    """
    # Organzied by dictionary
    vulcanheaderlist = list()
    vulcanheaderlist.append(("TimeStamp"           , "")       )
    vulcanheaderlist.append(("Time [sec]"          , "")       )
    vulcanheaderlist.append(("Current"             , "Current"))
    vulcanheaderlist.append(("Voltage"             , "Voltage"))
    if runNumber >= 69214:
        for ilog in xrange(1, 17):
            vulcanheaderlist.append( ("tc.user%d"%(ilog), "tc.user%d"%(ilog)) )

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
    outputfilename = ''
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
    assert len(outputfilename) > 0

    # Raise exception
    if isnewfilename is False:
        raise NotImplementedError("Unable to find an unused log file name for run %d. " % (runNumber))
    else:
        print "Log file will be written to %s. " % outputfilename

    # Export
    try:
        ExportSampleLogsToCSVFile(InputWorkspace= logwsname,
                                  OutputFilename= outputfilename,
                                  SampleLogNames= samplelognames,
                                  WriteHeaderFile= True,
                                  TimeZone =TIMEZONE2,
                                  Header =headstr)
    except RuntimeError:
        print "Error in exporting Generic DAQ log for run %s. " % (str(runNumber))

    return


def exportMTSLog(logwsname, outputDir, ipts, run_number):
    """ Export MTS log
    List of MTS Log:
        X       Y       Z       O       HROT     VROT
        MTSDisplacement MTSForce        MTSStrain       MTSStress      MTSAngle
        MTSTorque       MTSLaser        MTSlaserstrain  MTSDisplaceoffset       MTSAngleceoffset
        MTST1   MTST2   MTST3   MTST4   FurnaceT
        FurnaceOT       FurnacePower    VacT    VacOT
    """
    # Organzied by dictionary
    vulcanheaderlist = list()
    vulcanheaderlist.append( ("TimeStamp"           , "")       )
    vulcanheaderlist.append( ("Time [sec]"          , "")       )
    vulcanheaderlist.append( ("MPTIndex"            , "loadframe.MPTIndex")     )
    vulcanheaderlist.append( ("X"                   , "X")      )
    vulcanheaderlist.append( ("Y"                   , "Y")      )
    vulcanheaderlist.append( ("Z"                   , "Z")      )
    vulcanheaderlist.append( ("O"                   , "OMEGA")  )
    vulcanheaderlist.append( ("HROT"                , "HROT")   )
    vulcanheaderlist.append( ("VROT"                , "VROT")   )
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
    vulcanheaderlist.append( ("MTSHighTempStrain"   , "loadframe.strain_hightemp") )
    vulcanheaderlist.append( ("FurnaceT"            , "furnace.temp1") )
    vulcanheaderlist.append( ("FurnaceOT"           , "furnace.temp2") )
    vulcanheaderlist.append( ("FurnacePower"        , "furnace.power") )
    vulcanheaderlist.append( ("VacT"                , "partlow1.temp") )
    vulcanheaderlist.append( ("VacOT"               , "partlow2.temp") )
    vulcanheaderlist.append( ('EuroTherm1Powder'    , 'eurotherm1.power') )
    vulcanheaderlist.append( ('EuroTherm1SP'        , 'eurotherm1.sp') )
    vulcanheaderlist.append( ('EuroTherm1Temp'      , 'eurotherm1.temp') )
    vulcanheaderlist.append( ('EuroTherm2Powder'    , 'eurotherm2.power') )
    vulcanheaderlist.append( ('EuroTherm2SP'        , 'eurotherm2.sp') )
    vulcanheaderlist.append( ('EuroTherm2Temp'      , 'eurotherm2.temp') )

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
    outputfilename = ''
    while isnewfilename is False and numattempts < maxattempts:
        if numattempts == 0:
            outputfilename = "IPTS-%d-MTSLoadFrame-%d.txt" % (ipts, run_number)
        else:
            outputfilename = "IPTS-%d-MTSLoadFrame-%d_%d.txt" % (ipts, run_number, numattempts)
        outputfilename = os.path.join(outputDir, outputfilename)
        if os.path.isfile(outputfilename) is False:
            isnewfilename = True
        else:
            numattempts += 1
    # ENDWHILE
    assert len(outputfilename) > 0

    # Raise exception
    if isnewfilename is False:
        raise NotImplementedError("Unable to find an unused log file name for run %d. " % run_number)
    else:
        print "Log file will be written to %s. " % outputfilename

    ExportSampleLogsToCSVFile(
        InputWorkspace=logwsname,
        OutputFilename=outputfilename,
        SampleLogNames=samplelognames,
        WriteHeaderFile=True,
        TimeZone=TIMEZONE2,
        Header=headstr)


    return


def exportVulcanSampleEnvLog(log_ws_name, output_dir, ipts, run_number):
    """ Export Vulcan sample environment log
    Requirements
    Guarantees: export the file name as 'Vulcan-IPTS-XXXX-SEnv-RRRR.txt'
    """
    # Check inputs
    assert isinstance(ipts, int)
    assert isinstance(run_number, int)

    # Create list of the sample logs to be exported.
    # each element is a 2-tuple of string as (log name in output log file, log name in workspace)
    vulcan_header_list = list()
    vulcan_header_list.append(("TimeStamp           ", ""))
    vulcan_header_list.append(("Time [sec]          ", ""))
    vulcan_header_list.append(("MPTIndex            ", "loadframe.MPTIndex"))
    vulcan_header_list.append(("X                   ", "X"))
    vulcan_header_list.append(("Y                   ", "Y"))
    vulcan_header_list.append(("Z                   ", "Z"))
    vulcan_header_list.append(("O"                   , "OMEGA"))
    vulcan_header_list.append(("HROT"                , "HROT"))
    vulcan_header_list.append(("VROT"                , "VROT"))
    vulcan_header_list.append(("MTSDisplacement"     , "loadframe.displacement"))
    vulcan_header_list.append(("MTSForce"            , "loadframe.force"))
    vulcan_header_list.append(("MTSStrain"           , "loadframe.strain"))
    vulcan_header_list.append(("MTSStress"           , "loadframe.stress"))
    vulcan_header_list.append(("MTSAngle"            , "loadframe.rot_angle"))
    vulcan_header_list.append(("MTSTorque"           , "loadframe.torque"))
    vulcan_header_list.append(("MTSLaser"            , "loadframe.laser"))
    vulcan_header_list.append(("MTSlaserstrain"      , "loadframe.laserstrain"))
    vulcan_header_list.append(("MTSDisplaceoffset"   , "loadframe.x_offset"))
    vulcan_header_list.append(("MTSAngleceoffset"    , "loadframe.rot_offset"))
    vulcan_header_list.append(("MTS1"                , "loadframe.furnace1"))
    vulcan_header_list.append(("MTS2"                , "loadframe.furnace2"))
    vulcan_header_list.append(("MTS3"                , "loadframe.extTC3"))
    vulcan_header_list.append(("MTS4"                , "loadframe.extTC4"))
    vulcan_header_list.append(("MTSHighTempStrain"   , "loadframe.strain_hightemp"))
    vulcan_header_list.append(("FurnaceT"            , "furnace.temp1"))
    vulcan_header_list.append(("FurnaceOT"           , "furnace.temp2"))
    vulcan_header_list.append(("FurnacePower"        , "furnace.power"))
    vulcan_header_list.append(("VacT"                , "partlow1.temp"))
    vulcan_header_list.append(("VacOT"               , "partlow2.temp"))
    vulcan_header_list.append(('EuroTherm1Powder'    , 'eurotherm1.power'))
    vulcan_header_list.append(('EuroTherm1SP'        , 'eurotherm1.sp'))
    vulcan_header_list.append(('EuroTherm1Temp'      , 'eurotherm1.temp'))
    vulcan_header_list.append(('EuroTherm2Powder'    , 'eurotherm2.power'))
    vulcan_header_list.append(('EuroTherm2SP'        , 'eurotherm2.sp'))
    vulcan_header_list.append(('EuroTherm2Temp'      , 'eurotherm2.temp'))

    # Generate title/header list and log name list from
    sample_log_name_list = []
    header_title_list = []
    for i in xrange(len(vulcan_header_list)):
        title = vulcan_header_list[i][0].strip()
        log_name = vulcan_header_list[i][1].strip()

        header_title_list.append(title)
        if len(log_name) > 0:
            sample_log_name_list.append(log_name)
    # END-FOR

    # For header string frrom list
    header_str = ''
    for title in header_title_list:
        header_str += "%s\t" % title

    # Make a new name in case an old one exists. Try max 10 times
    is_new_file_name = False
    max_attempts = 10
    num_attempt = 0
    output_file_name = None
    while is_new_file_name is False and num_attempt < max_attempts:
        # create file name
        if num_attempt == 0:
            output_file_name = 'Vulcan-IPTS-%d-SEnv-%d.txt' % (ipts, run_number)
        else:
            output_file_name = 'Vulcan-IPTS-%d-SEnv-%d-%d.txt' % (ipts, run_number, num_attempt)
        output_file_name = os.path.join(output_dir, output_file_name)

        # check whether it is a new file such that no old file will be overwritten
        is_new_file_name = not os.path.exists(output_file_name)
    # END-WHILE
    assert output_file_name is not None
    assert is_new_file_name, 'Unable to find an unused log file name for run %d.' % run_number
    print 'Log file will be written to %s.' % output_file_name

    # Export sample logs
    ExportSampleLogsToCSVFile(InputWorkspace=log_ws_name,
                              OutputFilename=output_file_name,
                              SampleLogNames=sample_log_name_list,
                              WriteHeaderFile=True,
                              SeparateHeaderFile=False,
                              DateTitleInHeader=False,
                              TimeZone=TIMEZONE2,
                              Header=header_str)

    return


RecordBase = [
    ("RUN",             "run_number", None),
    ("IPTS",            "experiment_identifier", None),
    ("Title",           "run_title", None),
    ("Notes",           "file_notes", None),
    ("Sample",          "Sample", None),  # stored on sample object
    ('ITEM',            'items.id', '0'),
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
    ("VROT",            "VROT", "0"),
    ("BandCentre",      "lambda", "0"),
    ("BandWidth",       "bandwidth", "0"),
    ("Frequency",       "skf1.speed", "0"),
    ("Guide",           "Guide", "0"),
    ("IX",              "IX",   "average"),
    ("IY",              "IY",   "average"),
    ("IZ",              "IZ",   "average"),
    ("IHA",             "IHA",  "average"),
    ("IVA",             "IVA",  "average"),
    ("Collimator",      "Vcollimator", None),
    ("MTSDisplacement", "loadframe.displacement",   "average"),
    ("MTSForce",        "loadframe.force",          "average"),
    ("MTSStrain",       "loadframe.strain",         "average"),
    ("MTSStress",       "loadframe.stress",         "average"),
    ("MTSAngle",        "loadframe.rot_angle",      "average"),
    ("MTSTorque",       "loadframe.torque",         "average"),
    ("MTSLaser",        "loadframe.laser",          "average"),
    ("MTSlaserstrain",  "loadframe.laserstrain",    "average"),
    ("MTSDisplaceoffset","loadframe.x_offset",      "average"),
    ("MTSAngleceoffset", "loadframe.rot_offset",    "average"),
    ("MTST1",           "loadframe.furnace1",       "average"),
    ("MTST2",           "loadframe.furnace2",       "average"),
    ("MTST3",           "loadframe.extTC3",         "average"),
    ("MTST4",           "loadframe.extTC4",         "average"),
    ("MTSHighTempStrain", "loadframe.strain_hightemp", "average"),
    ("FurnaceT",          "furnace.temp1",  "average"),
    ("FurnaceOT",         "furnace.temp2",  "average"),
    ("FurnacePower",      "furnace.power",  "average"),
    ("VacT",              "partlow1.temp",  "average"),
    ("VacOT",             "partlow2.temp",  "average"),
    ('EuroTherm1Powder', 'eurotherm1.power', 'average'),
    ('EuroTherm1SP',     'eurotherm1.sp',    'average'),
    ('EuroTherm1Temp',   'eurotherm1.temp',  'average'),
    ('EuroTherm2Powder', 'eurotherm2.power', 'average'),
    ('EuroTherm2SP',     'eurotherm2.sp',    'average'),
    ('EuroTherm2Temp',   'eurotherm2.temp',  'average'),
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

        # # Get last line
        # titleline, lastline = self.get_last_line_in_binary_file(recordfilename)

        # # print "First line: ", titleline
        # # print "Last line: ", lastline

        # # Parse last line and first line
        # rtitles = titleline.split("\t")
        # titles = []
        # for title in rtitles:
        #     title = title.strip()
        #     titles.append(title)

        # values = lastline.split("\t")

        # valuedict = {}
        # if len(titles) != len(values):
        #     raise NotImplementedError("Number of tiles are different than number of values.")
        # for itit in xrange(len(titles)):
        #     valuedict[titles[itit]] = values[itit]

        # # Substitute
        # ipts = self._getIPTS()
        # cvdict = self._readCvInfoFile()
        # rundict = self._readRunInfoFile()

        # valuedict["IPTS"] = "%s" % (str(ipts))
        # for title in cvdict.keys():
        #     valuedict[title] = cvdict[title]

        # # print valuedict.keys()

        # for title in rundict.keys():
        #     valuedict[title] = rundict[title]

        # # Form the line again: with 7 spaces in front
        # newline = "       "
        # for i in xrange(len(titles)):
        #     title = titles[i]
        #     if i > 0:
        #         newline += "\t"
        #     newline += "%s" % (str(valuedict[title]))

        # # Remove last line and append the patched line
        # self.remove_last_line_in_text(recordfilename)

        # with open(recordfilename, "a") as myfile:
        #     myfile.write("\n"+newline)

        # return

    @staticmethod
    def get_last_line_in_binary_file(filename):
        """ Get the first and last line of a (possibly long) file
        """
        # Open an binary file
        with open(filename, 'rb') as binary_file:
            # Determine a roughly the size of a line
            first_line = next(binary_file).decode().strip()
            second_line = next(binary_file).decode().strip()
            line_size = len(second_line)

            try:
                # search from the end of line
                binary_file.seek(-2*line_size, 2)
                last_line = binary_file.readlines()[-1].decode().strip()
                binary_file.close()
            except IOError:
                # File is too short
                # close the file and re-open
                binary_file.close()
                binary_file = open(filename, 'rb')

                lines = binary_file.readlines()
                last_line = lines[-1]
        # END-WITH

        return first_line, last_line

    @staticmethod
    def remove_last_line_in_text(filename):
        """ Remove last line
        """
        # ifile = open(sys.argv[1], "r+", encoding = "utf-8")
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
        Return: integer
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

        id_node = None
        for child in proposal:
            if child.tag == "ID":
                id_node = child
                break
        if id_node is None:
            raise NotImplementedError("No ID")

        ipts = id_node.text
        ipts = int(ipts)

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


def export_experiment_records(log_ws_name, instrument, ipts, run, auto_reduction_record_file_name,
                              logs_record_file_name, export_mode):
    """ Write the summarized sample logs of this run number to the record files
    :param log_ws_name:
    :param instrument:
    :param ipts:
    :param run:
    :param auto_reduction_record_file_name:
    :param logs_record_file_name
    :param export_mode: sample log exporting mode
    :return: True if it is an alignment run
    """
    # Convert the record base to input arrays
    sample_title_list, sample_name_list, sample_operation_list = generateRecordFormat()

    # Patch for logs that do not exist in event NeXus yet
    patcher = PatchRecord(instrument, ipts, run)
    patch_list = patcher.exportPatch()

    # Auto reduction and manual reduction
    if os.path.exists(logs_record_file_name) is True:
        # Determine mode: append is safer, as the list of titles changes, the old record
        # will be written to the a new file.
        filemode = "append"
    else:
        # New a file
        filemode = "new"

    # Export to auto record
    ExportExperimentLog(InputWorkspace=log_ws_name,
                        OutputFilename=logs_record_file_name,
                        FileMode=filemode,
                        SampleLogNames=sample_name_list,
                        SampleLogTitles=sample_title_list,
                        SampleLogOperation=sample_operation_list,
                        TimeZone="America/New_York",
                        OverrideLogValue=patch_list,
                        OrderByTitle='RUN',
                        RemoveDuplicateRecord=True)

    # Set up the mode for global access
    file_access_mode = oct(os.stat(logs_record_file_name)[stat.ST_MODE])
    file_access_mode = file_access_mode[-3:]
    if file_access_mode != '666' and file_access_mode != '676':
        print "Current file %s's mode is %s." % (logs_record_file_name, file_access_mode)
        os.chmod(logs_record_file_name, 0666)

    # Export to either data or align
    try:
        log_ws = mantid.AnalysisDataService.retrieve(log_ws_name)
        title = log_ws.getTitle()
        record_file_path = os.path.dirname(logs_record_file_name)
        if title.startswith('Align:'):
            categorized_record_file = os.path.join(record_file_path, 'AutoRecordAlign.txt')
            is_alignment_run = True
        else:
            categorized_record_file = os.path.join(record_file_path, 'AutoRecordData.txt')
            is_alignment_run = False

        if os.path.exists(categorized_record_file) is False:
            filemode2 = 'new'
        else:
            filemode2 = 'append'
        ExportExperimentLog(InputWorkspace=log_ws_name,
                            OutputFilename=categorized_record_file,
                            FileMode=filemode2,
                            SampleLogNames=sample_name_list,
                            SampleLogTitles=sample_title_list,
                            SampleLogOperation=sample_operation_list,
                            TimeZone="America/New_York",
                            OverrideLogValue=patch_list,
                            OrderByTitle='RUN',
                            RemoveDuplicateRecord=True)

        # Change file  mode
        if file_access_mode != '666' and file_access_mode != '676':
            os.chmod(categorized_record_file, 0666)
    except NameError as e:
        print '[Error] %s.' % str(e)

    # Auto reduction only
    if export_mode == "auto":
        # Check if it is necessary to copy AutoRecord.txt from rfilename2 to rfilename1
        if os.path.exists(auto_reduction_record_file_name) is False:
            # File do not exist, the copy
            shutil.copy(logs_record_file_name, auto_reduction_record_file_name)
        else:
            # Export the log by appending
            ExportExperimentLog(InputWorkspace=log_ws_name,
                                OutputFilename=auto_reduction_record_file_name,
                                FileMode=filemode,
                                SampleLogNames=sample_name_list,
                                SampleLogTitles=sample_title_list,
                                SampleLogOperation=sample_operation_list,
                                TimeZone=TIMEZONE1,
                                OverrideLogValue=patch_list,
                                OrderByTitle='RUN',
                                RemoveDuplicateRecord=True)

    return is_alignment_run


def saveGSASFile(ipts, runnumber, outputdir):
    """ Save for Nexus file
    """
    import os

    outfilename = os.path.join(outputdir, "%s.gda" % (str(runnumber)))
    if os.path.isfile(outfilename) is True:
        print "GSAS file (%s) has been reduced for run %s already. " % (outfilename, str(runnumber))
        return outfilename

    SNSPowderReduction(Instrument='VULCAN',
                       RunNumber=runnumber,
                       Extension="_event.nxs",
                       PreserveEvents=True,
                       CalibrationFile=calibrationfilename,
                       CharacterizationRunsFile=characterfilename,
                       Binning="-0.001",
                       SaveAS="",
                       OutputDirectory=outputdir,
                       NormalizeByCurrent=False,
                       FilterBadPulses=0,
                       CompressTOFTolerance=0.,
                       FrequencyLogNames="skf1.speed",
                       WaveLengthLogNames="skf12.lambda")

    # convert unit and save for VULCAN-specific GSAS
    input_ws_name = 'VULCAN_%d' % runnumber
    vulcan_ws_name = "VULCAN_%d_SNSReduc" % runnumber
    ConvertUnits(InputWorkspace=input_ws_name, OutputWorkspace=vulcan_ws_name,
                 Target="TOF", EMode="Elastic", AlignBins=False)

    SaveVulcanGSS(InputWorkspace=vulcan_ws_name, BinFilename=refLogTofFilename,
                  OutputWorkspace="Proto2Bank", GSSFilename=outfilename,
                  IPTS=ipts, GSSParmFilename="Vulcan.prm")

    return outfilename


def duplicate_gsas_file(source_gsas_file_name, target_directory):
    """ Duplicate gsas file to a new directory with file mode 664
    """
    # Verify input
    if os.path.exists(source_gsas_file_name) is False:
        print "Warning.  Input file wrong"
        return
    elif os.path.isdir(source_gsas_file_name) is True:
        print "Warning.  Input file is not file but directory."
        return
    if os.path.isabs(source_gsas_file_name) is not True:
        print "Warning"
        return

    # Create directory if it does not exist
    if os.path.isdir(target_directory) is not True:
        os.makedirs(target_directory)

    # Copy
    target_file_name = os.path.join(target_directory, os.path.basename(source_gsas_file_name))
    if os.path.isfile(target_file_name) is True:
        print "Destination GSAS file exists. "
        return
    else:
        shutil.copy(source_gsas_file_name, target_directory)
        os.chmod(target_file_name, 0664)

    return


def main(argv):
    """ Main method
    1. Generating log files including
        1) Furnace log;
        2) Generic DAQ log;
        3) MTS log;
        4) New sample environment log
    2. Experiment log record including
        1) AutoRecord.txt
        2) AutoRecordAlign.txt (run title starts with 'Align:'
        3) AutoRecordData.txt
    3. Reducing and generating GSAS file
    """
    # Parse input arguments
    try:
        opts, args = getopt.getopt(argv, "hdi:o:l:g:G:r:R:", ["help", "ifile=", "ofile=", "log=",
                                                              "gsas=", "gsas2=", "record=", "record2=",
                                                              "dryrun"])
    except getopt.GetoptError:
        print "Exception: %s" % (str(getopt.GetoptError))
        print 'test.py -i <inputfile> -o <outputfile>'
        return

    # Initialize
    event_file_abs_path = None
    outputDir = None
    recordFileName = None
    record2FileName = None
    gsasDir = None
    gsas2Dir = None
    logDir = None
    dryRun = False

    # process input arguments in 2 different modes: auto-reduction and manual reduction (options)
    if len(opts) == 0:
        # Default/auto reduction mode
        mode = "auto"

        if len(argv) < 2:
            print "Auto   reduction Inputs:   [1. File name with full length] [2. Output directory]"
            print "Manual reduction Inputs:   --help"
            return
        event_file_abs_path = argv[0]
        outputDir = argv[1]

        logDir = change_output_directory(outputDir)

        recordFileName = os.path.join(outputDir, "AutoRecord.txt")
        m1Dir = change_output_directory(outputDir, "")
        record2FileName = os.path.join(m1Dir, "AutoRecord.txt")

        gsasDir = change_output_directory(outputDir, "autoreduce/binned")
        gsas2Dir = change_output_directory(outputDir, "binned_data")

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
                event_file_abs_path = arg
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
            # END-IF-ELSE
        # END-FOR (opt)
    # END-IF-ELSE (len(opt)==0)

    # Check validity
    if event_file_abs_path is None or outputDir is None:
        print "Input event Nexus file and output directory must be given!"
        return

    # Obtain information from input file name and path
    eventFile = os.path.split(event_file_abs_path)[-1]
    nexusDir = event_file_abs_path.replace(eventFile, '')
    runNumber = int(eventFile.split('_')[1])
    configService = mantid.config
    dataSearchPath = configService.getDataSearchDirs()
    dataSearchPath.append(nexusDir)
    configService.setDataSearchDirs(";".join(dataSearchPath))

    # Check file's existence
    if os.path.exists(event_file_abs_path) is False:
        print "NeXus file %s is not accessible or does not exist. " % (event_file_abs_path)
        return

    # Find out IPTS
    if event_file_abs_path.count("IPTS") == 1:
        terms = event_file_abs_path.split("/")
        ipts_str = ''
        for t in terms:
            if t.count("IPTS") == 1:
                ipts_str = t
                break
        assert len(ipts_str) > 0, 'Impossible that IPTS string does not exist!'
        ipts = int(ipts_str.split("-")[1])
    else:
        ipts = 0

    # 1D plot file name
    pngfilename = os.path.join(outputDir, 'VULCAN_'+str(runNumber)+'.png')

    if dryRun is True:
        # Output result in case it is a dry-run
        print "Input NeXus file    : %s" % (event_file_abs_path)
        print "Output directory    : %s" % (outputDir)
        print "Log directory       : %s" % (str(logDir))
        print "GSAS  directory     : %s;  If it is None, no GSAS will be written." % (str(gsasDir))
        print "GSAS2 directory     : %s" % (str(gsas2Dir))
        print "Record file name    : %s" % (str(recordFileName))
        print "Record(2) file name : %s" % (str(record2FileName))
        print "1D plot file name   : %s" % (pngfilename)

        return

    # Generate sample logs and auto records
    if logDir is not None or recordFileName is not None or record2FileName is not None:
        # Load file to generate the matrix workspace with some logs
        meta_ws_name = "VULCAN_%d_MetaDataOnly" % (runNumber)
        try:
            Load(Filename=event_file_abs_path, OutputWorkspace=meta_ws_name, MetaDataOnly=True, LoadLogs=True)
        except RuntimeError as err:
            print "Unable to load NeXus file %s. Error message: %s. " % (event_file_abs_path, str(err))
            return

        # export sample log file for this run
        if logDir is not None:
            # Export furnace log
            exportFurnaceLog(meta_ws_name, logDir, runNumber)

            # Export Generic DAQ log
            exportGenericDAQLog(meta_ws_name, logDir, ipts, runNumber)

            # Export load frame /MTS log
            exportMTSLog(meta_ws_name, logDir, ipts, runNumber)

            # Export standard VULCAN sample environment data
            exportVulcanSampleEnvLog(meta_ws_name, logDir, ipts, runNumber)
        # ENDIF

        # export sample log summary to this IPTS
        if recordFileName is not None or record2FileName is not None:
            # Append auto record file
            instrument = "VULCAN"
            is_alignment_run = export_experiment_records(meta_ws_name, instrument, ipts, runNumber, recordFileName, 
                                                         record2FileName, mode)
        # ENDIF
    # ENDIF

    # Reduce to GSAS file
    if gsasDir is not None:
        # SNSPowderReduction
        gsasfilename = saveGSASFile(ipts, runNumber, gsasDir)

        # 2nd copy for Ke if it IS NOT an alignment run
        if is_alignment_run is False: 
            duplicate_gsas_file(gsasfilename, gsas2Dir)

        try:
            SavePlot1D(InputWorkspace="Proto2Bank", OutputFilename=pngfilename,  YLabel='Intensity')
            
            #from postprocessing.publish_plot import plot1d
            #x = mtd["Proto2Bank"].readX(0)
            #y = mtd["Proto2Bank"].readY(0)
            #x2 = mtd["Proto2Bank"].readX(1)
            #y2 = mtd["Proto2Bank"].readY(1)
    
            #plot1d(run_number, [[x, y], [x2, y2]], instrument='VULCAN',
            #       data_names=["sp-1", "sp-2"], 
            #       x_title=u"Time-of-flight (\u03BCs)",
            #       y_title="Intensity", y_log=True, show_dx=False)

        except ValueError as err:
            print "Unable to generate 1D plot for run %s caused by %s. " % (str(runNumber), str(err))
        except RuntimeError as err:
            print "Unable to generate 1D plot for run %s caused by %s. " % (str(runNumber), str(err))
    # ENDIF

    return

if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
