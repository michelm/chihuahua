#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

'''
Summary
-------
*TODO*

Description
-----------
*TODO*

Usage
-----
*TODO*

'''

import os
from waflib import Build, Logs, Scripting, Task, Context
from waftools import makefile
from waftools import codeblocks
from waftools import eclipse
from waftools import cmake

VERSION='0.0.2'

def options(opt):
	'''Adds command line options to the *waf* build environment 

	:param opt: Options context from the *waf* build environment.
	:type opt: waflib.Options.OptionsContext
	'''
	opt.add_option('--cleanup', dest='cleanup', default=False, 
		action='store_true', help='removes files generated by export')

	codeblocks.options(opt)
	eclipse.options(opt)
	makefile.options(opt)
	cmake.options(opt)


def configure(conf):
	'''Method that will be invoked by *waf* when configuring the build 
	environment.
	
	:param conf: Configuration context from the *waf* build environment.
	:type conf: waflib.Configure.ConfigurationContext
	'''
	codeblocks.configure(conf)
	eclipse.configure(conf)
	makefile.configure(conf)
	cmake.configure(conf)


def task_process(task):
	'''Collects information of build tasks duing the build process.

	:param task: A concrete task (e.g. compilation of a C source file
				that is bing processed.
	:type task: waflib.Task.TaskBase
	'''
	if not hasattr(task, 'cmd'):
		return
	task.cmd = [arg.replace('\\', '/') for arg in task.cmd]
	gen = task.generator
	bld = task.generator.bld
	if gen not in bld.components:
		bld.components[gen] = [task]
	else:
		bld.components[gen].append(task)


def build_postfun(bld):
	'''Will be called by the build environment after all tasks have been
	processed.

	Converts all collected information from task, task generator and build
	context and converts most used info to an Export class. And finally 
	triggers the actual export modules to start the export process on 
	available C/C++ build tasks.
	
	:param task: A concrete task (e.g. compilation of a C source file
				that is bing processed.
	:type task: waflib.Task.TaskBase
	'''
	bld.export = Export(bld)

	if bld.options.cleanup:
		codeblocks.cleanup(bld)
		eclipse.cleanup(bld)
		makefile.cleanup(bld)
		cmake.cleanup(bld)

	else:
		codeblocks.export(bld)
		eclipse.export(bld)
		makefile.export(bld)
		cmake.export(bld)


class ExportContext(Build.BuildContext):
	'''Exports and converts tasks to external formats (e.g. makefiles, 
	codeblocks, msdev, ...).
	'''
	fun = 'build'
	cmd = 'export'

	def execute(self, *k, **kw):
		'''Executes the *export* command.

		The export command installs a special task process method
		which enables the collection of tasks being executed (i.e.
		the actual command line being executed). Furthermore it 
		installs a special *post_process* methods that will be called
		when the build has been completed (see build_postfun).

		Note that before executing the *export* command, a *clean* command
		will forced by the *export* command. This is needed in order to
		(re)start the task processing sequence.
		'''
		self.components = {}

		old_exec = Task.TaskBase.exec_command
		def exec_command(self, *k, **kw):
			ret = old_exec(self, *k, **kw)
			try:
				self.cmd = k[0]
			except IndexError:
				pass
			return ret
		Task.TaskBase.exec_command = exec_command

		old_process = Task.TaskBase.process
		def process(task):
			old_process(task)
			task_process(task)
		Task.TaskBase.process = process

		def postfun(bld):
			if not len(bld.components):
				Logs.warn('export failed: no targets found!')
			else:
				build_postfun(bld)
		super(ExportContext, self).add_post_fun(postfun)

		Scripting.run_command('clean')
		super(ExportContext, self).execute(*k, **kw)


class Export(object):
	'''Class that collects and converts information from the build 
	context (e.g. convert back- into forward slashes).

	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.Build.BuildContext
	'''
	def __init__(self, bld):
		self.version = VERSION
		self.wafversion = Context.WAFVERSION
		try:
			self.appname = getattr(Context.g_module, Context.APPNAME)
		except AttributeError:
			self.appname = os.path.basename(bld.path.abspath())
		try:
			self.appversion = getattr(Context.g_module, Context.VERSION)
		except AttributeError:
			self.appversion = ""
		self.prefix = bld.env.PREFIX		
		try:
			self.top = os.path.abspath(getattr(Context.g_module, Context.TOP))
		except AttributeError:
			self.top = str(bld.path.abspath())
		try:
			self.out = os.path.abspath(getattr(Context.g_module, Context.OUT))
		except AttributeError:
			self.out = os.sep.join([self.top, 'build'])

		self.bindir = bld.env.BINDIR
		self.libdir = bld.env.LIBDIR
		ar = bld.env.AR
		if isinstance(ar, list):
			ar = ar[0]
		self.ar = ar
		try:
			self.cc = bld.env.CC[0]
		except IndexError:
			self.cc = 'gcc'
		try:
			self.cxx = bld.env.CXX[0]
		except IndexError:
			self.cxx = 'g++'
		self.rpath = ' '.join(bld.env.RPATH)
		self.cflags = ' '.join(bld.env.CFLAGS)
		self.cxxflags = ' '.join(bld.env.CXXFLAGS)
		self.defines = ' '.join(bld.env.DEFINES)
		self.dest_cpu = bld.env.DEST_CPU
		self.dest_os = bld.env.DEST_OS
		self._clean_os_separators()

	def _clean_os_separators(self):
		for attr in self.__dict__:
			val = getattr(self, attr)
			if isinstance(val, str):
				val = val.replace('\\', '/')
				setattr(self, attr, val)


