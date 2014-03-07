autoreduce
==========

The scripts directory contains autoReposSync.sh script which auto compares the beamline reduction python scripts to the scripts in repos, and auto checks into the git repository if they are different.

The scripts directory also contains processBatchRuns.sh script which takes a nexus directory and a range of run. If the run is not already cataloged, it will send the run file path to the queue where the workflow manager will kick off the process.

The SNSPostProcessRPM directory contains the following packages:
 - autoreduce-adara: used on the legacy beam lines to bridge the legacy translation with the automated post-processing.
 - autoreduce-mq: service running on the AR nodes to perform post-processing.
 - autoreduce-remote: Fermi version of the post-processing service.

To generate the RPMs, run 'make rpm' in the SNSPostProcessRPM directory.



