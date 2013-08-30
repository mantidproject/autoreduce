Summary: autoreduce-mq
Name: autoreduce-mq
Version: 1.3
Release: 1 
Group: Applications/Engineering
prefix: /usr
BuildRoot: %{_tmppath}/%{name}
License: Unknown
Source: autoreduce-mq.tgz
Requires: libNeXus.so.0()(64bit) libc.so.6()(64bit) libc.so.6(GLIBC_2.2.5)(64bit)
Requires: mantid 
Requires: mantidunstable 
Requires: mantidnightly
Requires: python-suds 
#Requires: stompest 
#Requires: stompest.async
%define debug_package %{nil}


%description
Autoreduce program to automatically catalog and reduce neutron data

%prep
%setup -q -n %{name}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/autoreduce
install -m 664	../autoreduce-mq/etc/autoreduce/icat4.cfg	 %{buildroot}%{_sysconfdir}/autoreduce/icat4.cfg
install -m 755 -d 	 ../autoreduce-mq/usr	 %{buildroot}/usr
mkdir -p %{buildroot}%{_bindir}
install -m 755	 ../autoreduce-mq/usr/bin/ingestNexus_mq.py	 %{buildroot}%{_bindir}/ingestNexus_mq.py
install -m 755	 ../autoreduce-mq/usr/bin/ingestReduced_mq.py	 %{buildroot}%{_bindir}/ingestReduced_mq.py
install -m 755	 ../autoreduce-mq/usr/bin/queueProcessor.py	 %{buildroot}%{_bindir}/queueProcessor.py
install -m 755	 ../autoreduce-mq/usr/bin/Configuration.py	 %{buildroot}%{_bindir}/Configuration.py
install -m 755	 ../autoreduce-mq/usr/bin/asynProducer.py	 %{buildroot}%{_bindir}/asynProducer.py
install -m 755	 ../autoreduce-mq/usr/bin/PostProcessAdmin.py	 %{buildroot}%{_bindir}/PostProcessAdmin.py

%post
chgrp snswheel %{_sysconfdir}/autoreduce/icat4.cfg

%files
%config %{_sysconfdir}/autoreduce/icat4.cfg
%attr(755, -, -) %{_bindir}/ingestNexus_mq.py
%attr(755, -, -) %{_bindir}/ingestReduced_mq.py
%attr(755, -, -) %{_bindir}/queueProcessor.py
%attr(755, -, -) %{_bindir}/Configuration.py
%attr(755, -, -) %{_bindir}/asynProducer.py
%attr(755, -, -) %{_bindir}/PostProcessAdmin.py
