#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

import os
import sys
from waflib.Build import BuildContext, CleanContext, InstallContext, UninstallContext
import waftools
from waftools.export import ExportContext

top = '.'
out = 'build'
prefix = 'output'

VERSION = '0.6.2'
APPNAME = 'ChiHuaHuaTest'

POKY = {}
if 'linux' in sys.platform:
	POKY['arm5'] = '/opt/poky/1.4.2/environment-setup-armv5te-poky-linux-gnueabi'
	POKY['arm7'] = '/opt/poky/1.4.2/environment-setup-armv7a-vfp-neon-poky-linux-gnueabi'

VARIANTS = POKY.keys()
if 'linux' in sys.platform:
	VARIANTS.append('win32')


CONTEXTS = (
	BuildContext, CleanContext, 
	InstallContext, UninstallContext, 
	ExportContext
)

def options(opt):
	opt.add_option('--prefix', 
		dest='prefix', 
		default=prefix, 
		help='installation prefix [default: %r]' % prefix)

	opt.add_option('--check_c_compiler', 
		dest='check_c_compiler', 
		default='gcc', action='store', 
		help='Selects C compiler type.')

	opt.add_option('--check_cxx_compiler', 
		dest='check_cxx_compiler', 
		default='gxx', 
		action='store', 
		help='Selects C++ compiler type.')

	opt.add_option('--debug', 
		dest='debug', 
		default=False, 
		action='store_true', 
		help='Build with debug information.')

	opt.load('cppcheck', tooldir=os.path.dirname(waftools.__file__))
	opt.load('export', tooldir=os.path.dirname(waftools.__file__))
	opt.load('package', tooldir=os.path.dirname(waftools.__file__))


def configure(conf):
	conf.check_waf_version(mini='1.7.0')
	prefix = conf.env.PREFIX

	if 'linux' in sys.platform:
		for key, value in POKY.items():
			_create_poky_env(conf, prefix, key, value)
		_create_mingw_env(conf, prefix)

	conf.setenv('')
	conf.load('compiler_c')
	conf.load('compiler_cxx')
	conf.load('cppcheck')
	conf.load('export')
	conf.load('package')
	_set_cc_options(conf)


def build(bld):
	def get_scripts(top, name):
		locations = []
		for cwd, _, files in os.walk(top):
			for f in files:
				if os.path.basename(f) != name:
					continue
				locations.append(cwd)				
		scripts = []
		for loc in locations:
			if any(os.path.dirname(loc).endswith(t) for t in locations):
				continue
			scripts.append(loc)
		return scripts

	scripts = get_scripts('components', 'wscript')
	for script in scripts:
		bld.recurse(script)


def dist(ctx):
	ctx.algo = 'tar.gz'
	ctx.excl = ' **/*~ **/.lock-w* **/CVS/** **/.svn/** downloads/** ext/** build/** tmp/**'


def _set_cc_options(conf):
	conf.env.CFLAGS = ['-Wall']
	conf.env.CXXFLAGS = ['-Wall']
	if conf.env.DEST_OS != 'win32':
		conf.env.RPATH = ['/lib', '/usr/lib', '/usr/local/lib']
		conf.env.append_unique('RPATH', conf.env.LIBDIR)

	if conf.options.debug:
		conf.env.append_unique('CFLAGS', '-ggdb')
		conf.env.append_unique('CFLAGS', '-g')
		conf.env.append_unique('CXXFLAGS', '-ggdb')
		conf.env.append_unique('CXXFLAGS', '-g')
	else:
		conf.env.append_unique('CFLAGS', '-O3')
		conf.env.append_unique('CXXFLAGS', '-O3')
		conf.env.append_unique('DEFINES', 'NDEBUG')


def _create_poky_env(conf, prefix, name, fname):
	'''Create a cross compile environment using settings from yocto/poky.'''
	if not os.path.exists(fname):
		conf.msg("Setup Yocto for '%s'" % name, 'skipping', color='RED')
		return
	conf.setenv(name)
	conf.env.PREFIX = os.sep.join([prefix, 'opt', name])
	conf.env.BINDIR = os.sep.join([prefix, 'opt', name, 'bin'])
	conf.env.LIBDIR = os.sep.join([prefix, 'opt', name, 'lib'])

	env = _get_poky_environment(fname)
	_set_poky_binaries(conf, env)
	conf.load('compiler_c')
	conf.load('compiler_cxx')
	conf.load('export')
	_add_poky_options(conf, env)


def _get_poky_environment(fname):
	'''Returns a dictionary containing environment settings from yocto/poky.
	'''
	with open(fname) as f:
		lines = f.readlines()
	env = {}
	var = [l[7:] for l in lines if l.startswith('export ')]
	for (key, value) in [v.split('=', 1) for v in var]:
		env[key] = value.replace('\n', '')
	return env


def _set_poky_binaries(conf, environment):
	'''Sets paths to programs used when cross compiling using the
	YOCTO/POKY SDK.
	'''
	env = dict(environment)

	paths = env['PATH'].replace('$PATH', '')
	paths = [p for p in paths.split(':') if len(p)]

	keys = ('CC', 'CXX', 'AR')
	for key in env.keys():
		if key not in keys:
			del env[key]

	for key in keys:
		value = env[key].replace('"', '').split()
		for path in paths:
			path = '%s/%s' % (path, value[0])
			if os.path.exists(path):
				value[0] = path
				break
		env[key] = [value[0]]

	for key, value in env.items():
		conf.env[key] = value


def _add_poky_options(conf, environment):
	'''Set environment options (e.g. compile flags) for the cross
	compile environment using the YOCTO/POKY SDK.
	'''
	env = dict(environment)
	_set_cc_options(conf)

	options = env['CC'].replace('"', '').split()[1:]
	for option in options:
		conf.env.append_unique('CFLAGS', option)

	options = env['CXX'].replace('"', '').split()[1:]
	for option in options:
		conf.env.append_unique('CXXFLAGS', option)


def _create_mingw_env(conf, prefix, name='win32'):
	'''Create a cross compile environment for MinGW.'''
	import platform
	if platform.machine() == 'i686':
		mach = 'i686'
		mingw = 'i686-w64-mingw32'
	else:
		mach = 'x86_64'
		mingw = 'x86_64-w64-mingw32'

	for cc in ('gcc', 'g++', 'ar'):
		try:
			conf.find_program('%s-%s' % (mingw, cc))
		except:
			conf.msg("Setup MinGW for '%s'" % mach, 'skipping', color='RED')
			return

	conf.setenv(name)
	conf.env.PREFIX = os.sep.join([prefix, 'opt', name])
	conf.env.BINDIR = os.sep.join([prefix, 'opt', name, 'bin'])
	conf.env.LIBDIR = os.sep.join([prefix, 'opt', name, 'lib'])
	conf.env.CC = ['%s-gcc' % (mingw)]
	conf.env.CXX = ['%s-g++' % (mingw)]
	conf.env.AR = ['%s-ar' % (mingw)]
	conf.load('compiler_c')
	conf.load('compiler_cxx')
	conf.load('export')
	_set_cc_options(conf)


for var in VARIANTS:
	for ctx in CONTEXTS:
		name = ctx.__name__.replace('Context','').lower()
		class _t(ctx):
			__doc__ = "%ss '%s'" % (name, var)
			cmd = name + '_' + var
			variant = var

