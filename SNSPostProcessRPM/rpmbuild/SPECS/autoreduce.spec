Summary: autoreduce
Name: autoreduce
Version: 1.3
Release: 1 
Group: Applications/Engineering
prefix: /usr
BuildRoot: %{_tmppath}/%{name}
License: Unknown
Source: autoreduce.tgz
Requires: libc.so.6()(64bit) libc.so.6(GLIBC_2.2.5)(64bit)
Requires: stomp 
%define debug_package %{nil}


%description
Sending message to active MQ when a pre ADARA run is produced

%prep
%setup -q -n %{name}

%build

%install
rm -rf %{buildroot}
install -m 755 -d 	 ../autoreduce/usr	 %{buildroot}/usr
mkdir -p %{buildroot}%{_bindir}
install -m 755	 ../autoreduce/usr/bin/process_run.sh	 %{buildroot}%{_bindir}/process_run.sh
install -m 755	 ../autoreduce/usr/bin/sendMessage.py	 %{buildroot}%{_bindir}/sendMessage.py
mkdir -p %{buildroot}%{_libdir}

%post

%files
%attr(755, -, -) %{_bindir}/process_run.sh
%attr(755, -, -) %{_bindir}/sendMessage.py
