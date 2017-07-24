#!/usr/bin/python
from __future__ import (absolute_import, division, print_function, unicode_literals)
import grp
import h5py
import os
import stat
import sys
import numpy
import csv
import re
try:
    import ConfigParser as configparser
except ImportError:
    import configparser


class RunInfo:
    def __init__(self, instrument, infilename):
        self._names = []
        self._nodes = []
        self._values = []
        self._infilename = infilename
        instrument = instrument.upper()
        config_path = '/SNS/' + instrument + '/shared/autoreduce/sumRun_' + instrument + '.cfg'
        if not os.path.exists(config_path):
            raise RuntimeError('Failed to find config "%s"' % config_path)
        print('loading config:', config_path)
        config = configparser.SafeConfigParser()
        config.read(config_path)
        self._names = config.get("header", "names").split(',')

        for name in self._names:
            self._nodes.append(config.get('node', name))

    def fillRunData(self):
        # open nexus file
        with h5py.File(self._infilename, 'r') as f:
            for node in self._nodes:
                try:
                    value = f[node].value
                    if isinstance(value, numpy.ndarray):
                        if value.shape == (1,1):
                            value = value[0][0]
                        elif value.shape == (1,):
                            value = value[0]
                        else:
                            value = sum(value)
                        if isinstance(value, bytes):
                            value = value.decode().replace(',','')
                        if 'time' in node.lower():
                            value = re.sub('\..*','',value) # remove fractional seconds
                            value = re.sub('-','/',value) # change  '-' to '/'
                            value = re.sub('T','/',value) # change  'T' to '/'
                except Exception as e:
                    print('WARNING %s:' % node, e)
                    value = 'N/A'
                self._values.append(str(value))

    def getNames(self):
        return self._names

    def getValues(self):
        return self._values

def fixPermissions(filename, instrument):
    # user read, user write, group read, group write, other read - i.e. 664
    permission = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
    print('chmod 644', filename)
    os.chmod(filename, permission)
    group = 'sns_%s_team' % instrument.lower()
    try:
        gid = grp.getgrnam(group).gr_gid
        print('chgrp %s %s' % (group, filename))
        os.chown(filename, -1, gid)
    except KeyError:
        print('failed to find group "%s"' % group)

if __name__ == "__main__":
    # set up the options
    if len(sys.argv) != 4:
        print("run_info takes 3 arguments: instrument, nexus file and output file. Exiting...")
        sys.exit(-1)

    instrument, nexus, outfile = sys.argv[1:4]
    print('instrument:', instrument)
    print('input:', nexus)
    print('output:', outfile)
    runInfo = RunInfo(instrument.upper(), nexus)
    runInfo.fillRunData()

    # create the output file or stdout as appropriate
    if os.path.exists(outfile):
        f = open(outfile, 'a')
        writer = csv.writer(f)
    else:
        f = open(outfile, 'w')
        writer = csv.writer(f)
        handle = open(outfile, "w")
        # get header information for the csv file
        writer.writerow(runInfo.getNames())

    writer.writerow(runInfo.getValues())
    f.close()

    fixPermissions(outfile, instrument)
