#!/usr/bin/env python
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import os
import shutil

# this is only a list of the "special" ones
INSTRUMENTS = {'HYSPEC': 'HYS',
               'NOMAD': 'NOM',
               'POWGEN': 'PG3',
               'SEQUOIA': 'SEQ',
               'VISION': 'VIS'}


def toShared(name, srcdir):
    direc = os.path.join(srcdir, shortName(name), 'shared')
    return direc


def filesInGit(gitdir, instrument):
    direc = os.path.join(options.gitdir, instrument)

    filenames = os.listdir(direc)
    for f in filenames:
        if os.path.isdir(os.path.join(direc,f)):
            filenames.extend([os.path.join(f,_f) for _f in os.listdir(os.path.join(direc,f))])
    return filenames


def shortName(instrument):
    instrument = instrument.upper()
    return INSTRUMENTS.get(instrument, instrument)


def defaultAutoNames(instrument):
    instrument = shortName(instrument)

    filenames = ['reduce_%s.py',
                 'reduce_%s_utilities.py',
                 'reduce_%s.py.template',
                 'sumRun_%s.py',
                 'sumRun_%s.cfg',
                 'sumBatchRun_%s.sh']

    filenames = [item % instrument for item in filenames]
    return filenames


def defaultLiveNames(instrument):
    instrument = shortName(instrument)

    filenames = ['reduce_%s_live_proc.py',
                 'reduce_%s_live_post_proc.py']
    filenames = [item % shortName(instrument) for item in filenames]

    return filenames


def copyfile(filename, src, dst):
    srcfile = os.path.join(src, filename)
    dstfile = os.path.join(dst, filename)

    if os.path.exists(srcfile):
        # TODO could check to see if they are different
        print('copy', srcfile, 'to', dstfile)
        shutil.copyfile(srcfile, dstfile)


def copyfiles(filenames, src, dst):
    for filename in filenames:
        copyfile(filename, src, dst)

if __name__ == '__main__':
    # configure the argument parser
    import argparse
    parser = argparse.ArgumentParser(description="Copy autoreduction and "
                                     "livereduction files to specified "
                                     "directory")
    parser.add_argument('gitdir', help='Directory with the git repository')
    parser.add_argument('srcdir', nargs='?',
                        help='Directory containing reduction script root',
                        default='/SNS')

    # parse the command line
    options = parser.parse_args()
    if not os.path.isdir(options.srcdir):
        raise RuntimeError(options.srcdir + ' does not exist')
    if not os.path.isdir(options.gitdir):
        raise RuntimeError(options.gitdir + ' does not exist')

    options.gitdir = os.path.join(options.gitdir, 'ReductionScripts', 'sns')

    instruments = os.listdir(options.gitdir)

    for instrument in instruments:
        # list of instruments to skip
        if instrument in ['saved']:
            continue
        print('*****', instrument)

        sharedir = toShared(instrument, options.srcdir)
        gitdir = os.path.join(options.gitdir, instrument)

        autodir = os.path.join(sharedir, 'autoreduce')

        if os.path.isdir(autodir):
            print('-----', autodir)

            filenames = filesInGit(options.gitdir, instrument)
            filenames.extend(defaultAutoNames(instrument))
            filenames = list(set(filenames))  # remove repeats

            copyfiles(filenames, autodir, gitdir)

        livedir = os.path.join(sharedir, 'livereduce')
        if os.path.isdir(livedir):
            print('-----', livedir)

            filenames = defaultLiveNames(instrument)

            copyfiles(filenames, livedir, gitdir)
