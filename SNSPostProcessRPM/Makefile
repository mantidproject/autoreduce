prefix := /var/www/reduction_service

ifeq ($(OS),Windows_NT)
UNAME_S=Windows
else
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Linux)
ISLINUX = 1
endif
ifeq ($(UNAME_S),Darwin)
ISOSX = 1
endif
endif

all:
	@echo "Installing post-processing service"
	
clean: 
	rm -f /usr/bin/Configuration.py
	rm -f /usr/bin/ingestNexus_mq.py
	rm -r /usr/bin/ingestReduced_mq.py
	rm -f /usr/bin/PostProcessAdmin.py
	rm -f /usr/bin/queueProcessor.py
	
check:
	# Check dependencies
	@python -c "import xml.utils.iso8601" || echo "\nERROR: Need PyXML: easy_install PyXML\n"
	@python -c "import requests" || echo "\nERROR: Need requests: easy_install requests\n"
	@python -c "import stompest" || echo "\nERROR: Need stompest: easy_install stompest\n"
	@python -c "import stompest.async" || echo "\nERROR: Need stompest.async: easy_install stompest.async\n"
	@python -c "import suds" || echo "\nERROR: Need suds: easy_install suds\n"
	@python -c "import nxs" || echo "\nERROR: Need nexus: http://download.nexusformat.org/kits/\n"
	
install: autoreducemq
       
autoreducemq: check
	# Make sure the directories exist
	test -d /etc/autoreduce || mkdir -m 0755 -p /etc/autoreduce
	test -d /var/log/SNS_applications || mkdir -m 0755 /var/log/SNS_applications
	
	# Install application code

	install -m 664	rpmbuild/autoreduce-mq/etc/autoreduce/icat4.cfg	 /etc/autoreduce/icat4.cfg
	install -m 755	rpmbuild/autoreduce-mq/usr/bin/ingestNexus_mq.py	 /usr/bin/ingestNexus_mq.py
	install -m 755	rpmbuild/autoreduce-mq/usr/bin/ingestReduced_mq.py	 /usr/bin/ingestReduced_mq.py
	install -m 755	rpmbuild/autoreduce-mq/usr/bin/queueProcessor.py	 /usr/bin/queueProcessor.py
	install -m 755	rpmbuild/autoreduce-mq/usr/bin/Configuration.py	 /usr/bin/Configuration.py
	install -m 755	rpmbuild/autoreduce-mq/usr/bin/PostProcessAdmin.py	 /usr/bin/PostProcessAdmin.py
	
.PHONY: check
.PHONY: clean
.PHONY: install
.PHONY: webapp
