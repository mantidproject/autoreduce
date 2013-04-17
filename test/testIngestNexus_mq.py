import sys

post_processing_bin = sys.path.append("/usr/bin") 
from ingestNexus_mq import IngestNexus

def usage():
    print "This script takes 1 argument: a path to a nexus file to be cataloged; e.g. /SNS/HYSA/IPTS-8056/nexus/HYSA_13207.nxs.h5"
    sys.exit(1)

def main(argv):
    args = sys.argv[1:]
    if len(args) != 1:
         usage()

    path = args[0]
    ingestNexus = IngestNexus(path)
    ingestNexus.execute()
    ingestNexus.logout()
    sys.exit(0)

if __name__ == "__main__":
   main(sys.argv[1:])

