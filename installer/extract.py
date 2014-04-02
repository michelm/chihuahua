#!/usr/env python
# -*- encoding: utf-8 -*-

'''
DESCRIPTION:
Extracts compressed tar.gz, tar.bz2 or zip archives.

USAGE:
	python extract.py [options]

OPTIONS:
	-h | --help		prints this help message.
	
	-n archive | --name=archive
					specify the name of the archive to extact.

	-p location | --path=location
					specify the extraction location.

'''

import os
import sys
import getopt
import tarfile
import zipfile


def usage():
	print(__doc__)


def unzip(zip, path):
	z = zipfile.ZipFile(zip)
	for name in z.namelist():
		(dirname, filename) = os.path.split(name)
		if filename == '': # directory
			dir = os.path.join(path, dirname)
			if not os.path.exists(dir):
				os.mkdir(dir)
		else: # file
			fname = os.path.join(path, name)
			print(fname)
			fd = open(fname, 'wb')
			fd.write(z.read(name))
			fd.close()			
	z.close()


def untar(tar, path):
	if name.endswith('.gz'):
		compression = 'gz'
	else:
		compression = 'bz2'
	
	t = tarfile.open(name, 'r:%s' % compression)
	for member in t.getmembers():
		print(member.name)
		t.extract(member, path=path)
	

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hn:p:', ['help', 'name=', 'path='])
	except getopt.GetoptError as err:
		print(str(err))
		usage()
		sys.exit(2)

	name = None
	path = '.'

	for o, a in opts:
		if o in ('-h', '--help'):
			usage()
			sys.exit()
		elif o in ('-n', '--name'):
			name = a
		elif o in ('-p', '--path'):
			path = a

	if not name:
		usage()
		sys.exit(2)
	
	if name.endswith('.zip'):
		unzip(name, path)
	else:
		untar(name, path)
