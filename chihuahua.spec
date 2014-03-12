Name:           chihuahua
Version:        0.1.1
Release:        1%{?dist}
Summary:        Cross platform development environment for embedded systems

License:        MIT      
URL:            https://github.com/michelm/chihuahua
#Source0:        https://github.com/michelm/chihuahua/%{name}-%{version}.tar.gz

Requires:	wget git subversion python python-pygments cppcheck

%description
ChiHuaHua provides a concrete cross platform development environment for
embedded systems.

%build
waf distclean
waf configure --prefix=$RPM_BUILD_ROOT
waf build
waf dist


%changelog
* Wed Mar 12 2014 michel.mooij7@gmail.com
- 
