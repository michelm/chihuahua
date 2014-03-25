#!/usr/bin/env python

import shutil, os, sys
from waflib import Build, Context, Scripting, Logs

PACKAGE_TYPES_DEFAULT='all'

def options(opt):
	'''Adds command line options to the *waf* build environment 

	:param opt: Options context from the *waf* build environment.
	:type opt: waflib.Options.OptionsContext
	'''
	opt.add_option('--package_types', 
		dest='package_types',
		default=PACKAGE_TYPES_DEFAULT,
		action='store',
		help='package types to create (default=all)')

	opt.add_option('--package_cleanup', 
		dest='package_cleanup',
		default=False,
		action='store_true',
		help='cleanup package staging area')

	opt.add_option('--nsis_script', 
		dest='nsis_script',
		default='install.nsi',
		action='store',
		help='nsis install script (default=install.nsi)')
		
		
def configure(conf):
	'''Method that will be invoked by *waf* when configuring the build 
	environment.
	
	:param conf: Configuration context from the *waf* build environment.
	:type conf: waflib.Configure.ConfigurationContext
	'''	
	conf.env.PACKAGE_TYPES = conf.options.package_types.split(',')
	conf.env.NSIS_SCRIPT = conf.options.nsis_script
	conf.find_program('makensis', var='NSIS')

	
class PackageContext(Build.InstallContext):
	cmd = 'package'
	fun = 'build'

	def init_dirs(self, *k, **kw):
		super(PackageContext, self).init_dirs(*k, **kw)
		self._package = self.bldnode.make_node('.wafpackage')
		try:
			shutil.rmtree(self._package.abspath())
		except:
			pass
		if os.path.exists(self._package.abspath()):
			self.fatal('Could not remove temporary directory %r' % self._package)
		self._package.mkdir()
		self.options.destdir = self._package.abspath()

	def execute(self, *k, **kw):
		'''executes normal 'install' into a special, temporary, package directory
		and creates a package (e.g. tar.bz2 or rpm) file containing all installed
		files into this package directory.
		'''		
		super(PackageContext, self).execute(*k, **kw)

		version = getattr(Context.g_module, Context.VERSION, self.top_dir)
		appname = getattr(Context.g_module, Context.APPNAME, self.top_dir)
		variant = self.variant if self.variant else ''
		pkgtype = self.env.PACKAGE_TYPES
		files = self._get_files()

		pkg = self.options.package_types
		if pkg != PACKAGE_TYPES_DEFAULT:
			pkgtype = pkg.split(',')
		
		if set(pkgtype) & set(['all', 'ls']):
			self._package_ls(appname, variant, version, files)
		
		if set(pkgtype) & set(['all', 'tar.bz2']):
			self._package_tar_bz2(appname, variant, version)

		if set(pkgtype) & set(['all', 'nsis']):
			self._package_nsis(appname, variant, version, files)

		if self.options.package_cleanup:
			shutil.rmtree(self._package.abspath())

	def _get_files(self):
		'''returns a list of file names to be packaged from which the PREFIX
		path has been stripped.		
		'''
		files = []
		prefix = str(self.env.PREFIX)
		i = prefix.find(':')
		if i >= 0 and (i+1) < len(prefix):
			prefix = prefix[i+1:]
		i = len(self._package.relpath()) + len(prefix)

		for f in self._package.ant_glob('**'):
			files.append(str(f.relpath()[i:]).replace('\\','/'))
		return files

	def _package_ls(self, appname, variant, version, files):
		'''just print all files that will be packaged.'''
		p = Logs.info
		p('')
		p('=======================')
		p('PACKAGE (ls)')
		p('=======================')
		for f in files:
			p('$PREFIX%s' % f)
		p('-----------------------')
		
	def _package_tar_bz2(self, appname, variant, version):
		name = '%s%s-%s' % (appname, variant, version)
		p = Logs.info
		p('')
		p('=======================')
		p('PACKAGE (tar.bz2)')
		p('=======================')
		p('PREFIX=%s' % self.env.PREFIX)	
		ctx = Scripting.Dist()
		ctx.arch_name = '%s.tar.bz2' % (name)
		ctx.files = self._package.ant_glob('**')
		ctx.tar_prefix = ''
		ctx.base_path = self._package
		ctx.archive()
		p('-----------------------')

	def _package_nsis(self, appname, variant, version, files):
		nsis = self.env.NSIS
		if isinstance(nsis, list):
			if not len(nsis):
				Logs.warn('NSIS not available, skipping')
				return
			nsis = nsis[0]
			
		fname = self.env.NSIS_SCRIPT
		script = self.path.find_node(fname)
		if not script:
			script = self._nsis_create_script(fname)
		
		cwd = self._package.abspath()
		cmd = '%s /NOCD %s' % (nsis, script.abspath())
		stdout = self.cmd_and_log(cmd, output=Context.STDOUT, quiet=Context.STDOUT, cwd=cwd)
		Logs.info(stdout)

	def _nsis_create_script(self, fname):
		script = self.path.make_node(fname)
		# TODO: create nsi script using buildin template
		return script
	
