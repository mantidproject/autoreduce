# Autoreduce Startup Instructions
Since there are now three machines involved in the running of autoreduction, I have separated the startup instructions into the instructions for each of the machines.

## Utilities Machine (reducequeue - Windows)
* Run the following command ```python C:\database_backup\mysql_post_cycle.py cycle_XX_X``` where the cycle is given as the most recent cycle. This will clear the MySQL database and store the most recent backups of that database. 
* Open the Services control panel and ensure that MySQL57, ActiveMQ and Autoreduce Instrument Monitor are all running. If they are not then restart them.
* Restart the Autoreduce Instrument Monitor anyway as it needs to pick up the new cycle. You can check the monitor_log to ensure that the process is working correctly. 

## Back End Machine (autoreduce - Linux)
* •	Ensure that the latest stable and nightly Mantid builds are installed.
* On the backend machine log in with your federal credentials and then switch user to isisautoreduce. After logging in, run the following commands: ```python /home/isisautoreduce/NewQueueProcessing/AutoreductionProcessor/queue_processor_daemon.py restart``` and then ```python /home/isisautoreduce/NewQueueProcessing/QueueProcessor/queue_processor_daemon.py restart```
* Then, take a look at the log files which can be located at ```/home/isisautoreduce/NewQueueProcessing/logs/autoreductionProcessor.log``` and ```/home/isisautoreduce/NewQueueProcessing/logs/queueProcessor.log``` respectively. At this point, I would run a tail -F on each of the log files and send a test message with ```python /home/isisautoreduce/NewQueueProcessing/test/sendMessage.py```. Make sure the message passes through correctly. 

## Front End Machine (reduce - Windows)
* At the time of writing, I haven't set up a functional account to be able to run the Apache server as a Windows service. Therefore, log in as your local user, open a command window to ```C:\Program Files (x86)\Apache Software Foundation\Apache2.2\bin``` and run ```http.exe```. This will ensure that there are no problems when retrieving files from the archive. Ideally, this should run as a service instead. 
* Once the front end is up and running, check you can navigate to http://reduce.isis.cclrc.ac.uk. You should be able to see the test run that you ran earlier. 