import sys
import getopt
import tarfile

def usage():
	print('extracts compressed tar.gz or tar.bz2 archives')
	print('usage: %s [options]' % sys.argv[0])
	print('')
	print('-h          | --help              prints this help')
	print('-n archive  | --name=archive      specify the name of the archive to extact')
	print('-p location | --path=location     speicify the location of the files to be extracted')

if __name__ == "__main__":
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'hn:p:', ['help', 'name=', 'path='])
	except getopt.GetoptError as err:
		print(str(err))
		usage()
		sys.exit(2)

	name = None
	path = '.'
	compression = 'bz2'

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
	
	if name.endswith('.gz'):
		compression = 'gz'

	t = tarfile.open(name, 'r:%s' % compression)
	t.extractall(path=path)

