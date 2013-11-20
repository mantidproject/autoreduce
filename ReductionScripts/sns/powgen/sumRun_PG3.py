#!/usr/bin/python
import nxs, os, numpy, sys, posixpath, logging, csv
import xml.utils.iso8601, ConfigParser
from datetime import datetime

class RunInfo:
    def __init__(self, instrument, infilename):
        self._names = []
        self._nodes = []
        self._values = []
        self._infilename = infilename
        config_path = '/SNS/' + instrument + '/shared/autoreduce/sumRun_' + instrument + '.cfg' 
        print config_path
        config = ConfigParser.SafeConfigParser()
        config.read(config_path)
        self._names = config.get("header", "names").split(',')

        for name in self._names:
            self._nodes.append(config.get('node', name))

    def fillRunData(self):
        #open nexus file
        file = nxs.open(self._infilename, 'r')
        for node in self._nodes:
            try:
                file.openpath(node)
                value =  file.getdata()
                if isinstance(value, numpy.ndarray):
                    value = sum(value)
            except Exception as e:
                print e 
                value = 'N/A' 
                
            self._values.append(str(value))
        file.close()
 
    def getNames(self):
        return self._names

    def getValues(self):
        return self._values

if __name__ == "__main__":
    # set up the options
    if len(sys.argv) != 4:
        print "run_info takes 3 arguments: instrument, nexus file and output file. Exiting..."
        sys.exit(-1)

    print sys.argv[1]
    print sys.argv[2]
    print sys.argv[3]
    runInfo = RunInfo(sys.argv[1], sys.argv[2])
    runInfo.fillRunData()

    outfile = sys.argv[3]

    # create the output file or stdout as appropriate
    if os.path.exists(outfile):
        writer = csv.writer(open(outfile, 'a'))
    else:
        writer = csv.writer(open(outfile, 'w'))
        handle = open(outfile, "w")
        # get header information for the csv file 
        writer.writerow(runInfo.getNames())

    writer.writerow(runInfo.getValues())