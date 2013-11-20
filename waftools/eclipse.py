#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com


import sys
import os
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
import waflib
from waflib import Logs


def export(bld):
	'''Generates Eclipse CDT projects for each C/C++ task.

	Also generates a top level Eclipse PyDev project
	for the WAF build environment itself.
	Warns when multiple task have been defined in the same,
	or top level, directory.
	'''
	scan_project_locations(bld)

	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			project = CDTProject(bld, gen, targets)
			project.export()

	project = WafProject(bld)
	project.export()


def cleanup(bld):
	'''Removes all generated CDT and PyDev project files
	'''
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			project = CDTProject(bld, gen, targets)
			project.cleanup()

	project = WafProject(bld)
	project.cleanup()


def scan_project_locations(bld):
	'''Warns when multiple TaskGen's has been defined in the same directory.

	Since Eclipse works with static project filenames, only one project	per
	directory can be created. If multiple task generators have been defined
	in the same directory (i.e. same wscript) one will overwrite the other(s).
	This problem can only e circumvented by changing the structure of the 
	build environment; i.e. place each single task generator in a seperate 
	directory.
	'''
	locations = { '.': 'waf (top level)' }
	anomalies = {}

	for gen, _ in bld.components.items():
		name = gen.get_name()
		location = str(gen.path.relpath()).replace('\\', '/')
		
		if locations.has_key(location):
			anomalies[name] = location
		else:
			locations[location] = name

	cnt = len(anomalies.keys())
	if cnt != 0:
		Logs.info('')
		Logs.warn('WARNING ECLIPSE EXPORT: TASK LOCATION CONFLICTS(%s)' % cnt)
		Logs.info('Failed to create project files for:')
		s = ' {n:<15} {l:<40}'
		Logs.info(s.format(n='(name)', l='(location)'))
		for (name, location) in anomalies.items():
			Logs.info(s.format(n=name, l=location))
		Logs.info('')
		Logs.info('TIPS:')
		Logs.info('- use one task per directory/wscript.')
		Logs.info('- don\'t place tasks in the top level directory/wscript.')
		Logs.info('')


class Project(object):
	def __init__(self, bld, gen):
		self.bld = bld
		self.exp = bld.export
		self.gen = gen
		self.natures = []
		self.buildcommands = []
		self.comments = ['<?xml version="1.0" encoding="UTF-8"?>']

	def export(self):
		content = self.get_content()
		if not content:
			return
		content = self.xml_clean(content)

		node = self.make_node()
		if not node:
			return
		node.write(content)

	def cleanup(self):
		node = self.find_node()
		if node:
			node.delete()

	def find_node(self):
		name = self.get_fname()
		if not name:
			return None    
		return self.bld.srcnode.find_node(name)

	def make_node(self):
		name = self.get_fname()
		if not name:
			return None    
		return self.bld.srcnode.make_node(name)

	def get_fname(self):
		if self.gen:
			name = '%s/.project' % (self.gen.path.relpath().replace('\\', '/'))
		else:
			name = '.project'
		return name

	def get_content(self):
		root = ElementTree.fromstring(ECLIPSE_PROJECT)
		name = root.find('name')
		name.text = self.get_name()

		if self.gen:
			projects = root.find('projects')
			for project in getattr(self.gen, 'use', []):
				ElementTree.SubElement(projects, 'project').text = project

		buildspec = root.find('buildSpec')
		for buildcommand in self.buildcommands:
			(name, triggers, arguments) = buildcommand
			element = ElementTree.SubElement(buildspec, 'buildCommand')
			ElementTree.SubElement(element, 'name').text = name
			if triggers is not None:
				ElementTree.SubElement(element, 'triggers').text = triggers
			if arguments is not None:
				element.append(arguments)

		natures = root.find('natures')
		for nature in self.natures:
			element = ElementTree.SubElement(natures, 'nature')
			element.text = nature

		return ElementTree.tostring(root)

	def get_name(self):
		if self.gen:
			name = self.gen.get_name()
		else:
			name = self.exp.appname
		return name

	def xml_clean(self, content):
		s = minidom.parseString(content).toprettyxml(indent="\t")
		lines = [l for l in s.splitlines() if not l.isspace() and len(l)]
		lines = self.comments + lines[1:] + ['']
		return '\n'.join(lines)


class PyDevProject(Project):
	def __init__(self, bld, gen, targets):
		super(PyDevProject, self).__init__(bld, gen)
		self.targets = targets
		self.project = Project(bld, gen)
		self.project.natures.append('org.python.pydev.pythonNature')
		self.project.buildcommands.append(('org.python.pydev.PyDevBuilder', None, None))
		self.ext_source_paths = []
		self.comments = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>','<?eclipse-pydev version="1.0"?>']

	def export(self):
		super(PyDevProject, self).export()
		self.project.export()

	def cleanup(self):
		super(PyDevProject, self).cleanup()
		self.project.cleanup()

	def get_fname(self):
		name = '.pydevproject'
		if self.gen:
			name = '%s/%s' % (self.gen.path.relpath(), name)
		return name.replace('\\', '/')

	def get_content(self):
		root = ElementTree.fromstring(ECLIPSE_PYDEVPROJECT)
		for pathproperty in root.iter('pydev_pathproperty'):
			if pathproperty.get('name')	== 'org.python.pydev.PROJECT_EXTERNAL_SOURCE_PATH':
				for source_path in self.ext_source_paths:
					ElementTree.SubElement(pathproperty, 'path').text = source_path
		return ElementTree.tostring(root)


class WafProject(PyDevProject):
	def __init__(self, bld):
		super(WafProject, self).__init__(bld, None, None)
		self.cproject = WafCDT(bld, self.project)

		path = os.path.dirname(waflib.__file__)
		self.ext_source_paths.append(path.replace('\\', '/'))

		path = os.path.dirname(path)
		self.ext_source_paths.append(path.replace('\\', '/'))

	def export(self):
		super(WafProject, self).export()
		self.cproject.export()

	def cleanup(self):
		super(WafProject, self).cleanup()
		self.cproject.cleanup()


class CDTProject(Project):
	def __init__(self, bld, gen, targets, project=None):
		super(CDTProject, self).__init__(bld, gen)
		self.targets = targets
		self.comments = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>','<?fileVersion 4.0.0?>']

		if gen is not None:
			if 'cxx' in gen.features:
				self.language = 'cpp'
			else:
				self.language = 'c'
			self.is_program = set(('cprogram', 'cxxprogram')) & set(gen.features)
			self.is_shlib = set(('cshlib', 'cxxshlib')) & set(gen.features)
			self.is_stlib = set(('cstlib', 'cxxstlib')) & set(gen.features)

		else:
			self.language = 'cpp'
			self.is_program = False
			self.is_shlib = False
			self.is_stlib = False
	
		if project is None:
			project = Project(bld, gen)
		self.project = project

		project.natures.append('org.eclipse.cdt.core.cnature')
		if self.language == 'cpp':
			project.natures.append('org.eclipse.cdt.core.ccnature')
		project.natures.append('org.eclipse.cdt.managedbuilder.core.managedBuildNature')
		project.natures.append('org.eclipse.cdt.managedbuilder.core.ScannerConfigNature')
		project.buildcommands.append(('org.eclipse.cdt.managedbuilder.core.genmakebuilder', 'clean,full,incremental,', None))
		project.buildcommands.append(('org.eclipse.cdt.managedbuilder.core.ScannerConfigBuilder', 'full,incremental,', None))

		self.uuid = {
			'debug': self.get_uuid(),
			'release': self.get_uuid(),
			'c_debug_compiler': self.get_uuid(),
			'c_debug_input': self.get_uuid(),
			'c_release_compiler': self.get_uuid(),
			'c_release_input': self.get_uuid(),
			'cpp_debug_compiler': self.get_uuid(),
			'cpp_debug_input': self.get_uuid(),
			'cpp_release_compiler': self.get_uuid(),
			'cpp_release_input': self.get_uuid(),
		}

		if self.is_shlib:
			self.kind_name = 'Shared Library'
			self.kind = 'so'
		elif self.is_stlib:
			self.kind_name = 'Static Library'
			self.kind = 'lib'
		elif self.is_program:
			self.kind_name = 'Executable'
			self.kind = 'exe'
			self.launch = CDTLaunch(bld, gen, self.uuid['release'])
			self.launch_debug = CDTLaunchDebug(bld, gen, self.uuid['debug'])

	def export(self):
		super(CDTProject, self).export()
		self.project.export()
		if hasattr(self, 'launch'):
			self.launch.export()
		if hasattr(self, 'launch_debug'):
			self.launch_debug.export()

	def cleanup(self):
		super(CDTProject, self).cleanup()
		self.project.cleanup()
		if hasattr(self, 'launch'):
			self.launch.cleanup()
		if hasattr(self, 'launch_debug'):
			self.launch_debug.cleanup()

	def get_fname(self):
		name = '.cproject'
		if self.gen is not None:
			name = '%s/%s' % (self.gen.path.relpath(), name)
		return name.replace('\\', '/')

	def get_content(self):
		root = ElementTree.fromstring(ECLIPSE_CDT_PROJECT)
		for module in root.findall('storageModule'):
			if module.get('moduleId') == 'org.eclipse.cdt.core.settings':
				self.update_cdt_core_settings(module)
			if module.get('moduleId') == 'cdtBuildSystem':
				self.update_buildsystem(module)
			if module.get('moduleId') == 'scannerConfiguration':
				self.update_scannerconfiguration(module)
			if module.get('moduleId') == 'refreshScope':
				self.update_refreshscope(module)
		return ElementTree.tostring(root)

	def get_uuid(self):
		return int(os.urandom(4).encode('hex'), 16)

	def update_buildsystem(self, module):
		attr = {
			'id': '%s.cdt.managedbuild.target.gnu.%s.%s' % (self.gen.get_name(), self.kind, self.get_uuid()),
			'name': self.kind_name,
			'projectType': 'cdt.managedbuild.target.gnu.%s' % (self.kind)
		}
		ElementTree.SubElement(module, 'project', attrib=attr)

	def update_scannerconfiguration(self, module):
		self.add_scanner_config_build_info(module, key='release', language='c')
		self.add_scanner_config_build_info(module, key='debug', language='c')
		if self.language == 'cpp':
			self.add_scanner_config_build_info(module, key='release', language='cpp')
			self.add_scanner_config_build_info(module, key='debug', language='cpp')

	def add_scanner_config_build_info(self, module, key, language):
		cc_uuid = self.uuid['%s_%s_compiler' % (language, key)]
		in_uuid = self.uuid['%s_%s_input' % (language, key)]
		iid = [
			"cdt.managedbuild.config.gnu.%s.%s.%s" % (self.kind, key, self.uuid[key]),
			"cdt.managedbuild.config.gnu.%s.%s.%s." % (self.kind, key, self.uuid[key]),
			"cdt.managedbuild.tool.gnu.%s.compiler.%s.%s.%s" % (language, self.kind, key, cc_uuid),
			"cdt.managedbuild.tool.gnu.%s.compiler.input.%s" % (language, in_uuid)
		]
		element = ElementTree.SubElement(module, 'scannerConfigBuildInfo', {'instanceId':';'.join(iid)})

		attrib= {'enabled':'true', 'problemReportingEnabled':'true', 'selectedProfileId':''}
		ElementTree.SubElement(element, 'autodiscovery', attrib)

	def update_refreshscope(self, module):
		for resource in module.iter('resource'):
			resource.set('workspacePath', '/%s' % self.gen.get_name())

	def update_cdt_core_settings(self, module):
		self.add_cconfiguration(module, key='debug', name='Debug')
		self.add_cconfiguration(module, key='release', name='Release')

	def add_cconfiguration(self, module, key, name):
		ccid = 'cdt.managedbuild.config.gnu.%s.%s.%s' % (self.kind, key, self.uuid[key])
		cconfiguration = ElementTree.SubElement(module, 'cconfiguration', {'id':ccid})
		self.add_configuration_data_provider(cconfiguration, key, name)
		self.add_configuration_cdt_buildsystem(cconfiguration, key, name)
		ElementTree.SubElement(cconfiguration, 'storageModule', {'moduleId':'org.eclipse.cdt.core.externalSettings'})

	def add_configuration_data_provider(self, cconfiguration, key, name):
		module = ElementTree.fromstring(ECLIPSE_CDT_DATAPROVIDER)
		settings = module.find('externalSettings')
		if self.is_program:
			settings.clear()
		else:
			for entry in settings.iter('entry'):
				if entry.get('kind') == 'includePath':
					entry.set('name', '/%s' % self.gen.get_name())
				if entry.get('kind') == 'libraryPath':
					entry.set('name', '/%s/%s' % (self.gen.get_name(),name))
				if entry.get('kind') == 'libraryFile':
					entry.set('name', '%s' % self.gen.get_name())
		for extension in module.find('extensions').iter('extension'):
			if extension.get('point') == 'org.eclipse.cdt.core.BinaryParser':
				eid = extension.get('id')
				if self.gen.env.DEST_OS == 'win32':
					extension.set('id', eid.replace('.ELF', '.PE'))

		provider = ElementTree.SubElement(cconfiguration, 'storageModule')
		provider.set('id', 'cdt.managedbuild.config.gnu.%s.%s.%s' % (self.kind, key, self.uuid[key]))
		provider.set('name', name)
		provider.set('buildSystemId', 'org.eclipse.cdt.managedbuilder.core.configurationDataProvider')
		provider.set('moduleId', 'org.eclipse.cdt.core.settings') 
		provider.extend(module)

	def add_configuration_cdt_buildsystem(self, cconfiguration, key, name):
		module = ElementTree.fromstring(ECLIPSE_CDT_BUILDSYSTEM)
		config = module.find('configuration')
		config.set('name', name)
		if self.is_shlib:
			config.set('buildArtefactType', 'org.eclipse.cdt.build.core.buildArtefactType.sharedLib')
			config.set('artifactExtension', 'so')
		elif self.is_stlib:
			config.set('buildArtefactType', 'org.eclipse.cdt.build.core.buildArtefactType.staticLib')
			config.set('artifactExtension', 'a')
		else:
			config.set('buildArtefactType', 'org.eclipse.cdt.build.core.buildArtefactType.exe')

		config.set('parent', 'cdt.managedbuild.config.gnu.%s.%s' % (self.kind, key))
		config.set('id', '%s.%s' % (config.get('parent'), self.uuid[key]))

		btype = 'org.eclipse.cdt.build.core.buildType=org.eclipse.cdt.build.core.buildType.%s' % key
		atype = 'org.eclipse.cdt.build.core.buildArtefactType=%s' % config.get('buildArtefactType')
		config.set('buildProperties', '%s,%s' % (btype, atype))
	
		folder = config.find('folderInfo')
		folder.set('id','cdt.managedbuild.config.gnu.%s.%s.%s.' % (self.kind, key, self.uuid[key]))
		self.update_toolchain(folder, key, name)
		cconfiguration.append(module)

	def update_toolchain(self, folder, key, name):
		toolchain = folder.find('toolChain')
		toolchain.set('superClass', 'cdt.managedbuild.toolchain.gnu.%s.%s' % (self.kind, key))
		toolchain.set('id', '%s.%s' % (toolchain.get('superClass'), self.get_uuid()))

		target = toolchain.find('targetPlatform')
		target.set('name', '%s Platform' % name)
		target.set('superClass', 'cdt.managedbuild.target.gnu.platform.%s.%s' % (self.kind, key))
		target.set('id', '%s.%s' % (target.get('superClass'), self.get_uuid()))

		builder = toolchain.find('builder')
		builder.set('buildPath', '${workspace_loc:/%s}/%s' % (self.gen.get_name(), key.title()))
		builder.set('superClass', 'cdt.managedbuild.target.gnu.builder.%s.%s' % (self.kind, key))
		builder.set('id', '%s.%s' % (builder.get('superClass'), self.get_uuid()))

		archiver = ElementTree.SubElement(toolchain, 'tool', {'name':'GCC Archiver'})
		if self.is_stlib:
			archiver.set('superClass', 'cdt.managedbuild.tool.gnu.archiver.lib.%s' % key)
		else:
			archiver.set('superClass', 'cdt.managedbuild.tool.gnu.archiver.base')
		archiver.set('id', '%s.%s' % (archiver.get('superClass'), self.get_uuid()))

		self.add_compiler(toolchain, key, 'cpp', 'GCC C++ Compiler')
		self.add_compiler(toolchain, key, 'c', 'GCC C Compiler')
		self.add_linker(toolchain, key, 'c', 'GCC C Linker')
		self.add_linker(toolchain, key, 'cpp', 'GCC C++ Linker')

		assembler = ElementTree.SubElement(toolchain, 'tool', {'name':'GCC Assembler'})
		assembler.set('superClass', 'cdt.managedbuild.tool.gnu.assembler.%s.%s' % (self.kind, key))
		assembler.set('id', '%s.%s' % (assembler.get('superClass'), self.get_uuid()))
		inputtype = ElementTree.SubElement(assembler, 'inputType')
		inputtype.set('superClass', 'cdt.managedbuild.tool.gnu.assembler.input')
		inputtype.set('id', '%s.%s' % (inputtype.get('superClass'), self.get_uuid()))

	def add_compiler(self, toolchain, key, language, name):
		uuid = self.uuid['%s_%s_compiler' % (language, key)]
		compiler = ElementTree.SubElement(toolchain, 'tool', {'name' : name})
		compiler.set('superClass', 'cdt.managedbuild.tool.gnu.%s.compiler.%s.%s' % (language, self.kind, key))
		compiler.set('id', '%s.%s' % (compiler.get('superClass'), uuid))
		self.add_cc_options(compiler, key, language)
		self.add_cc_includes(compiler, key, language)
		self.add_cc_preprocessor(compiler, key, language)
		self.add_cc_input(compiler, key, 'c')
		if self.language == 'cpp':
			self.add_cc_input(compiler, key, 'cpp')
		return compiler

	def add_cc_options(self, compiler, key, language):
		if 'debug' in key:
			optimization_level = 'none'
			debug_level = 'max'
		else:
			optimization_level = 'most'
			debug_level = 'none'

		option = ElementTree.SubElement(compiler, 'option', {'name':'Optimization Level', 'valueType':'enumerated'})
		option.set('superClass', 'gnu.%s.compiler.%s.%s.option.optimization.level' % (language, self.kind, key))
		option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))

		if language == 'cpp':
			option.set('value', 'gnu.cpp.compiler.optimization.level.%s' % (optimization_level))
		else:
			option.set('value', 'gnu.c.optimization.level.%s' % (optimization_level))

		option = ElementTree.SubElement(compiler, 'option', {'name':'Debug Level', 'valueType':'enumerated'})
		option.set('superClass', 'gnu.%s.compiler.%s.%s.option.debugging.level' % (language, self.kind, key))
		option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))
		if language == 'cpp':
			option.set('value', 'gnu.cpp.compiler.debugging.level.%s' % (debug_level))
		else:
			option.set('value', 'gnu.c.debugging.level.%s' % (debug_level))

		if self.is_shlib and self.is_language(language):
			option = ElementTree.SubElement(compiler, 'option', {'value':'true','valueType':'boolean'})
			option.set('superClass', 'gnu.%s.compiler.option.misc.pic' % language)
			option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))

	def add_cc_includes(self, compiler, key, language):
		if not self.is_language(language):
			return
		uses = getattr(self.gen, 'use', [])
		includes = getattr(self.gen, 'includes', [])
		if not len(uses) and not len(includes):
			return

		option = ElementTree.SubElement(compiler, 'option', {'name':'Include paths (-I)', 'valueType':'includePath'})
		option.set('superClass', 'gnu.%s.compiler.option.include.paths' % (language))
		option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))

		for include in [str(i).lstrip('./') for i in includes]:
			listoption = ElementTree.SubElement(option, 'listOptionValue', {'builtIn':'false'})
			listoption.set('value', '"${workspace_loc:/${ProjName}/%s}"' % (include))

		for use in uses:			
			tgen = self.bld.get_tgen_by_name(use)
			includes = getattr(tgen, 'export_includes', [])
			for include in [i.lstrip('./') for i in includes]:
				listoption = ElementTree.SubElement(option, 'listOptionValue', {'builtIn':'false'})
				listoption.set('value', '"${workspace_loc:/%s/%s}"' % (use, include))

	def add_cc_preprocessor(self, compiler, key, language):
		if not self.is_language(language):
			return
		defines = list(self.gen.env.DEFINES)
		if key == 'debug':
			defines.remove('NDEBUG')
		if not len(defines):
			return
		defines = [d.replace('"', '\\"') for d in defines]

		if language == 'cpp':
			superclass = 'gnu.cpp.compiler.option.preprocessor.def'
		else:
			superclass = 'gnu.c.compiler.option.preprocessor.def.symbols'

		option = ElementTree.SubElement(compiler, 'option', {'name':'Defined symbols (-D)', 'valueType':'definedSymbols'})
		option.set('superClass', superclass)
		option.set('id', '%s.%s' % (superclass, self.get_uuid()))

		for define in defines:
			listoption = ElementTree.SubElement(option, 'listOptionValue', {'builtIn':'false'})
			listoption.set('value', define)

	def add_cc_input(self, compiler, key, language):
		if not compiler.get('id').count('.%s.' % language):
			return

		uuid = self.uuid['%s_%s_input' % (language, key)]
		inputtype = ElementTree.SubElement(compiler, 'inputType')
		inputtype.set('superClass', 'cdt.managedbuild.tool.gnu.%s.compiler.input' % (language))
		inputtype.set('id', '%s.%s' % (inputtype.get('superClass'), uuid))
		
		if self.is_shlib:
			ElementTree.SubElement(inputtype, 'additionalInput', {'kind':'additionalinputdependency', 'paths':'$(USER_OBJS)'})
			ElementTree.SubElement(inputtype, 'additionalInput', {'kind':'additionalinput', 'paths':'$(LIBS)'})

	def add_linker(self, toolchain, key, language, name):
		if self.is_stlib:
			superclass = 'cdt.managedbuild.tool.gnu.%s.linker.base' % (language)
		else:
			superclass = 'cdt.managedbuild.tool.gnu.%s.linker.%s.%s' % (language, self.kind, key)

		linker = ElementTree.SubElement(toolchain, 'tool', {'name':name})
		linker.set('superClass', superclass)
		linker.set('id', '%s.%s' % (superclass, self.get_uuid()))

		if self.is_shlib:
			option = ElementTree.SubElement(linker, 'option', {'name':'Shared (-shared)', 'defaultValue':'true', 'valueType':'boolean'})
			option.set('superClass', 'gnu.%s.link.so.%s.option.shared' % (language, key))
			option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))

		self.add_linker_libs(linker, key, language)
		self.add_linker_lib_paths(linker, key, language)
		self.add_linker_input(linker, key, language)
		return linker

	def add_linker_libs(self, linker, key, language):
		if not self.is_language(language):
			return

		libs = getattr(self.gen, 'lib', [])
		for use in getattr(self.gen, 'use', []):
			tgen = self.bld.get_tgen_by_name(use)
			if set(('cstlib', 'cshlib','cxxstlib', 'cxxshlib')) & set(tgen.features):
				libs.append(tgen.get_name())
		if not len(libs):
			return

		option = ElementTree.SubElement(linker, 'option', {'name':'Libraries (-l)', 'valueType':'libs'})
		option.set('superClass', 'gnu.%s.link.option.libs' % (language))
		option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))

		for lib in libs:
			listoption = ElementTree.SubElement(option, 'listOptionValue', {'builtIn':'false'})
			listoption.set('value', lib)

	def add_linker_lib_paths(self, linker, key, language):
		if not self.is_language(language):
			return

		libs = [] # TODO: add env.LIBDIR ??
		for use in getattr(self.gen, 'use', []):
			tgen = self.bld.get_tgen_by_name(use)
			if set(('cstlib', 'cshlib','cxxstlib', 'cxxshlib')) & set(tgen.features):
				libs.append(tgen.get_name())
		if not len(libs):
			return

		option = ElementTree.SubElement(linker, 'option', {'name':'Library search path (-L)', 'valueType':'libPaths'})
		option.set('superClass', 'gnu.%s.link.option.paths' % (language))
		option.set('id', '%s.%s' % (option.get('superClass'), self.get_uuid()))

		for lib in libs:
			listoption = ElementTree.SubElement(option, 'listOptionValue', {'builtIn':'false'})
			listoption.set('value', '"${workspace_loc:/%s/%s}"' % (lib, key.title()))

	def add_linker_input(self, linker, key, language):
		if not self.is_language(language):
			return
		if self.is_stlib:
			return

		inputtype = ElementTree.SubElement(linker, 'inputType')
		inputtype.set('superClass', 'cdt.managedbuild.tool.gnu.%s.linker.input' % (language))
		inputtype.set('id', '%s.%s' % (inputtype.get('superClass'), self.get_uuid()))
		ElementTree.SubElement(inputtype, 'additionalInput', {'kind':'additionalinputdependency', 'paths':'$(USER_OBJS)'})
		ElementTree.SubElement(inputtype, 'additionalInput', {'kind':'additionalinput', 'paths':'$(LIBS)'})

	def is_language(self, language):
		if language == 'cpp':
			language = 'cxx'
		return language in self.gen.features


class WafCDT(CDTProject):
	def __init__(self, bld, project):
		super(WafCDT, self).__init__(bld, None, None, project)
		self.comments = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>','<?fileVersion 4.0.0?>']
		self.waf = str(os.path.abspath(sys.argv[0])).replace('\\', '/')

	def get_content(self):
		root = ElementTree.fromstring(ECLIPSE_CDT_PROJECT)
		for module in root.findall('storageModule'):
			if module.get('moduleId') == 'org.eclipse.cdt.core.settings':
				self.update_cdt_core_settings(module)

			if module.get('moduleId') == 'cdtBuildSystem':
				self.update_cdt_buildsystem(module)

			if module.get('moduleId') == 'scannerConfiguration':
				self.update_scanner_configuration(module)

			if module.get('moduleId') == 'refreshScope':
				root.remove(module)

		self.add_buildtargets(root)
		return ElementTree.tostring(root)

	def update_cdt_core_settings(self, module):
		cconfig = ElementTree.fromstring(ECLIPSE_CDT_WAF_CONFIG)

		for extension in cconfig.find('storageModule/extensions').iter('extension'):
			if extension.get('point') == 'org.eclipse.cdt.core.BinaryParser':
				eid = extension.get('id')
				if self.bld.env.DEST_OS == 'win32':
					extension.set('id', eid.replace('.ELF', '.PE'))

		config = cconfig.find('storageModule/configuration')
		config.set('artifactName', self.exp.appname)

		platform = config.find('folderInfo/toolChain/targetPlatform')
		parser = platform.get('binaryParser')
		if self.bld.env.DEST_OS == 'win32':
			platform.set('binaryParser', parser.replace('.ELF', '.PE'))

		builder = config.find('folderInfo/toolChain/builder')
		builder.set('autoBuildTarget', '"%s" build' % self.waf)
		builder.set('cleanBuildTarget', '"%s" clean' % self.waf)
		builder.set('incrementalBuildTarget', '"%s" build' % self.waf)
		builder.set('command', str(sys.executable).replace('\\', '/'))

		module.append(cconfig)

	def update_cdt_buildsystem(self, module):
		name = self.exp.appname
		ElementTree.SubElement(module, 'project', {'id':'%s.null.1' % name, 'name': name})

	def update_scanner_configuration(self, module):
		scanner = ElementTree.SubElement(module, 'scannerConfigBuildInfo')
		scanner.set('instanceId', 'org.eclipse.cdt.core.default.config.1')
		ElementTree.SubElement(scanner, 'autodiscovery', {'enabled':'true', 'problemReportingEnabled':'true', 'selectedProfileId':''})

	def add_buildtargets(self, root):
		targets = {
			'configure' : 'configure',
			'dist'		: 'dist',
			'install'	: 'install',
			'build'		: 'build',
			'clean'		: 'clean',
			'uninstall'	: 'uninstall',
			'distclean'	: 'distclean',
		}

		module = ElementTree.SubElement(root, 'storageModule', {'moduleId':'org.eclipse.cdt.make.core.buildtargets'})
		buildtargets = ElementTree.SubElement(module, 'buildTargets')
		for (name, value) in targets.items():
			target = ElementTree.SubElement(buildtargets, 'target', {'name':name, 'path':''})
			target.set('targetID', 'org.eclipse.cdt.build.MakeTargetBuilder')
			ElementTree.SubElement(target, 'buildCommand').text = str(sys.executable).replace('\\', '/')
			ElementTree.SubElement(target, 'buildArguments')
			ElementTree.SubElement(target, 'buildTarget').text = '"%s" %s' % (self.waf, value)
			ElementTree.SubElement(target, 'stopOnError').text = 'true'
			ElementTree.SubElement(target, 'useDefaultCommand').text = 'false'
			ElementTree.SubElement(target, 'runAllBuilders').text = 'false'


class CDTLaunch(Project):
	def __init__(self, bld, gen, uuid):
		super(CDTLaunch, self).__init__(bld, gen)
		self.comments = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>']
		self.template = ECLIPSE_CDT_LAUNCH_RELEASE
		self.build_dir = 'Release'
		self.build_config_id = 'cdt.managedbuild.config.gnu.exe.release.%s' % uuid

	def get_fname(self):
		name = '%s(release).launch' % self.gen.get_name()
		if self.gen:
			name = '%s/%s' % (self.gen.path.relpath(), name)
		return name.replace('\\', '/')

	def get_content(self):
		root = ElementTree.fromstring(self.template)
		for attrib in root.iter('stringAttribute'):
			if attrib.get('key') == 'org.eclipse.cdt.launch.PROGRAM_NAME':
				attrib.set('value', '%s/%s' % (self.build_dir, self.gen.get_name()))
			if attrib.get('key') == 'org.eclipse.cdt.launch.PROJECT_ATTR':
				attrib.set('value', self.gen.get_name())
			if attrib.get('key') == 'org.eclipse.cdt.launch.PROJECT_BUILD_CONFIG_ID_ATTR':
				attrib.set('value', self.build_config_id)
			if attrib.get('key') == 'org.eclipse.cdt.launch.WORKING_DIRECTORY':
				start_dir = str(self.bld.env.BINDIR).replace('\\', '/')
				attrib.set('value', start_dir)

		for attrib in root.iter('listAttribute'):
			if attrib.get('key') == 'org.eclipse.debug.core.MAPPED_RESOURCE_PATHS':
				attrib.find('listEntry').set('value', '/%s' % self.gen.get_name())

		attrib = root.find('mapAttribute')
		for use in getattr(self.gen, 'use', []):
			tgen = self.bld.get_tgen_by_name(use)
			if set(('cshlib', 'cxxshlib')) & set(tgen.features):
				mapentry = ElementTree.SubElement(attrib, 'mapEntry', {'key':'LD_LIBRARY_PATH'})
				mapentry.set('value', '${workspace_loc:/%s}/Release' % tgen.get_name())

		return ElementTree.tostring(root)


class CDTLaunchDebug(CDTLaunch):
	def __init__(self, bld, gen, uuid):
		super(CDTLaunchDebug, self).__init__(bld, gen, uuid)
		self.template = ECLIPSE_CDT_LAUNCH_DEBUG
		self.build_dir = 'Debug'
		self.build_config_id = 'cdt.managedbuild.config.gnu.exe.debug.%s' % uuid

	def get_fname(self):
		name = '%s(debug).launch' % self.gen.get_name()
		if self.gen:
			name = '%s/%s' % (self.gen.path.relpath(), name)
		return name.replace('\\', '/')


ECLIPSE_PROJECT = \
'''<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
	<name></name>
	<comment></comment>
	<projects/>
	<buildSpec>
	</buildSpec>
	<natures>
	</natures>
</projectDescription>
'''


ECLIPSE_PYDEVPROJECT = \
'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?eclipse-pydev version="1.0"?>
<pydev_project>
	<pydev_pathproperty name="org.python.pydev.PROJECT_SOURCE_PATH">
		<path>/${PROJECT_DIR_NAME}</path>
	</pydev_pathproperty>
	<pydev_property name="org.python.pydev.PYTHON_PROJECT_VERSION">python 2.7</pydev_property>
	<pydev_property name="org.python.pydev.PYTHON_PROJECT_INTERPRETER">Default</pydev_property>
	<pydev_pathproperty name="org.python.pydev.PROJECT_EXTERNAL_SOURCE_PATH">
	</pydev_pathproperty>
</pydev_project>
'''


ECLIPSE_CDT_PROJECT = \
'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<?fileVersion 4.0.0?>
<cproject storage_type_id="org.eclipse.cdt.core.XmlProjectDescriptionStorage">
	<storageModule moduleId="org.eclipse.cdt.core.settings">
	</storageModule>
	<storageModule moduleId="cdtBuildSystem" version="4.0.0">
	</storageModule>
	<storageModule moduleId="scannerConfiguration">
		<autodiscovery enabled="true" problemReportingEnabled="true" selectedProfileId=""/>
	</storageModule>
	<storageModule moduleId="org.eclipse.cdt.core.LanguageSettingsProviders"/>
	<storageModule moduleId="refreshScope" versionNumber="2">
		<configuration configurationName="Release">
			<resource resourceType="PROJECT" workspacePath=""/>
		</configuration>
		<configuration configurationName="Debug">
			<resource resourceType="PROJECT" workspacePath=""/>
		</configuration>
	</storageModule>
</cproject>
'''


ECLIPSE_CDT_DATAPROVIDER = '''
<storageModule buildSystemId="org.eclipse.cdt.managedbuilder.core.configurationDataProvider" id="" moduleId="org.eclipse.cdt.core.settings" name="">
	<externalSettings>
		<externalSetting>
			<entry flags="VALUE_WORKSPACE_PATH" kind="includePath" name=""/>
			<entry flags="VALUE_WORKSPACE_PATH" kind="libraryPath" name=""/>
			<entry flags="RESOLVED" kind="libraryFile" name="" srcPrefixMapping="" srcRootPath=""/>
		</externalSetting>
	</externalSettings>
	<extensions>
		<extension id="org.eclipse.cdt.core.GmakeErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
		<extension id="org.eclipse.cdt.core.CWDLocator" point="org.eclipse.cdt.core.ErrorParser"/>
		<extension id="org.eclipse.cdt.core.GCCErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
		<extension id="org.eclipse.cdt.core.GASErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
		<extension id="org.eclipse.cdt.core.GLDErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
		<extension id="org.eclipse.cdt.core.ELF" point="org.eclipse.cdt.core.BinaryParser"/>
	</extensions>
</storageModule>
'''


ECLIPSE_CDT_BUILDSYSTEM = '''
<storageModule moduleId="cdtBuildSystem" version="4.0.0">
	<configuration artifactName="${ProjName}" buildArtefactType="" buildProperties="" cleanCommand="rm -rf" description="" id="" name="" parent="">
		<folderInfo id="" name="/" resourcePath="">
			<toolChain id="" name="Linux GCC" superClass="">
				<targetPlatform id="" name="" superClass=""/>
				<builder buildPath="" id="" keepEnvironmentInBuildfile="false" managedBuildOn="true" name="Gnu Make Builder" superClass=""/>
			</toolChain>
		</folderInfo>
	</configuration>
</storageModule>
'''


ECLIPSE_CDT_LAUNCH_DEBUG = \
'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<launchConfiguration type="org.eclipse.cdt.launch.applicationLaunchType">
	<stringAttribute key="org.eclipse.cdt.debug.mi.core.DEBUG_NAME" value="gdb"/>
	<stringAttribute key="org.eclipse.cdt.debug.mi.core.GDB_INIT" value=".gdbinit"/>
	<stringAttribute key="org.eclipse.cdt.debug.mi.core.commandFactory" value="org.eclipse.cdt.debug.mi.core.standardLinuxCommandFactory"/>
	<booleanAttribute key="org.eclipse.cdt.debug.mi.core.verboseMode" value="false"/>
	<booleanAttribute key="org.eclipse.cdt.dsf.gdb.AUTO_SOLIB" value="true"/>
	<listAttribute key="org.eclipse.cdt.dsf.gdb.AUTO_SOLIB_LIST"/>
	<stringAttribute key="org.eclipse.cdt.dsf.gdb.DEBUG_NAME" value="gdb"/>
	<booleanAttribute key="org.eclipse.cdt.dsf.gdb.DEBUG_ON_FORK" value="false"/>
	<stringAttribute key="org.eclipse.cdt.dsf.gdb.GDB_INIT" value=".gdbinit"/>
	<booleanAttribute key="org.eclipse.cdt.dsf.gdb.NON_STOP" value="false"/>
	<booleanAttribute key="org.eclipse.cdt.dsf.gdb.REVERSE" value="false"/>
	<listAttribute key="org.eclipse.cdt.dsf.gdb.SOLIB_PATH"/>
	<stringAttribute key="org.eclipse.cdt.dsf.gdb.TRACEPOINT_MODE" value="TP_NORMAL_ONLY"/>
	<booleanAttribute key="org.eclipse.cdt.dsf.gdb.UPDATE_THREADLIST_ON_SUSPEND" value="false"/>
	<booleanAttribute key="org.eclipse.cdt.dsf.gdb.internal.ui.launching.LocalApplicationCDebuggerTab.DEFAULTS_SET" value="true"/>
	<intAttribute key="org.eclipse.cdt.launch.ATTR_BUILD_BEFORE_LAUNCH_ATTR" value="2"/>
	<stringAttribute key="org.eclipse.cdt.launch.DEBUGGER_ID" value="gdb"/>
	<stringAttribute key="org.eclipse.cdt.launch.DEBUGGER_START_MODE" value="run"/>
	<booleanAttribute key="org.eclipse.cdt.launch.DEBUGGER_STOP_AT_MAIN" value="true"/>
	<stringAttribute key="org.eclipse.cdt.launch.DEBUGGER_STOP_AT_MAIN_SYMBOL" value="main"/>
	<stringAttribute key="org.eclipse.cdt.launch.PROGRAM_NAME" value=""/>
	<stringAttribute key="org.eclipse.cdt.launch.PROJECT_ATTR" value=""/>
	<stringAttribute key="org.eclipse.cdt.launch.PROJECT_BUILD_CONFIG_ID_ATTR" value="cdt.managedbuild.config.gnu.exe.debug.1878333522"/>
	<stringAttribute key="org.eclipse.cdt.launch.WORKING_DIRECTORY" value=""/>
	<booleanAttribute key="org.eclipse.cdt.launch.use_terminal" value="true"/>
	<listAttribute key="org.eclipse.debug.core.MAPPED_RESOURCE_PATHS">
		<listEntry value=""/>
	</listAttribute>
	<listAttribute key="org.eclipse.debug.core.MAPPED_RESOURCE_TYPES">
		<listEntry value="4"/>
	</listAttribute>
	<mapAttribute key="org.eclipse.debug.core.environmentVariables">
	</mapAttribute>
	<stringAttribute key="org.eclipse.dsf.launch.MEMORY_BLOCKS" value="&lt;?xml version=&quot;1.0&quot; encoding=&quot;UTF-8&quot; standalone=&quot;no&quot;?&gt;&#10;&lt;memoryBlockExpressionList context=&quot;reserved-for-future-use&quot;/&gt;&#10;"/>
	<stringAttribute key="process_factory_id" value="org.eclipse.cdt.dsf.gdb.GdbProcessFactory"/>
</launchConfiguration>
'''


ECLIPSE_CDT_LAUNCH_RELEASE = \
'''<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<launchConfiguration type="org.eclipse.cdt.launch.applicationLaunchType">
	<stringAttribute key="org.eclipse.cdt.debug.mi.core.DEBUG_NAME" value="gdb"/>
	<stringAttribute key="org.eclipse.cdt.debug.mi.core.GDB_INIT" value=".gdbinit"/>
	<stringAttribute key="org.eclipse.cdt.debug.mi.core.commandFactory" value="org.eclipse.cdt.debug.mi.core.standardLinuxCommandFactory"/>
	<booleanAttribute key="org.eclipse.cdt.debug.mi.core.verboseMode" value="false"/>
	<intAttribute key="org.eclipse.cdt.launch.ATTR_BUILD_BEFORE_LAUNCH_ATTR" value="2"/>
	<stringAttribute key="org.eclipse.cdt.launch.DEBUGGER_ID" value="org.eclipse.cdt.debug.mi.core.CDebuggerNew"/>
	<stringAttribute key="org.eclipse.cdt.launch.DEBUGGER_START_MODE" value="run"/>
	<stringAttribute key="org.eclipse.cdt.launch.PROGRAM_NAME" value=""/>
	<stringAttribute key="org.eclipse.cdt.launch.PROJECT_ATTR" value=""/>
	<stringAttribute key="org.eclipse.cdt.launch.PROJECT_BUILD_CONFIG_ID_ATTR" value=""/>
	<stringAttribute key="org.eclipse.cdt.launch.WORKING_DIRECTORY" value=""/>
	<booleanAttribute key="org.eclipse.cdt.launch.use_terminal" value="true"/>
	<listAttribute key="org.eclipse.debug.core.MAPPED_RESOURCE_PATHS">
		<listEntry value=""/>
	</listAttribute>
	<listAttribute key="org.eclipse.debug.core.MAPPED_RESOURCE_TYPES">
		<listEntry value="4"/>
	</listAttribute>
	<mapAttribute key="org.eclipse.debug.core.environmentVariables">
	</mapAttribute>
</launchConfiguration>
'''


ECLIPSE_CDT_WAF_CONFIG = '''
<cconfiguration id="org.eclipse.cdt.core.default.config.1">
	<storageModule buildSystemId="org.eclipse.cdt.managedbuilder.core.configurationDataProvider" id="org.eclipse.cdt.core.default.config.1" moduleId="org.eclipse.cdt.core.settings" name="Default">
		<externalSettings/>
		<extensions>
			<extension id="org.eclipse.cdt.core.VCErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
			<extension id="org.eclipse.cdt.core.GCCErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
			<extension id="org.eclipse.cdt.core.GASErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
			<extension id="org.eclipse.cdt.core.GLDErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
			<extension id="org.eclipse.cdt.core.GmakeErrorParser" point="org.eclipse.cdt.core.ErrorParser"/>
			<extension id="org.eclipse.cdt.core.CWDLocator" point="org.eclipse.cdt.core.ErrorParser"/>
			<extension id="org.eclipse.cdt.core.ELF" point="org.eclipse.cdt.core.BinaryParser"/>
		</extensions>
	</storageModule>
	<storageModule moduleId="cdtBuildSystem" version="4.0.0">
		<configuration artifactName="" buildProperties="" description="" id="org.eclipse.cdt.core.default.config.1" name="Waf Build" parent="org.eclipse.cdt.build.core.prefbase.cfg">
			<folderInfo id="org.eclipse.cdt.core.default.config.1." name="/" resourcePath="">
				<toolChain id="org.eclipse.cdt.build.core.prefbase.toolchain.1" name="No ToolChain" resourceTypeBasedDiscovery="false" superClass="org.eclipse.cdt.build.core.prefbase.toolchain">
					<targetPlatform binaryParser="org.eclipse.cdt.core.ELF" id="org.eclipse.cdt.build.core.prefbase.toolchain.1" name=""/>
					<builder autoBuildTarget="; build" cleanBuildTarget="" command="" enableAutoBuild="false" id="org.eclipse.cdt.build.core.settings.default.builder.1" incrementalBuildTarget="" keepEnvironmentInBuildfile="false" managedBuildOn="false" name="Gnu Make Builder" superClass="org.eclipse.cdt.build.core.settings.default.builder">
						<outputEntries>
							<entry flags="VALUE_WORKSPACE_PATH|RESOLVED" kind="outputPath" name=""/>
						</outputEntries>
					</builder>
					<tool id="org.eclipse.cdt.build.core.settings.holder.libs.353273715" name="holder for library settings" superClass="org.eclipse.cdt.build.core.settings.holder.libs"/>
				</toolChain>
			</folderInfo>
		</configuration>
	</storageModule>
	<storageModule moduleId="org.eclipse.cdt.core.externalSettings"/>
</cconfiguration>
'''


