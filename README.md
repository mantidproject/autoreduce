autoreduce
==========

The scripts directory contains autoReposSync.sh script which auto compares the beamline reduction python scripts to the scripts in repos, and auto checks into the git repository if they are different.

The scripts directory also contains processBatchRuns.sh script which takes a nexus directory and a range of run. If the run is not already cataloged, it will send the run file path to the queue where the workflow manager will kick off the process.

The SNSPostProcessRPM directory contains 3 rpm packages as autoreduce, autoreduce-adara, and autoreduce-mq.

The ReductionScripts directory contains auto reduction scripts for beamlines including the SNS beamlines arcs, basis, cncs, hyspec, nomad, powgen, ref_l, ref_m, and seequoia.


