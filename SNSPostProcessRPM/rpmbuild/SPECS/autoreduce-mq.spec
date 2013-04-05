Summary: autoreduce-mq
Name: autoreduce-mq
Version: 1.1
Release: 2 
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
%define debug_package %{nil}


%description
Autoreduce program to automatically reduce neutron data after a run

%prep
%setup -q -n %{name}

%build

%install
rm -rf %{buildroot}
mkdir -p %{buildroot}%{_sysconfdir}/autoreduce
install -m 664	../autoreduce-mq/etc/autoreduce/icat4.cfg	 %{buildroot}%{_sysconfdir}/autoreduce/icat4.cfg
install -m 664	../autoreduce-mq/etc/autoreduce/post_process_consumer.conf	 %{buildroot}%{_sysconfdir}/autoreduce/post_process_consumer.conf
install -m 755 -d 	 ../autoreduce-mq/usr	 %{buildroot}/usr
mkdir -p %{buildroot}%{_bindir}
install -m 755	 ../autoreduce-mq/usr/bin/ingestNexus_mq.py	 %{buildroot}%{_bindir}/ingestNexus_mq.py
install -m 755	 ../autoreduce-mq/usr/bin/ingestReduced_mq.py	 %{buildroot}%{_bindir}/ingestReduced_mq.py
install -m 755	 ../autoreduce-mq/usr/bin/queueListener.py	 %{buildroot}%{_bindir}/queueListener.py
install -m 755	 ../autoreduce-mq/usr/bin/queueProcessor.py	 %{buildroot}%{_bindir}/queueProcessor.py

%post
chgrp snswheel %{_sysconfdir}/autoreduce/icat4.cfg

%files
%config %{_sysconfdir}/autoreduce/icat4.cfg
%config %{_sysconfdir}/autoreduce/post_process_consumer.conf
%attr(755, -, -) %{_bindir}/ingestNexus_mq.py
%attr(755, -, -) %{_bindir}/ingestReduced_mq.py
%attr(755, -, -) %{_bindir}/queueListener.py
%attr(755, -, -) %{_bindir}/queueProcessor.py
