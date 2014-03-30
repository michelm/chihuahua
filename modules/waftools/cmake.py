#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

import os
import re
from waflib import Utils, Node, Tools


def options(opt):
	'''Adds command line options to the *waf* build environment 

	:param opt: Options context from the *waf* build environment.
	:type opt: waflib.Options.OptionsContext
	'''
	opt.add_option('--cmake', dest='cmake', default=False, 
		action='store_true', help='select cmake for export/import actions')


def configure(conf):
	'''Method that will be invoked by *waf* when configuring the build 
	environment.
	
	:param conf: Configuration context from the *waf* build environment.
	:type conf: waflib.Configure.ConfigurationContext
	'''	
	if conf.options.cmake:
		conf.find_program('cmake', var='CMAKE')


def _selected(bld):
	'''Returns True when this module has been selected/configured.'''
	m = bld.env.CMAKE
	return len(m) > 0 or bld.options.cmake

	
def export(bld):
	'''Exports all C and C++ task generators to cmake.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.Build.BuildContext
	'''
	if not _selected(bld):
		return
		
	cmakes = {}
	
	loc = bld.path.relpath().replace('\\', '/')
	top = CMake(bld, loc)
	cmakes[loc] = top
	
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			loc = gen.path.relpath().replace('\\', '/')
			if loc not in cmakes:
				cmake = CMake(bld, loc)
				cmakes[loc] = cmake
				top.add_child(cmake)
			cmakes[loc].add_tgen(gen)

	for cmake in cmakes.values():
		cmake.export()
				

def cleanup(bld):
	'''Removes all generated makefiles from the *waf* build environment.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.Build.BuildContext
	'''
	if not _selected(bld):
		return

	loc = bld.path.relpath().replace('\\', '/')
	CMake(bld, loc).cleanup()
		
	for gen, targets in bld.components.items():
		loc = gen.path.relpath().replace('\\', '/')
		CMake(bld, loc).cleanup()


class CMake(object):
	def __init__(self, bld, location):
		self.bld = bld
		self.exp = bld.export
		self.location = location
		self.cmakes = []
		self.tgens = []
		
	def export(self):
		content = self._get_content()
		if not content:
			return

		node = self._make_node()
		if not node:
			return
		node.write(content)

	def cleanup(self):
		node = self._find_node()
		if node:
			node.delete()

	def add_child(self, cmake):
		self.cmakes.append(cmake)

	def add_tgen(self, tgen):
		self.tgens.append(tgen)

	def get_location(self):
		return self.location

	def _get_fname(self):
		name = '%s/CMakeLists.txt' % (self.location)
		return name
		
	def _find_node(self):
		name = self._get_fname()
		if not name:
			return None    
		return self.bld.srcnode.find_node(name)

	def _make_node(self):
		name = self._get_fname()
		if not name:
			return None    
		return self.bld.srcnode.make_node(name)

	def _get_content(self):
		is_top = (self.location == self.bld.path.relpath())
				
		content = ''
		if is_top:
			content += 'cmake_minimum_required (VERSION 2.6)\n'
			content += 'project (%s)\n' % (self.exp.appname)
			content += '\n'

			env = self.bld.env			
			defines = env.DEFINES
			if len(defines):
				content += 'add_definitions(-D%s)\n' % (' -D'.join(defines))
				content += '\n'

			flags = env.CFLAGS
			if len(flags):
				content += 'set(CMAKE_C_FLAGS "%s")\n' % (' '.join(flags))

			flags = env.CXXFLAGS
			if len(flags):
				content += 'set(CMAKE_CXX_FLAGS "%s")\n' % (' '.join(flags))
		
		if len(self.tgens):
			content += '\n'
			for tgen in self.tgens:
				content += self._get_tgen_content(tgen)

		if len(self.cmakes):
			content += '\n'
			for cmake in self.cmakes:
				content += 'add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/%s)\n' % (cmake.get_location())

		return content

	def _get_tgen_content(self, tgen):
		content = ''
		name = tgen.get_name()

		content += 'set(%s_SOURCES' % (name)
		for src in tgen.source:
			content += '\n    %s' % src.path_from(tgen.path)
		content += ')\n\n'
		
		includes = self._get_genlist(tgen, 'includes')
		if len(includes):
			content += 'set(%s_INCLUDES' % (name)
			for include in includes:
				content += '\n    %s' % include
			content += ')\n'
			content += 'include_directories(${%s_INCLUDES})\n' % (name)
			content += '\n'

		defines = self._get_genlist(tgen, 'defines')
		if len(defines):
			content += 'add_definitions(-D%s)\n' % (' -D'.join(defines))
			content += '\n'
		
		if set(('cshlib', 'cxxshlib')) & set(tgen.features):
			content += 'add_library(%s SHARED ${%s_SOURCES})\n' % (name, name)
			
		elif set(('cstlib', 'cxxstlib')) & set(tgen.features):
			content += 'add_library(%s ${%s_SOURCES})\n' % (name, name)
	
		else:
			content += 'add_executable(%s ${%s_SOURCES})\n' % (name, name)

		libs = getattr(tgen, 'use', []) + getattr(tgen, 'lib', [])
		if len(libs):
			content += '\n'
			for lib in libs:
				content += 'target_link_libraries(%s %s)\n' % (name, lib)
			content += '\n'

		return content

	def _get_genlist(self, tgen, name):
		lst = Utils.to_list(getattr(tgen, name, []))
		lst = [l.path_from(tgen.path) if isinstance(l, Node.Nod3) else l for l in lst]
		return [l.replace('\\', '/') for l in lst]
		
