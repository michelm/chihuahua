#!/usr/bin/env python
import os
try:
	from urllib.request import urlopen
except ImportError:
	from urllib2 import urlopen


def download(url, saveto):
	u = f = None
	try:
		print("downloading %s" % url)
		u = urlopen(url)
		f = open(saveto, 'wb')
		f.write(u.read())
		print("done")
	finally:
		if u:
			u.close()
		if f:
			f.close()
	return os.path.realpath(saveto)

url = "https://raw.github.com/pypa/pip/master/contrib/get-pip.py"
download(url, "get-pip.py")


