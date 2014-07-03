autoreduce
==========

This repository contains the automated reduction and cataloging service code for legacy instruments.
The legacy translation service expects a script in /usr/bin/process_run.sh to perform the post-processing.
Since the post-processing is now handled by the Workflow Manager, this script now simply sends an ActiveMQ message
announcing a new data file.

The post-processing service code can be found here: https://github.com/neutrons/post_processing_agent


This repository also holds the automated reduction scripts for each instrument.
The scripts directory contains the autoReposSync.sh script, which compares the beamline 
reduction scripts to the scripts in the repository. 
It checks them into the git repository if they are different.



To generate the RPM to be used with the legacy translation service, run 'make rpm' in the SNSPostProcessRPM directory.



