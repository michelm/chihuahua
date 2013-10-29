chihuahua
=========
Test environment for exporting data from projects using the WAF meta build 
system (see http://code.google.com/p/waf) into other formats such as:
	- (gnu) makefiles
	- code::blocks projects and workspaces
	- cmake

usage
-----
Configure:
	waf configure

Build:
	waf build

Export:
	waf export --export-makefile

See command line help for additional information (waf --help).

