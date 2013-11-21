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

For each single task generator, for instance a *bld.program(...)* which has been
defined within a *wscript* file somewhere in the build environment, a single 
**Code::Blocks** project file will be generated in the same directory as where
the task generator has been defined. 
The name of task generator will be used as name for the exported 
**Code::Blocks** project file. If for instance the name of the task generator
is 'hello', then a **Code::Blocks** project file named *hello.cbp* will be 
exported in the same directory as where the task generator has been defined.

The following example presents an overview of an environment in which **Code::Blocks** 
files already have been exported::

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
        ├── codeblocks.workspace
        └── wscript



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
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
from waflib import Utils, Node


def export(bld):
	'''Exports all C and C++ task generators as **Code::Blocks** projects
	and creates a **Code::Blocks** workspace containing references to 
	those project.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.BuildContext
	:returns: None
	'''
	root = _CBWorkspace(bld)
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			child = _CBProject(bld, gen, targets)
			child.export()
			root.add_child(child.get_data())
	root.export()


def cleanup(bld):
	'''Removes all **Code::Blocks** projects and workspaces from the 
	*waf* build environment.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.BuildContext
	:returns: None
	'''
	root = _CBWorkspace(bld)
	for gen, targets in bld.components.items():
		child = CBProject(bld, gen, targets)
		child.cleanup()
	root.cleanup()


class _CodeBlocks(object):
	'''Abstract base class used for exporting *waf* project data to 
	**Code::Blocks** projects and workspaces.
	'''
	def __init__(self, bld):
		self.bld = bld
		self.exp = bld.export

	def export(self):
		'''exports a code::blocks workspace or project.'''
		content = self.get_content()
		if not content:
			return
		content = self._xml_clean(content)

		node = self.make_node()
		if not node:
			return
		node.write(content)

	def cleanup(self):
		'''deletes code::blocks workspace or project file including .layout and .depend files'''
		cwd = self.get_cwd()
		for node in cwd.ant_glob('*.layout'):
			node.delete()
		for node in cwd.ant_glob('*.depend'):
			node.delete()
		node = self.find_node()
		if node:
			node.delete()

	def get_cwd(self):
		cwd = os.path.dirname(self.get_name())
		if cwd == "":
			cwd = "."
		return self.bld.srcnode.find_node(cwd)

	def find_node(self):
		name = self.get_name()
		if not name:
			return None    
		return self.bld.srcnode.find_node(name)

	def make_node(self):
		name = self.get_name()
		if not name:
			return None    
		return self.bld.srcnode.make_node(name)

	def get_name(self): 
		'''abstract operation to be defined in child'''
		return None

	def get_content(self):
		'''abstract operation to be defined in child'''
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
		self.childs = {}

	def get_name(self):
		return 'codeblocks.workspace'

	def get_content(self):
		'''returns the content of a code::blocks workspace file containing references to all 
		projects and project dependencies.
		'''
		root = ElementTree.fromstring(CODEBLOCKS_WORKSPACE)
		workspace = root.find('Workspace')
		workspace.set('title', self.exp.appname)
		for (name, deps) in self.childs.values():
			project = ElementTree.SubElement(workspace, 'Project', attrib={'filename':name})
			for dep in deps:
				(depends, _) = self.childs[dep]
				ElementTree.SubElement(project, 'Depends', attrib={'filename':depends})
		return ElementTree.tostring(root)

	def add_child(self, child):
		(name, project, deps) = child
		self.childs[name] = (project, deps)


class _CBProject(_CodeBlocks):
	'''Class used for exporting *waf* project data to **Code::Blocks** 
	projects.
	'''
	def __init__(self, bld, gen, targets):
		super(_CBProject, self).__init__(bld)
		self.gen = gen
		self.targets = targets

	def get_name(self):
		gen = self.gen
		return '%s/%s.cbp' % (gen.path.relpath().replace('\\', '/'), gen.get_name())

	def get_content(self):
		'''returns the content of a code::blocks project file.'''
		gen = self.gen
		root = ElementTree.fromstring(CODEBLOCKS_PROJECT)
		project = root.find('Project')
		for option in project.iter('Option'):
			if option.get('title'):
				option.set('title', gen.get_name())
				
		target = project.find('Build').find('Target')
		for option in target.iter('Option'):
			if option.get('output'):
				option.set('output', self._get_output())
				
			elif option.get('object_output'):
				option.set('object_output', self._get_object_output())
				
			elif option.get('type'):
				option.set('type', self._get_target_type())
		
		compiler = target.find('Compiler')
		for option in self._get_compiler_options():
			ElementTree.SubElement(compiler, 'Add', attrib={'option':option})
		for define in self._get_compiler_defines():
			ElementTree.SubElement(compiler, 'Add', attrib={'option':'-D%s' % define})
		for include in self._get_compiler_includes():
			ElementTree.SubElement(compiler, 'Add', attrib={'directory':include})

		linker = target.find('Linker')
		for option in self._get_link_options():
			ElementTree.SubElement(linker, 'Add', attrib={'option':option})
		for library in self._get_link_libs():
			ElementTree.SubElement(linker, 'Add', attrib={'library':library})
		for directory in self._get_link_paths():
			ElementTree.SubElement(linker, 'Add', attrib={'directory':directory})
		
		sources = self._get_genlist(self.gen, 'source')
		for source in sources:
			ElementTree.SubElement(project, 'Unit', attrib={'filename':source})
		
		includes = self._get_includes_files()
		for include in includes:
			ElementTree.SubElement(project, 'Unit', attrib={'filename':include})
		
		return ElementTree.tostring(root)

	def get_data(self):
		gen = self.gen
		name = gen.get_name()
		project = self.get_name()
		deps = Utils.to_list(getattr(gen, 'use', []))
		return (name, project, deps)

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
		defines = self._get_genlist(gen, 'defines')
		# TODO: code::blocks version 10.05 needs double backslashes as 
		# escape in string defines
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
            <Target title="Default">
                <Option output="XXX" prefix_auto="1" extension_auto="1" />
                <Option object_output="XXX" />
                <Option type="XXX" />
                <Option compiler="gcc" />
                <Compiler>
                </Compiler>
                <Linker>
                </Linker>
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
