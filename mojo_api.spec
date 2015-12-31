Name:           mojo_api
Version:        0.3
Release:        0%{?dist}
Summary:        Mojo api
Group:          Development/Languages

License:        GPLv2+
URL:            https://github.com/shi2wei3/mojo_api
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch

BuildRequires:  python-setuptools
Requires:       python-requests
Requires:       python-requests-kerberos
Requires:       python-beautifulsoup4

%description
Mojo api

%prep
%setup -q -n %{name}-%{version}

%build
%{__python} setup.py build

%install
# install app
%{__python} setup.py install -O1 --skip-build --root %{buildroot}

%files
%{python_sitelib}/*
%{_bindir}/*

%changelog
* Thu Dec 31 2015 Wei Shi <wshi@redhat.com> - 0.3-0
- Change auth method to SPNEGO with Kerberos

* Thu Feb 26 2015 Wei Shi <wshi@redhat.com> - 0.2-0
- Mail funcion for mojo_report added, ready for preview

* Tue Jan 15 2015 Wei Shi <wshi@redhat.com> - 0.1-1
- Create app base on mojo_api by Tomas Dabasinskas <tomas@redhat.com>
