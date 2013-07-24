Summary: autoreduce-remote
Name: autoreduce-remote
Version: 0.0 
Release: 2 
Group: Applications/Engineering
prefix: /usr
BuildRoot: %{_tmppath}/%{name}
License: Unknown
Source: autoreduce-remote.tgz
Requires: libc.so.6()(64bit) libc.so.6(GLIBC_2.2.5)(64bit)
%define debug_package %{nil}


%description
Autoreduce program to automatically reduce neutron data in a parallel fashion

%prep
%setup -q -n %{name}

%build

%install
rm -rf %{buildroot}
install -m 755 -d 	 ../autoreduce-remote/usr	 %{buildroot}/usr
mkdir -p %{buildroot}%{_bindir}
install -m 755	 ../autoreduce-remote/usr/bin/queueListener.py	 %{buildroot}%{_bindir}/queueListener.py
install -m 755	 ../autoreduce-remote/usr/bin/queueProcessor.py	 %{buildroot}%{_bindir}/queueProcessor.py
install -m 755	 ../autoreduce-remote/usr/bin/qsub_job.sh %{buildroot}%{_bindir}/qsub_job.sh

%files
%attr(755, -, -) %{_bindir}/queueListener.py
%attr(755, -, -) %{_bindir}/queueProcessor.py
%attr(755, -, -) %{_bindir}/qsub_job.sh
