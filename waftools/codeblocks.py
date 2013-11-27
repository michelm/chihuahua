#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

'''
Introduction
------------
This module exports and converts *waf* project data, for C/C++ programs, 
static- and shared libraries, into **Code::Blocks** project files (.cbp) and 
workspaces (codeblock.workspace).
**Code::Blocks** is an open source integrated development environment for C
and C++. It is available for all major Deskop Operating Systems (MS Windows,
all major Linux distributions and Macintosh OS-X).
See http://www.codeblocks.org for a more detailed description on how to install
and use it for your particular Desktop environment.

Description
-----------
When exporting *waf* project data, a single **Code::Blocks** workspace will be
exported in the top level directory of the *waf* build environment. This 
workspace file will contain references to all exported **Code::Blocks** 
projects and will include dependencies between those projects.

For each single task generator (*waflib.TaskGenerator*), for instance a 
*bld.program(...)* which has been defined within a *wscript* file somewhere in
the build environment, a single **Code::Blocks** project file will be generated
in the same directory as where the task generator has been defined.
The name of this task generator will be used as name for the exported 
**Code::Blocks** project file. If for instance the name of the task generator
is *hello*, then a **Code::Blocks** project file named *hello.cbp* will be 
exported.

The following example presents an overview of an environment in which
**Code::Blocks** files already have been exported::

        .
        ├── components
        │   └── clib
        │       ├── program
        │       │   ├── cprogram.cbp
        │       │   └── wscript
        │       ├── shared
        │       │   ├── cshlib.cbp
        │       │   └── wscript
        │       └── static
        │           ├── cstlib.cbp
        │           └── wscript
        │
        ├── waf.cbp
        ├── codeblocks.workspace
        └── wscript

Furthermore a special **Code::Blocks** project named *waf.cbp* will be
generated in the top level directory of the build environment. This project 
will contain the following build targets:

* build
* clean
* install
* uninstall

Each of these targets contains a single prebuild step for executing a *waf*
command on the entire build environment; building the *clean* target, for 
instance, will result in all build results being removed from the build 
directory in the build environment.

Projects will be exported such that they will use the same settings and 
structure as has been defined for that build task within the *waf* build 
environment. Following present a summary of the items that will be exported to
**Code::Blocks** projects:

* Source files
* Inlcude paths
* Preprocessor defines
* Compiler settings
* Linker settings
* Libraries to be use
* Library search paths
* Build location (same as in *waf* environment)
* Debug and start location (install location as defined in *waf* environment)

All this information will be combined in a single *build* *target* within the 
project. The name of this build target depends on the current environment 
configuration and the compiler being used to build the target; if the build 
environment, for instance, has been configured to build all C/C++ tasks
with debugging information the build target will be named *Debug* otherwise 
it will be named *Release*. If the destination OS and/or destination CPU is 
not the same as current host on which the target will be build, then these 
will also be added to the name of the build target (e.g. *Debug-WIN32* when 
cross compiling for Windows on a Linux host).
Please note that only **one** build target will be exported for each 
environment (see waf *variants*) that has been defined in the actual waf 
build environment. So when using a single waf build environment, i.e. one 
without using variants, **Code::Blocks** projects will be exported for either
*Debug* **or** *Release*, depending on the current configuration.

Usage
-----
**Code::Blocks** project and workspace files can be exported using the *export* 
command, as shown in the example below::

        waf export --export-codeblocks

When needed, exported **Code::Blocks** project- and workspaces files can be 
removed using the *export-clean* command, as shown in the example below::

        waf export --export-cleanup

Once exported simple open the *codeblocks.workspace* using **Code::Blocks**
this will automatically open all exported projects as well.

Module Interface
----------------
Basically the module exposes only two public methods; one for exporting project
files and workspaces (*export*), and one for deleting exporting project files
and workspaces (*cleanup*).
'''

import os
import sys
import copy
import platform
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from waflib import Utils, Node, Logs


def export(bld):
	'''Exports all C and C++ task generators as **Code::Blocks** projects
	and creates a **Code::Blocks** workspace containing references to 
	those project.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.BuildContext
	:returns: None
	'''
	workspace = _CBWorkspace(bld)
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			project = _CBProject(bld, gen, targets)
			project.export()
			workspace.add_project(project.get_metadata())
			cc_name = project.get_toolchain()

	if cc_name != 'gcc':
		Logs.info("")
		Logs.warn("EXPORT NOTIFICATION")
		Logs.warn("Remember to setup your toolchain in Code::Blocks for these projects!")
		Logs.info("")
		Logs.info("Toolchain name: '%s'" % cc_name)
		Logs.info("CC            : '%s'" % bld.export.cc)
		Logs.info("CXX           : '%s'" % bld.export.cxx)
		Logs.info("AR            : '%s'" % bld.export.ar)
		Logs.info("")

	project = _WafCBProject(bld)
	project.export()
	workspace.add_project(project.get_metadata())
	workspace.export()


def cleanup(bld):
	'''Removes all **Code::Blocks** projects and workspaces from the 
	*waf* build environment.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.BuildContext
	:returns: None
	'''
	for gen, targets in bld.components.items():
		project = _CBProject(bld, gen, targets)
		project.cleanup()

	project = _WafCBProject(bld)
	project.cleanup()

	workspace = _CBWorkspace(bld)
	workspace.cleanup()


class _CodeBlocks(object):
	'''Abstract base class used for exporting *waf* project data to 
	**Code::Blocks** projects and workspaces.
	'''

	PROGRAM	= '1'
	STLIB	= '2'
	SHLIB	= '3'
	OBJECT	= '4'

	def __init__(self, bld):
		self.bld = bld
		self.exp = bld.export

	def export(self):
		'''exports a code::blocks workspace or project.'''
		content = self._get_content()
		if not content:
			return
		content = self._xml_clean(content)

		node = self._make_node()
		if not node:
			return
		node.write(content)

	def cleanup(self):
		'''deletes code::blocks workspace or project file including .layout and .depend files'''
		cwd = self._get_cwd()
		for node in cwd.ant_glob('*.layout'):
			node.delete()
		for node in cwd.ant_glob('*.depend'):
			node.delete()
		node = self._find_node()
		if node:
			node.delete()

	def _get_cwd(self):
		cwd = os.path.dirname(self._get_fname())
		if cwd == "":
			cwd = "."
		return self.bld.srcnode.find_node(cwd)

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

	def _get_fname(self): 
		'''<abstract> Returns file name.'''
		return None

	def _get_content(self):
		'''<abstract> Returns file content.'''
		return None

	def _xml_clean(self, content):
		s = minidom.parseString(content).toprettyxml(indent="\t")
		lines = [l for l in s.splitlines() if not l.isspace() and len(l)]
		lines[0] = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
		return '\n'.join(lines)


class _CBWorkspace(_CodeBlocks):
	'''Class used for exporting *waf* project data to a **Code::Blocks** 
	workspace located in the lop level directory of the *waf* build
	environment.
	'''
	def __init__(self, bld):
		super(_CBWorkspace, self).__init__(bld)
		self.projects = {}

	def _get_fname(self):
		'''Returns the workspace's file name.'''
		return 'codeblocks.workspace'

	def _get_content(self):
		'''returns the content of a code::blocks workspace file containing references to all 
		projects and project dependencies.
		'''
		root = ElementTree.fromstring(CODEBLOCKS_WORKSPACE)
		workspace = root.find('Workspace')
		workspace.set('title', self.exp.appname)

		for name in sorted(self.projects.iterkeys()):
			(fname, deps) = self.projects[name]
			project = ElementTree.SubElement(workspace, 'Project', attrib={'filename':fname})
			for dep in deps:
				(fname, _) = self.projects[dep]
				ElementTree.SubElement(project, 'Depends', attrib={'filename':fname})
		return ElementTree.tostring(root)

	def add_project(self, project):
		'''Adds a project to the workspace.'''
		(name, fname, deps) = project
		self.projects[name] = (fname, deps)


class _CBProject(_CodeBlocks):
	'''Class used for exporting *waf* project data to **Code::Blocks** 
	projects.
	'''

	def __init__(self, bld, gen, targets):
		super(_CBProject, self).__init__(bld)
		self.gen = gen
		self.targets = targets

	def _get_fname(self):
		'''Returns the project's file name.'''
		gen = self.gen
		return '%s/%s.cbp' % (gen.path.relpath().replace('\\', '/'), gen.get_name())

	def _get_root(self):
		'''Returns a document root, either from an existing file, or from template.
		'''
		fname = self._get_fname()
		if os.path.exists(fname):
			tree = ElementTree.parse(fname)
			root = tree.getroot()
		else:
			root = ElementTree.fromstring(CODEBLOCKS_PROJECT)
		return root

	def _get_target(self, project, toolchain):
		'''Returns a targets for the requested toolchain name.

		If the target doesn't exist in the project it will be added.
		'''
		build = project.find('Build')
		for target in build.iter('Target'):
			for option in target.iter('Option'):
				if option.get('compiler') in [toolchain, 'XXX']:
					return target

		target = copy.deepcopy(build.find('Target'))
		build.append(target)
		return target

	def _get_content(self):
		'''Returns the content of a project file.'''
		root = self._get_root()
		project = root.find('Project')
		for option in project.iter('Option'):
			if option.get('title'):
				option.set('title', self.gen.get_name())
		
		toolchain = self.get_toolchain()
		target = self._get_target(project, toolchain)
		target.set('title', self._get_target_title())
		target_type = self._get_target_type()

		for option in target.iter('Option'):
			if option.get('output'):
				option.set('output', self._get_output())
			elif option.get('object_output'):
				option.set('object_output', self._get_object_output())
			elif option.get('type'):
				option.set('type', target_type)
			elif option.get('compiler'):
				option.set('compiler', toolchain)
			elif option.get('working_dir'):
				if target_type == _CodeBlocks.PROGRAM:
					option.set('working_dir', self._get_working_directory())

		compiler = target.find('Compiler')
		compiler.clear()
		for option in self._get_compiler_options():
			ElementTree.SubElement(compiler, 'Add', attrib={'option':option})
		for define in self._get_compiler_defines():
			ElementTree.SubElement(compiler, 'Add', attrib={'option':'-D%s' % define})
		for include in self._get_compiler_includes():
			ElementTree.SubElement(compiler, 'Add', attrib={'directory':include})

		linker = target.find('Linker')
		linker.clear()
		for option in self._get_link_options():
			ElementTree.SubElement(linker, 'Add', attrib={'option':option})
		for library in self._get_link_libs():
			ElementTree.SubElement(linker, 'Add', attrib={'library':library})
		for directory in self._get_link_paths():
			ElementTree.SubElement(linker, 'Add', attrib={'directory':directory})
		
		sources = self._get_genlist(self.gen, 'source')
		for unit in project.iter('Unit'):
			source = unit.get('filename')
			if source in sources:
				sources.remove(source)
		for source in sources:
			ElementTree.SubElement(project, 'Unit', attrib={'filename':source})
		
		includes = self._get_includes_files()
		for unit in project.iter('Unit'):
			include = unit.get('filename')
			if include in includes:
				includes.remove(include)
		for include in includes:
			ElementTree.SubElement(project, 'Unit', attrib={'filename':include})
		
		return ElementTree.tostring(root)

	def get_metadata(self):
		'''Returns a tuple containing project information (name, file name and 
		dependencies).
		'''
		gen = self.gen
		name = gen.get_name()
		fname = self._get_fname()
		deps = Utils.to_list(getattr(gen, 'use', []))
		return (name, fname, deps)

	def get_toolchain(self):
		'''Returns the name of the compiler toolchain.
		'''
		if self.gen.env.DEST_OS == 'win32':
			if sys.platform == 'win32':
				toolchain = 'gcc'
			else:
				toolchain = 'mingw32'

		elif self.gen.env.DEST_CPU != platform.processor():
			bld = self.gen.bld
			if bld.variant:
				toolchain = 'gcc_%s' % bld.variant
			else:
				toolchain = 'gcc_%s' % self.gen.env.DEST_CPU

		else:
			toolchain = 'gcc'

		return toolchain

	def _get_target_title(self):
		bld = self.gen.bld
		env = self.gen.env

		if bld.variant:
			title = '%s ' % (bld.variant)
		elif env.DEST_OS in sys.platform \
				and env.DEST_CPU == platform.processor():
			title = ''
		else:
			title = '%s-%s' % (env.DEST_OS, env.DEST_CPU)

		if '-g' in env.CFLAGS or '-g' in env.CXXFLAGS:
			title += 'debug'
		else:
			title += 'release'

		return title.title()

	def _get_buildpath(self):
		bld = self.bld
		gen = self.gen
		pth = '%s/%s' % (bld.path.get_bld().path_from(gen.path), gen.path.relpath())
		return pth.replace('\\', '/')

	def _get_output(self):
		gen = self.gen
		return '%s/%s' % (self._get_buildpath(), gen.get_name())

	def _get_object_output(self):
		return self._get_buildpath()

	def _get_working_directory(self):
		gen = self.gen
		bld = self.bld

		sdir = gen.bld.env.BINDIR
		if sdir.startswith(bld.path.abspath()):
			sdir = os.path.relpath(sdir, gen.path.abspath())

		return sdir.replace('\\', '/')

	def _get_target_type(self):
		gen = self.gen
		if set(('cprogram', 'cxxprogram')) & set(gen.features):
			return '1'
		elif set(('cstlib', 'cxxstlib')) & set(gen.features):
			return '2'
		elif set(('cshlib', 'cxxshlib')) & set(gen.features):
			return '3'
		else:
			return '4'

	def _get_genlist(self, gen, name):
		lst = Utils.to_list(getattr(gen, name, []))
		lst = [l.path_from(gen.path) if isinstance(l, Node.Nod3) else l for l in lst]
		return [l.replace('\\', '/') for l in lst]

	def _get_compiler_options(self):
		bld = self.bld
		gen = self.gen
		if 'cxx' in gen.features:
			flags = getattr(gen, 'cxxflags', []) + bld.env.CXXFLAGS
		else:
			flags = getattr(gen, 'cflags', []) + bld.env.CFLAGS

		if 'cshlib' in gen.features:
			flags.extend(bld.env.CFLAGS_cshlib)
		elif 'cxxshlib' in gen.features:
			flags.extend(bld.env.CXXFLAGS_cxxshlib)
		return list(set(flags))

	def _get_compiler_includes(self):
		gen = self.gen
		includes = self._get_genlist(gen, 'includes')
		return includes

	def _get_compiler_defines(self):
		gen = self.gen
		defines = self._get_genlist(gen, 'defines') + gen.bld.env.DEFINES
		return [d.replace('"', '\\\\"') for d in defines]

	def _get_link_options(self):
		bld = self.bld
		gen = self.gen
		flags = getattr(gen, 'linkflags', []) + bld.env.LINKFLAGS

		if 'cshlib' in gen.features:
			flags.extend(bld.env.LINKFLAGS_cshlib)
		elif 'cxxshlib' in gen.features:
			flags.extend(bld.env.LINKFLAGS_cxxshlib)
		return list(set(flags))

	def _get_link_libs(self):
		bld = self.bld
		gen = self.gen
		libs = Utils.to_list(getattr(gen, 'lib', []))
		deps = Utils.to_list(getattr(gen, 'use', []))
		for dep in deps:
			tgen = bld.get_tgen_by_name(dep)
			if set(('cstlib', 'cshlib', 'cxxstlib', 'cxxshlib')) & set(tgen.features):
				libs.append(dep)
		return libs
	
	def _get_link_paths(self):
		bld = self.bld
		gen = self.gen
		dirs = []
		deps = Utils.to_list(getattr(gen, 'use', []))
		for dep in deps:
			tgen = bld.get_tgen_by_name(dep)
			if set(('cstlib', 'cshlib', 'cxxstlib', 'cxxshlib')) & set(tgen.features):
				directory = tgen.path.get_bld().path_from(gen.path)
				dirs.append(directory.replace('\\', '/'))
		return dirs

	def _get_includes_files(self):
		gen = self.gen
		includes = []
		for include in self._get_genlist(gen, 'includes'):
			node = gen.path.find_dir(include)
			if node:
				for include in node.ant_glob('*.h*'):
					includes.append(include.path_from(gen.path).replace('\\', '/'))
		return includes


class _WafCBProject(_CodeBlocks):
	'''Class used for creating a dummy **Code::Blocks** project containing
	only waf commands as pre-build steps.
	'''

	def __init__(self, bld):
		super(_WafCBProject, self).__init__(bld)
		self.title = 'waf'

	def _get_fname(self):
		'''Returns the file name.'''
		return 'waf.cbp'

	def _get_content(self):
		'''Returns the content of a code::blocks project file.
		'''
		root = ElementTree.fromstring(CODEBLOCKS_PROJECT)
		project = root.find('Project')
		for option in project.iter('Option'):
			if option.get('title'):
				option.set('title', self.title)

		target = project.find('Build/Target')
		target.set('title', 'build')
		for option in target.iter('Option'):
			if option.get('output'):
				option.set('output', '')

			elif option.get('object_output'):
				option.set('object_output', '')

		for cmd in ['clean', 'install', 'uninstall']:
			tgt = copy.deepcopy(target)
			tgt.set('title', cmd)
			project.find('Build').append(tgt)

		for target in project.iter('Target'):
			cmd = 'waf %s' % target.get('title')
			build = ElementTree.SubElement(target, 'ExtraCommands')
			ElementTree.SubElement(build, 'Add', {'before': cmd})

		return ElementTree.tostring(root)

	def get_metadata(self):
		'''Returns a tuple containing project information (name, file name and 
		dependencies).
		'''
		name = self.title
		fname = self._get_fname()
		deps = []
		return (name, fname, deps)


CODEBLOCKS_WORKSPACE = \
'''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<CodeBlocks_workspace_file>
    <Workspace title="Workspace">
    </Workspace>
</CodeBlocks_workspace_file>
'''

CODEBLOCKS_PROJECT = \
'''<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
<CodeBlocks_project_file>
    <FileVersion major="1" minor="6" />
    <Project>
        <Option title="XXX" />
        <Option pch_mode="2" />
        <Option compiler="gcc" />
        <Build>
            <Target title="XXX">
                <Option output="XXX" prefix_auto="1" extension_auto="1" />
                <Option object_output="XXX" />
                <Option working_dir="."/>
                <Option type="2" />
                <Option compiler="XXX" />
                <Compiler/>
                <Linker/>
            </Target>
        </Build>
        <Extensions>
            <code_completion />
            <envvars />
            <debugger />
            <lib_finder disable_auto="1" />
        </Extensions>
    </Project>
</CodeBlocks_project_file>
'''
