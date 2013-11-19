#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

# TODO: add RPATH ??
# TODO: change build location to waf build location ?? 
#       -> hard to realize in Eclipse as soon as binary is not in projec directory
#       CDT no longer is able to find it !?
# TODO: find workaround for multiple taskgen's in the same wscript/directory,
#       since they cannot coexist in the same .cproject file (at the same location).
# TODO: create debug and run launchers for executables

import os
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
import waflib
from waflib import Utils, Node


def export(bld):
	root = WafProject(bld)
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			child = CDTProject(bld, gen, targets)
			child.export()
	root.export()


def cleanup(bld):
	root = WafProject(bld)
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			child = CDTProject(bld, gen, targets)
			child.cleanup()
	root.cleanup()


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
		cwd = self.get_cwd()
		node = self.find_node()
		if node:
			node.delete()

	def get_cwd(self):
		cwd = os.path.dirname(self.get_fname())
		if cwd == "":
			cwd = "."
		return self.bld.srcnode.find_node(cwd)

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
			if triggers:
				ElementTree.SubElement(element, 'triggers').text = triggers
			ElementTree.SubElement(element, 'arguments').text = arguments

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
		self.project.buildcommands.append(('org.python.pydev.PyDevBuilder', None, ''))
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
		path = os.path.dirname(waflib.__file__).replace('\\', '/')
		self.ext_source_paths.append(path)
		path = os.path.dirname(path).replace('\\', '/')
		self.ext_source_paths.append(path)
		

class CDTProject(Project):
	def __init__(self, bld, gen, targets):
		super(CDTProject, self).__init__(bld, gen)
		self.targets = targets
		self.project = Project(bld, gen)
		self.comments = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>','<?fileVersion 4.0.0?>']

		if 'cxx' in self.gen.features:
			self.language = 'cpp'
		else:
			self.language = 'c'
	
		self.is_program = set(('cprogram', 'cxxprogram')) & set(self.gen.features)
		self.is_shlib = set(('cshlib', 'cxxshlib')) & set(self.gen.features)
		self.is_stlib = set(('cstlib', 'cxxstlib')) & set(self.gen.features)
		self.project.natures.append('org.eclipse.cdt.core.cnature')
		if self.language == 'cpp':
			self.project.natures.append('org.eclipse.cdt.core.ccnature')
		self.project.natures.append('org.eclipse.cdt.managedbuilder.core.managedBuildNature')
		self.project.natures.append('org.eclipse.cdt.managedbuilder.core.ScannerConfigNature')
		self.project.buildcommands.append(('org.eclipse.cdt.managedbuilder.core.genmakebuilder', 'clean,full,incremental,', ''))
		self.project.buildcommands.append(('org.eclipse.cdt.managedbuilder.core.ScannerConfigBuilder', 'full,incremental,', ''))

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
		else:
			self.kind_name = 'Executable'
			self.kind = 'exe'

	def export(self):
		super(CDTProject, self).export()
		self.project.export()

	def cleanup(self):
		super(CDTProject, self).cleanup()
		self.project.cleanup()

	def get_fname(self):
		return '%s/.cproject' % (self.gen.path.relpath().replace('\\', '/'))

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


ECLIPSE_PROJECT = \
'''<?xml version="1.0" encoding="UTF-8"?>
<projectDescription>
	<name></name>
	<comment></comment>
	<projects>
	</projects>
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
#TODO: GLDErrorParser not needed for static libs?


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


