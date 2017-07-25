# Autoreduction Installation
There are three machines involved in an installation of Autoreduction. For simplicities sake, I will be using the same generic names for the machines throughout. I have listed these names here, along with the description of each machine:

* **Utilities Machine (Windows)** - The machine which hosts the MySQL server, the ActiveMQ server and the EndOfRunMonitor
* **Queue Processing Machine (RedHat Linux)** - The machine hosting the two queue processing programs (AutoreductionProcessor and QueueProcessor)
* **WebApp Machine (Windows)** - The machine which hosts the WebApp.

## Utilities Machine
The first step will be to install the required programs on the Utilities machine as this machine is relied upon by the other two for execution.

### MySQL
To start with, download the latest version of MySQL 32Bit for Windows from [here](https://dev.mysql.com/downloads/windows/installer/5.7.html). Before starting to install it, you should also download and install the C++ redistributable package 2013 from [here](https://www.microsoft.com/en-gb/download/details.aspx?id=40784) as MySQL server is dependent on it. 

Once you have installed the C++ package, go through the MySQL installation process and make sure to install the "Developer Default" option. There will be also be a "Check Requirements" page where you will have to click "Execute" to install missing dependencies. You will also have to set the root password at this stage. 

Once installation has completed, you should be able to use the included MySQL workbench to connect to the local database. Once you're happy everything is working as intended, you can move onto installing ActiveMQ.

### ActiveMQ

Firstly, you should install Java on the utilities machine. You can find the latest version of the JRE [here](http://www.oracle.com/technetwork/java/javase/downloads/jre8-downloads-2133155.html). After installing the JRE, you can download the ActiveMQ zip from [here](http://activemq.apache.org/download.html). After extracting the zip to a sensible location, you will need to configure your Windows ports so that external processes can access the ActiveMQ on port 61616. You can find instructions on how to do this on Windows [here](https://wiki.eveoh.nl/pages/viewpage.action?pageId=14287030#InstallingActiveMQ(MicrosoftWindows)-ConfiguringtheWindowsFirewall).

After configuring the firewall, you should set up ActiveMQ as a service so that it will automatically restart if the machine is rebooted. To do this, navigate to ```C:\ActiveMQ\apache-activemq-5.15.0\bin\win32``` and run the ```InstallService.bat``` file as an administrator. This will install ActiveMQ as a service. 

To optionally set a password on the ActiveMQ, you can modify the activemq.xml by adding the following section to the broker section:

```
<plugins>
    <simpleAuthenticationPlugin>
        <users>
            <authenticationUser username="user" password="password" groups="users,admins"/>
        </users>
    </simpleAuthenticationPlugin>
</plugins>
```

### EndOfRunMonitor
Copy the code for the EndOfRunMonitor across to the utilities machine. To install this, you are going to need to install Python and some extra dependencies. Here is the list:
* Download and install Python 32 Bit from [here](https://www.python.org/downloads/release/python-2713/)
* Download and run the get-pip script from [here](https://bootstrap.pypa.io/get-pip.py). 
* Download and install Pywin32 from [here](https://kent.dl.sourceforge.net/project/pywin32/pywin32/Build%20221/pywin32-221.win32-py2.7.exe)
* Download and install WinRar [here](http://www.rarlab.com/rar/wrar55b5.exe)
* Download and install Stomp.py [here](https://pypi.python.org/packages/26/5c/6b10498b29cf846727d7554f323ef317815ada748daf3e0fad077bb572e3/stomp.py-4.1.18.tar.gz#md5=edcc0e3246cb42b59f4199439665422e)
* Download and install suds-jurko from [here](https://bbuseruploads.s3.amazonaws.com/jurko/suds/downloads/suds-jurko-0.6.zip?Signature=1rouc5m44SRes0Y2xBkHzEYMPRw%3D&Expires=1500557431&AWSAccessKeyId=AKIAIQWXW6WLXMB5QZAQ&versionId=null&response-content-disposition=attachment%3B%20filename%3D%22suds-jurko-0.6.zip%22)
* Finally, download and install Python-ICAT from [here](https://icatproject.org/misc/python-icat/download/python-icat-0.13.1.tar.gz)

Once all of the dependencies have been successfully installed, you need to navigate to your EndOfRunMonitor folder. Once in there, edit the settings.py file to ensure you are connecting to the correct locations. Once the settings have been updated, run ```python ISIS_monitor_win_service``` to install the EndOfRunMonitor as a Windows service. You will then need to manually update the service in your service explorer and change the user that it runs as such that it has the correct permissions to work properly.

## QueueProcessingMachine
Firstly, install all of the dependencies you will need. To do this, you will need pip if you don't have it already:
* yum install python-pip
* pip install stomp.py daemon twisted service_identity

Once all of the python libraries have installed, you can copy across the two queue processing programs. These can both be found [here] (https://github.com/mantidproject/autoreduce/tree/master/ISISPostProcessRPM/rpmbuild/autoreduce-mq/usr/bin).

Copy the folders across and edit each of the settings.py files to ensure you are connecting to the correct databases and ActiveMQ servers.

When you need to run the queue processors, just run ```python queue_processor_daemon.py start``` in each of the queue processors. 

## WebApp machine
### Install prerequisites

* Download and install Python 2.7 (32 bit) from: https://www.python.org/downloads/windows/
* Add c:\Python27 to the PATH environmental variable.
* Download and install 7-Zip from: http://downloads.sourceforge.net/sevenzip/7z920.exe
* Download and install MySqlServer from: http://dev.mysql.com/downloads/windows/installer/5.6.html
* Download and install Git from: http://git-scm.com/download/win
* Download and install MySQL-Python from: http://www.lfd.uci.edu/~gohlke/pythonlibs/4y6heurj/MySQL-python-1.2.5.win-amd64-py2.7.exe
* Download and install https://kent.dl.sourceforge.net/project/pywin32/pywin32/Build%20221/pywin32-221.win32-py2.7.exe
* Download https://raw.github.com/pypa/pip/master/contrib/get-pip.py and run python get-pip.py
* Add c:\python27\scripts to the path environmental variable.
* run ```pip install chardet``` and ```pip install Django==1.7.1```

### Install the WebApp

Copy across the files for the WebApp and then edit the settings.py and apache/apache_django_wsgi such that they have the correct configuration. If you are using the [UOWS login page](https://users.facilities.rl.ac.uk/auth/Login.aspx?ReturnUrl=/auth/Login.aspx) then you will probably need to add a certficate so that Apache and Django trust the site. To do this, get the certificate from [here](https://fitbawebdev.isis.cclrc.ac.uk:8181/UserOfficeWebService/UserOfficeWebService?wsdl) and place it on the WebApp machine. Then, add its directory to the settings.py file. This will ensure that the connection is trusted.

### Install Apache
Download Apache from [here](https://archive.apache.org/dist/httpd/binaries/win32/httpd-2.2.25-win32-x86-openssl-0.9.8y.msi) and run the MSI to install it. You will then need the Mod_WSGI package for Windows to be able to link the Django app up to the Apache server. This can be downloaded [here](https://github-production-release-asset-2e65be.s3.amazonaws.com/15648929/da6a22d0-08a6-11e5-8a5b-0d214c853629?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIAIWNJYAX4CSVEH53A%2F20170721%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20170721T072450Z&X-Amz-Expires=300&X-Amz-Signature=487c0889d87401114b447be381ef9a03886271fd3365e8623f971bebbead5518&X-Amz-SignedHeaders=host&actor_id=14982322&response-content-disposition=attachment%3B%20filename%3Dmod_wsgi-windows-4.4.12.tar.gz&response-content-type=application%2Foctet-stream). Get the 32 bit version of the mod_wsgi and place it in Apache2.2/modules. 

You will now need to edit your httpd.conf to include the mod_wsgi library. To do this, add the following line in the 'LoadModule' section: ```LoadModule wsgi_module modules/mod_wsgi-py27-VC9.so```. At the end of the file, you will need to add a line to include the wsgi.conf from the Django WebApp. 

You should then be able to start Apache as either a service or just through the command line by running ```httpd.exe``` found in Apache2.2/bin/httpd.exe.



