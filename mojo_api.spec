Name:           mojo_api
Version:        0.1
Release:        1%{?dist}
Summary:        Mojo api
Group:          Development/Languages
License:        GPL
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python-setuptools
Requires:       python-requests
Requires:       python-argparse

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
* Tue Jan 15 2015 Wei Shi <wshi@redhat.com> - 0.1-1
- Create app base on mojo_api by Tomas Dabasinskas <tomas@redhat.com>
