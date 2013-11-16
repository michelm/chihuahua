#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

import os
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
import waflib
from waflib import Utils, Node


def export(bld):
	root = WafProject(bld)
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			child = CProject(bld, gen, targets)
			child.export()
	root.export()


def cleanup(bld):
	root = WafProject(bld)
	for gen, targets in bld.components.items():
		if set(('c', 'cxx')) & set(getattr(gen, 'features', [])):
			child = CProject(bld, gen, targets)
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
		self.comments = [
			'<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
			'<?eclipse-pydev version="1.0"?>'
		]

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
		

class CProject(Project):
	def __init__(self, bld, gen, targets):
		super(CProject, self).__init__(bld, gen)
		self.targets = targets
		self.project = Project(bld, gen)
		
		natures = [
			'org.eclipse.cdt.core.cnature',
			'org.eclipse.cdt.managedbuilder.core.managedBuildNature',
			'org.eclipse.cdt.managedbuilder.core.ScannerConfigNature'
		]
		self.project.natures.extend(natures)

		buildcommands = [
		(	'org.eclipse.cdt.managedbuilder.core.genmakebuilder',
			'clean,full,incremental,',
			''
		),
		(	'org.eclipse.cdt.managedbuilder.core.ScannerConfigBuilder',
			'full,incremental,',
			''
		)]
		self.project.buildcommands.extend(buildcommands)

	def export(self):
		super(CProject, self).export()
		self.project.export()

	def cleanup(self):
		super(CProject, self).cleanup()
		self.project.cleanup()

	def get_fname(self):
		return '%s/.cproject' % (self.gen.path.relpath().replace('\\', '/'))

	def get_content(self):
		root = ElementTree.fromstring(ECLIPSE_PROJECT)
		return ElementTree.tostring(root)


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



