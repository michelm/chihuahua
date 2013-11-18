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
		self.comments = [
			'<?xml version="1.0" encoding="UTF-8" standalone="no"?>',
			'<?fileVersion 4.0.0?>'
		]
		
		natures = [
			'org.eclipse.cdt.core.cnature',
			'org.eclipse.cdt.managedbuilder.core.managedBuildNature',
			'org.eclipse.cdt.managedbuilder.core.ScannerConfigNature',
		]
		self.project.natures.extend(natures)

		buildcommands = [ 
		# name, triggers, arguments
		('org.eclipse.cdt.managedbuilder.core.genmakebuilder', 'clean,full,incremental,', ''),
		('org.eclipse.cdt.managedbuilder.core.ScannerConfigBuilder', 'full,incremental,', '')
		]
		self.project.buildcommands.extend(buildcommands)

		self.uuid = {
			'debug'		: self.get_uuid(),
			'debug_compiler': self.get_uuid(),
			'debug_input'	: self.get_uuid(),
			'release'	: self.get_uuid(),
			'release_compiler': self.get_uuid(),
			'release_input'	: self.get_uuid(),
		}


	def export(self):
		super(CProject, self).export()
		self.project.export()

	def cleanup(self):
		super(CProject, self).cleanup()
		self.project.cleanup()

	def get_fname(self):
		return '%s/.cproject' % (self.gen.path.relpath().replace('\\', '/'))

	def get_content(self):
		root = ElementTree.fromstring(ECLIPSE_CPROJECT)
		for module in root.iter('storageModule'):
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
		attr = {}
		if set(('cprogram', 'cxxprogram')) & set(self.gen.features):
			attr['id'] = '%s.cdt.managedbuild.target.gnu.exe.%s' % (self.gen.get_name(), self.get_uuid())
			attr['name'] = 'Executable'
			attr['projectType'] = 'cdt.managedbuild.target.gnu.exe'
		if set(('cshlib', 'cxxshlib')) & set(self.gen.features):
			attr['id'] = '%s.cdt.managedbuild.target.gnu.so.%s' % (self.gen.get_name(), self.get_uuid())
			attr['name'] = 'Shared Library'
			attr['projectType'] = 'cdt.managedbuild.target.gnu.so'
		if set(('cstlib', 'cxxstlib')) & set(self.gen.features):
			attr['id'] = '%s.cdt.managedbuild.target.gnu.lib.%s' % (self.gen.get_name(), self.get_uuid())
			attr['name'] = 'Static Library'
			attr['projectType'] = 'cdt.managedbuild.target.gnu.lib'
		ElementTree.SubElement(module, 'project', attrib=attr)

	def update_scannerconfiguration(self, module):
		iid = [
			"cdt.managedbuild.config.gnu.exe.debug.%s" % self.uuid['debug'],
			"cdt.managedbuild.config.gnu.exe.debug.%s." % self.uuid['debug'],
			"cdt.managedbuild.tool.gnu.c.compiler.exe.debug.%s" % self.uuid['debug_compiler'],
			"cdt.managedbuild.tool.gnu.c.compiler.input.%s" % self.uuid['debug_input']
		]
		self.add_scanner_config_build_info(module, ';'.join(iid))

		iid = [
			"cdt.managedbuild.config.gnu.exe.release.%s" % self.uuid['release'],
			"cdt.managedbuild.config.gnu.exe.release.%s." % self.uuid['release'],
			"cdt.managedbuild.tool.gnu.c.compiler.exe.release.%s" % self.uuid['release_compiler'],
			"cdt.managedbuild.tool.gnu.c.compiler.input.%s" % self.uuid['release_input']
		]
		self.add_scanner_config_build_info(module, ';'.join(iid))

	def add_scanner_config_build_info(self, module, instance_id):
		attrib = {
			'instanceId':instance_id
		}
		element = ElementTree.SubElement(module, 'scannerConfigBuildInfo', attrib)

		attrib= {
			'enabled':'true', 
			'problemReportingEnabled':'true', 
			'selectedProfileId':''
		}
		ElementTree.SubElement(element, 'autodiscovery', attrib)

	def update_refreshscope(self, module):
		for resource in module.iter('resource'):
			resource.set('workspacePath', '/%s' % self.gen.get_name())


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


ECLIPSE_CPROJECT = \
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




