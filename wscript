#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

import os

top = '.'
out = 'build'
prefix = 'output'

VERSION = '0.0.1-beta'
APPNAME = 'chihuahua'


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

	opt.load('cppcheck', tooldir='./waftools')
	opt.load('export', tooldir='./waftools')


def configure(conf):
	conf.check_waf_version(mini='1.7.0')
	conf.load('compiler_c')
	conf.load('compiler_cxx')
	conf.load('cppcheck')
	conf.load('export')
	conf.env.CFLAGS = ['-Wall']
	conf.env.CXXFLAGS = ['-Wall']
	conf.env.RPATH = ['/lib', '/usr/lib', '/usr/local/lib']
	conf.env.append_unique('RPATH', '%s/lib' % conf.env.PREFIX)
	if conf.options.debug:
		conf.env.append_unique('CFLAGS', '-ggdb')
		conf.env.append_unique('CFLAGS', '-g')
		conf.env.append_unique('CXXFLAGS', '-ggdb')
		conf.env.append_unique('CXXFLAGS', '-g')
	else:
		conf.env.append_unique('CFLAGS', '-O3')
		conf.env.append_unique('CXXFLAGS', '-O3')
		conf.env.append_unique('DEFINES', 'NDEBUG')


def build(bld):
	def get_scripts(top, script):
		scripts = []
		for cwd, _dirs, files in os.walk(top):
			if script not in files:
				continue
			if any(cwd.startswith(path) for path in scripts):
				if any(cwd.count(os.sep) != s.count(os.sep) for s in scripts):
					continue
			scripts.append(cwd)
		return scripts

	scripts = get_scripts('components', 'wscript')
	for script in scripts:
		bld.recurse(script)


def dist(ctx):
	ctx.algo = 'tar.gz'
	ctx.excl = ' **/*~ **/.lock-w* **/CVS/** **/.svn/** downloads/** ext/** build/** tmp/**'



