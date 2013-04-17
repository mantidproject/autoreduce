import sys 

post_processing_bin = sys.path.append("/usr/bin")

from ingestReduced_mq import IngestReduced

def usage():
    print "This script takes 1 argument: a path to a nexus file to be cataloged; e.g. /SNS/HYSA/IPTS-8056/nexus/HYSA_13207.nxs.h5"
    sys.exit(1)

def main(argv):
    args = sys.argv[1:]
    if len(args) != 1:
         usage()

    path = args[0]
    param = path.split("/")
    if len(param) > 5:
        facility = param[1]
        instrument = param[2]
        ipts = param[3]
        filename = param[5]
                
        param2 = filename.split(".")
        if len(param2) > 2:
            param3 = param2[0].split("_")
            if len(param3) > 1:
                run_number = param3[1]

    ingestReduced = IngestReduced(facility, instrument, ipts, run_number)
    ingestReduced.execute()
    ingestReduced.logout()
    sys.exit(0)

if __name__ == "__main__":
    main(sys.argv[1:])


