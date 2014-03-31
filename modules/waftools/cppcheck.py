#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com


'''
Summary
-------
Provides a *waf* wrapper (i.e. waftool) around the static C/C++ source code
checking tool **cppcheck**.

See http://cppcheck.sourceforge.net/ for more information on **cppcheck** 
itself; how you can obtain and install it for your particular desktop 
environment. Note that many linux distributions already provide a ready to 
install version of **cppcheck**. On *Fedora*, for instance, it can be installed
using *yum*::

	$ sudo yum install cppcheck


Description
-----------
Each time a C/C++ task generator within your *waf* build environment is being 
build or rebuild, its source code can be checked using cppcheck. This module 
will gather and extract all the required information from the C/C++ task
generator (e.g. *bld.program* defined somewhere in a *wscript* file) and will 
use it to perform a source code analysis using cppcheck on command line. The 
command line results from **cppcheck** (in XML format) will be used as input in 
order to create a highlighted and colorful HTML report pinpointing all
(possible) problems. 
For each single C/C++ task defined within your *waf* build environment such a 
separate HTML report will be created. Furthermore a single HTML index page will
be created containing references to all individual HTML reports of components. 
All these reports will be stored in the sub directory *reports/cppcheck* in the
top level directory of your build environment. When needed this location can
also be changed to, see command line options.

Example below present an example of the reports generated in a build environment
in which three *C* components have been defined::

	.
	├── components
	│   ├── chello
	│   │   ├── include
	│   │   │   └── hello.h
	│   │   ├── src
	│   │   │   └── hello.c
	│   │   └── wscript
	│   ├── ciambad
	│   │   ├── cppcheck.suppress
	│   │   ├── include
	│   │   ├── src
	│   │   │   └── iambad.c
	│   │   └── wscript
	│   └── cleaking
	│       ├── include
	│       │   └── leaking.h
	│       ├── src
	│       │   └── leaking.c
	│       └── wscript
	├── reports
	│   └── cppcheck
	│       ├── components
	│       │   ├── chello
	│       │   │   ├── chello
	│       │   │   │   ├── index.html
	│       │   │   │   └── style.css
	│       │   │   └── chello.xml
	│       │   ├── ciambad
	│       │   │   ├── ciambad
	│       │   │   │   ├── 0.html
	│       │   │   │   ├── index.html
	│       │   │   │   └── style.css
	│       │   │   └── ciambad.xml
	│       │   └── cleaking
	│       │       ├── cleaking
	│       │       │   ├── 0.html
	│       │       │   ├── index.html
	│       │       │   └── style.css
	│       │       └── cleaking.xml
	│       ├── index.html
	│       └── style.css
	└── wscript

Note that each report for a task generator from the components directory 
contains an extra indent in the reports directory; cppchecks reports are stored
in a sub directory using the name of the unique task generator as name for that
sub directory. This allows for the creation of multiple reports at the same
location in case a single *wscript* file contains multiple task generators in
the components directory.  

Under normal conditions no additional parameters or definitions are needed in
the definition of a C/C++ task generator itself; simply defining it as 
*program*, *stlib* or *shlib* and adding this module to the top level *wscript*
of your *waf* build environment will suffice. However in some cases 
**cppcheck** might detect problems that are either not true, or you just want
to suppress them. In these cases you can either use global suppression options
(using command line options) but you can also add special rules to the 
definition of the C/C++ task generators in question (more on this the next 
section Usage).


Usage
-----
In order to use this waftool simply add it to the 'options' and 'configure' 
functions of your main *waf* script as shown in the example below::

	def options(opt):
		opt.load('cppcheck', tooldir='./waftools')

	def configure(conf):
		conf.load('cppcheck')
		
Note that example shown above assumes that the **cppcheck** waftool is located 
in the sub directory named 'waftools'.

When configured as shown in the example above, **cppcheck** will perform a 
source code analysis on all C/C++ tasks that have been defined in your *waf* 
build environment when using the '--cppcheck' build option::

	waf build --cppcheck

The example shown below for a C program will be used as input for **cppcheck** 
when building the task::

	def build(bld):
		bld.program(name='foo', src='foobar.c')

The result of the source code analysis will be stored both as XML and HTML 
files in the build location for the task. Should any error be detected by
**cppcheck**, then the build process will be aborted and a link to the HTML 
report will be presented. When desired you also choose to resume with checking
other components after a fatal error has been detected using the following command
line option::

	$ waf build --cppcheck --cppcheck-err-resume 

When needed source code checking by **cppcheck** can be disabled per task or even 
for each specific error and/or warning within a particular task.

In order to exclude a task from source code checking add the skip option to the
task as shown below::

	def build(bld):
		bld.program(name='foo',	src='foobar.c',	cppcheck_skip=True)

When needed problems detected by cppcheck may be suppressed using a file 
containing a list of suppression rules. The relative or absolute path to this 
file can be added to the build task as shown in the example below::

	bld.program(name='bar', src='foobar.c', cppcheck_suppress='bar.suppress')

A **cppcheck** suppress file should contain one suppress rule per line. Each of 
these rules will be passed as an '--suppress=<rule>' argument to **cppcheck**.

'''

import os
import sys
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
import pygments
from pygments import formatters, lexers
from waflib import TaskGen, Context, Logs


def options(opt):
	'''Adds command line options to the *waf* build environment 

	:param opt: Options context from the *waf* build environment.
	:type opt: waflib.Options.OptionsContext
	'''
	opt.add_option('--cppcheck', dest='cppcheck', default=False,
		action='store_true', help='check C/C++ sources (default=False)')

	opt.add_option('--cppcheck-path', dest='cppcheck_path', default='reports/cppcheck',
		action='store', help='location to save cppcheck reports to.')
	
	opt.add_option('--cppcheck-fatals', dest='cppcheck_fatals', default='error',
		action='store', help='comma separated list of fatal severities')
	
	opt.add_option('--cppcheck-err-resume', dest='cppcheck_err_resume',
		default=False, action='store_true',
		help='continue in case of errors (default=False)')

	opt.add_option('--cppcheck-bin-enable', dest='cppcheck_bin_enable',
		default='warning,performance,portability,style,unusedFunction',
		action='store',
		help="cppcheck option '--enable=' for binaries (default=warning,performance,portability,style,unusedFunction)")

	opt.add_option('--cppcheck-lib-enable', dest='cppcheck_lib_enable',
		default='warning,performance,portability,style', action='store',
		help="cppcheck option '--enable=' for libraries (default=warning,performance,portability,style)")

	opt.add_option('--cppcheck-std-c', dest='cppcheck_std_c',
		default='c99', action='store',
		help='cppcheck standard to use when checking C (default=c99)')

	opt.add_option('--cppcheck-std-cxx', dest='cppcheck_std_cxx',
		default='c++03', action='store',
		help='cppcheck standard to use when checking C++ (default=c++03)')

	opt.add_option('--cppcheck-check-config', dest='cppcheck_check_config',
		default=False, action='store_true',
		help='forced check for missing buildin include files, e.g. stdio.h (default=False)')

	opt.add_option('--cppcheck-max-configs', dest='cppcheck_max_configs',
		default='10', action='store',
		help='maximum preprocessor (--max-configs) define iterations (default=20)')


def configure(conf):
	'''Method that will be invoked by *waf* when configuring the build 
	environment.
	
	:param conf: Configuration context from the *waf* build environment.
	:type conf: waflib.Configure.ConfigurationContext
	'''
	if conf.options.cppcheck:
		conf.env.CPPCHECK_EXECUTE = [1]
	conf.env.CPPCHECK_PATH = conf.options.cppcheck_path
	conf.env.CPPCHECK_FATALS = conf.options.cppcheck_fatals.split(',')	
	conf.env.CPPCHECK_STD_C = conf.options.cppcheck_std_c
	conf.env.CPPCHECK_STD_CXX = conf.options.cppcheck_std_cxx
	conf.env.CPPCHECK_MAX_CONFIGS = conf.options.cppcheck_max_configs
	conf.env.CPPCHECK_BIN_ENABLE = conf.options.cppcheck_bin_enable
	conf.env.CPPCHECK_LIB_ENABLE = conf.options.cppcheck_lib_enable
	conf.find_program('cppcheck', var='CPPCHECK')


@TaskGen.feature('c')
@TaskGen.feature('cxx')
def cppcheck_execute(self):
	'''Method that will be invoked by *waf* for each task generator for the 
	C/C++ language.
	
	:param self: A task generator that contains all information of the C/C++
				 program, shared- or static library to be exported.
	:type self: waflib.Task.TaskGen
	'''
	bld = self.bld
	check = bld.env.CPPCHECK_EXECUTE
	
	# check if this task generator should be checked
	if not bool(check) and not bld.options.cppcheck:
		return
	if getattr(self, 'cppcheck_skip', False):
		return

	if not hasattr(bld, 'cppcheck_catalog'):
		bld.cppcheck_catalog = []
		bld.add_post_fun(cppcheck_postfun)

	fatals = bld.env.CPPCHECK_FATALS
	if bld.options.cppcheck_err_resume:
		fatals = []

	cppcheck = CppcheckGen(self, bld.env.CPPCHECK_PATH, fatals)
	cppcheck.execute()
	
	index = cppcheck.get_html_index()
	severities = cppcheck.severities

	catalog = bld.cppcheck_catalog
	catalog.append( (self.get_name(), index, severities) )


def cppcheck_postfun(bld):
	'''Method that will be invoked by the *waf* build environment once the 
	build has been completed.
	
	It will use the result of the source code checking stored within the given
	build context and use it to create a global HTML index. This global index
	page contains a reference to all reports on C/C++ components that have been
	checked.
	
	:param bld: Build context from the *waf* build environment.
	:type bld: waflib.Build.BuildContext		
	'''
	catalog = bld.cppcheck_catalog
	if not len(catalog):
		bld.fatal('CPPCHECK EMPTY CATALOG')
		return
		
	cppcheck = Cppcheck(bld, bld.env.CPPCHECK_PATH)
	cppcheck.create_html_index(catalog)
	
	index = cppcheck.get_html_index()
	
	msg =  "\nccpcheck completed, report can be found at:"
	msg += "\n    file://%s" % (index)
	msg += "\n"
	Logs.warn(msg)


class CppcheckDefect(object):
	'''Temporary placeholder for passing reported defects per component within 
	this module.

	At run time the following attributes will be added::
	
		defect.id
		defect.severity
		defect.msg
		defect.verbose
		defect.file
		defect.line
	'''


class Cppcheck(object):
	'''Base class creating a **cppcheck** source code HTML report.
	
	:param bld: a *waf* build instance from the top level *wscript*.
	:type bld: waflib.BuildContext
	
	:param root: location (path) where the report should be stored 
	:type root: str
	'''
	def __init__(self, bld, root):
		self.bld = bld
		self.root = root

	def get_html_index(self):
		'''Returns the absolute path name to the index file.
		'''
		name = '%s/%s/index.html' % (self.bld.path.abspath(), self.root)
		return name.replace('\\', '/')

	def create_html_index(self, catalog):
		'''Creates the HTML report.
		
		:param catalog: List of tuples, one for each checked C/C++ component.
						Each tuple in this list contains the name, path to HTML
						index file and a list of detected severity levels.
		:type catalog:  list
		'''
		# save the CSS file for the top page of problem report
		self._create_css_file('style.css')

		try:
			name = getattr(Context.g_module, Context.APPNAME)
		except AttributeError:
			name = os.path.basename(self.bld.path.abspath())

		try:
			version = getattr(Context.g_module, Context.VERSION)
		except AttributeError:
			version = ""

		root = ElementTree.fromstring(CPPCHECK_HTML_FILE)
		title = root.find('head/title')
		title.text = 'cppcheck - %s' % (name)

		body = root.find('body')
		for div in body.findall('div'):
			if div.get('id') == 'page':
				page = div
				break
		for div in page.findall('div'):
			if div.get('id') == 'header':
				h1 = div.find('h1')
				h1.text = 'cppcheck report - %s %s' % (name, version)
			if div.get('id') == 'content':
				content = div
				self._create_index_table(content, catalog)

		content = ElementTree.tostring(root, method='html')
		content = self._html_clean(content)
		return self._save_file('index.html', content)

	def _save_file(self, name, content):
		name = '%s/%s' % (self.root, name)
				
		path = os.path.dirname(name)
		if not os.path.exists(path):
			os.makedirs(path)

		node = self.bld.path.make_node(name)
		node.write(content)
		return node

	def _html_clean(self, content):
		h = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
		if sys.version_info[0] == 2:
			lines = [l for l in content.splitlines()]
		else:
			lines = [l.decode('utf-8') for l in content.splitlines()]
		lines.insert(0, h)
		return '\n'.join([l for l in lines if len(l.strip())])
	
	def _create_css_file(self, name):
		css = str(CPPCHECK_CSS_FILE)
		if hasattr(self, 'css_style_defs'):
			css += "\n%s\n" % (self.css_style_defs)
		self._save_file(name, css)

	def _create_index_table(self, content, catalog):
		table = ElementTree.fromstring(CPPCHECK_HTML_INDEX_TABLE)
		for (name, index, severities) in catalog:
			if os.path.exists(index):
				tr = ElementTree.SubElement(table, 'tr')
				td = ElementTree.SubElement(tr, 'td')
				a = ElementTree.SubElement(td, 'a')
				a.text = str(name)
				a.set('href', index.replace('\\', '/'))
				td = ElementTree.SubElement(tr, 'td')
				td.text = ','.join(set(severities))
				if 'error' in severities:
					td.set('class', 'error')
		content.append(table)


class CppcheckGen(Cppcheck):
	'''Class used for creating colorfull HTML reports based on the source code 
	check results from **cppcheck**.
	
	:param taskgen: Contains all input information for the C/C++ component
	:type taskgen: waflib.Task.TaskGen
	:param root: path where the HTML report will be stored
	:type root: str
	:param fatals: List of severities that should be treated as fatal when encountered
	:type fatals: list
	'''	
	def __init__(self, taskgen, root, fatals):
		super(CppcheckGen, self).__init__(taskgen.bld, root)
		self.taskgen = taskgen
		self.severities = []
		self.fatals = fatals

	def execute(self):
		'''Excutes source code checking using cppcheck on the C/C++
		component.
		
		The XML results from cppcheck will converted and used to create
		HTML reports.
		
		Returns a list of detected severities for this component.
		'''
		bld = self.taskgen.bld
		cmd = self._get_command()
		stderr = bld.cmd_and_log(cmd, quiet=Context.BOTH, output=Context.STDERR)
		
		# save the result from command line to a XML report
		self._save_xml_report(stderr, cmd)

		# process and convert the results from command line
		defects = self._get_defects(stderr)
		
		# create a HTML report using the converted defects
		index = self._create_html_report(defects)
		
		# report defects to standard output including a link to the report
		self._print_defects(defects, index)
		
		# create and return a list of severities
		self.severities = [defect.severity for defect in defects]
		return self.severities
		
	def get_html_index(self):
		'''Returns the absolute path name to the index file.'''
		bld = self.bld
		gen = self.taskgen 
		name = '%s/%s/%s/%s/index.html' % (bld.path.abspath(), self.root, gen.path.relpath(), gen.get_name())
		return name.replace('\\', '/')

	def create_html_index(self, files):
		'''Creates the HTML report for a C/C++ component.
		
		:param files: 	Contains location to HTML files and error for each 
						source file that is part of the component
		:type files: 	dict
		'''
		bld = self.bld
		gen = self.taskgen
		name = gen.get_name()

		# create the path to the top level HTML index page of the report
		home = '%s/%s/index.html' % (bld.path.abspath(), self.root)
		root = ElementTree.fromstring(CPPCHECK_HTML_FILE)
		title = root.find('head/title')
		title.text = 'cppcheck - report - %s' % (name)

		body = root.find('body')
		for div in body.findall('div'):
			if div.get('id') == 'page':
				page = div
				break
		for div in page.findall('div'):
			if div.get('id') == 'header':
				h1 = div.find('h1')
				h1.text = 'cppcheck report - %s' % (name)
			if div.get('id') == 'menu':
				a = div.find('a')
				a.set('href', home.replace('\\', '/'))
			if div.get('id') == 'content':
				content = div
				self._create_html_table(content, files)

		name = '%s/%s/index.html' % (gen.path.relpath(), gen.get_name())
		content = ElementTree.tostring(root, method='html')
		content = self._html_clean(content)
		return self._save_file(name, content)

	def _get_command(self):
		'''returns the CPPCHECK command to be executed'''
		bld = self.bld
		gen = self.taskgen
		env = self.taskgen.env
		
		features = getattr(gen, 'features', [])
		std_c = env.CPPCHECK_STD_C
		std_cxx = env.CPPCHECK_STD_CXX
		max_configs = env.CPPCHECK_MAX_CONFIGS
		bin_enable = env.CPPCHECK_BIN_ENABLE
		lib_enable = env.CPPCHECK_LIB_ENABLE

		cmd  = ['%s' % env.CPPCHECK, '-v', '--xml', '--xml-version=2']
		cmd.append('--inconclusive')
		cmd.append('--report-progress')
		cmd.append('--max-configs=%s' % max_configs)

		if 'cxx' in features:
			cmd.append('--language=c++')
			cmd.append('--std=%s' % std_cxx)
		else:
			cmd.append('--language=c')
			cmd.append('--std=%s' % std_c)

		if bld.options.cppcheck_check_config:
			cmd.append('--check-config')

		if set(['cprogram','cxxprogram']) & set(features):
			cmd.append('--enable=%s' % bin_enable)
		else:
			cmd.append('--enable=%s' % lib_enable)

		for src in gen.to_list(gen.source):
			cmd.append('%r' % src)
		for inc in gen.to_incnodes(gen.to_list(getattr(gen, 'includes', []))):
			cmd.append('-I%r' % inc)
		for inc in gen.to_incnodes(gen.to_list(gen.env.INCLUDES)):
			cmd.append('-I%r' % inc)
		return cmd

	def _save_xml_report(self, stderr, cmd):
		# create a XML tree from the command result 
		root = ElementTree.fromstring(stderr)
		element = ElementTree.SubElement(root.find('cppcheck'), 'cmd')
		element.text = str(' '.join(cmd))

		# clean up the indentation of the XML tree
		s = ElementTree.tostring(root)
		s = minidom.parseString(s).toprettyxml(indent="\t", encoding="utf-8")

		lines = [str(l) for l in s.splitlines()]
		content = '\n'.join([l for l in lines if len(l.strip())])

		gen = self.taskgen
		name = '%s/%s.xml' % (gen.path.relpath(), gen.get_name())
		self._save_file(name, content)

	def _get_defects(self, stderr):
		defects = []
		for error in ElementTree.fromstring(stderr).iter('error'):
			defect = CppcheckDefect()
			defect.id = error.get('id')
			defect.severity = error.get('severity')
			defect.msg = str(error.get('msg')).replace('<','&lt;')
			defect.verbose = error.get('verbose')
			
			for location in error.findall('location'):
				defect.file = location.get('file')
				defect.line = str(int(location.get('line')))
			defects.append(defect)
		return defects

	def _create_html_report(self, defects):
		# create a HTML for each source file
		files = self._create_html_files(defects)
		
		# create a HTML top page for this task generator
		index = self.create_html_index(files)

		# create a CSS file used by the HTML files of this task generator
		gen = self.taskgen
		name = '%s/%s/style.css' % (gen.path.relpath(), gen.get_name())
		self._create_css_file(name)
		return index

	def _print_defects(self, defects, index):
		bld = self.bld
		gen = self.taskgen
		
		name = gen.get_name()
		fatal = self.fatals
		severity = [d.severity for d in defects]
		problems = [d for d in defects if d.severity != 'information']

		if set(fatal) & set(severity):
			exc  = "\n"
			exc += "\nccpcheck detected fatal error(s) in task '%s', see report for details:" % (name)
			exc += "\n    file://%r" % (index)
			exc += "\n"
			bld.fatal(exc)

		elif len(problems):
			msg =  "\nccpcheck detected (possible) problem(s) in task '%s', see report for details:" % (name)
			msg += "\n    file://%r" % (index)
			msg += "\n"
			Logs.error(msg)

	def _create_html_files(self, defects):
		# group the defects per source file
		sources = {}
		defects = [d for d in defects if getattr(d, 'file', None)]
		for defect in defects:
			name = defect.file
			if not name in sources:
				sources[name] = [defect]
			else:
				sources[name].append(defect)

		gen = self.taskgen
		files = {}
		names = list(sources.copy().keys())

		for i in range(0,len(names)):
			name = names[i]
			html = '%s/%s/%i.html' % (gen.path.relpath(), gen.get_name(), i)
			errs = sources[name]

			# create a HTML report for each source file
			self.css_style_defs = self._create_html_file(html, name, errs)

			# add location of HTML report including errors to files dictionary
			# this dictionary will be used on the HTML index to list all
			# source files
			files[name] = { 'htmlfile': '%s/%s' % (self.root, html), 'errors': errs }
			
		return files

	def _create_html_file(self, fname, source, errors):
		bld = self.bld
		name = self.taskgen.get_name()
		
		# create the path to the top level HTML index page of the report
		home = '%s/%s/index.html' % (bld.path.abspath() ,self.root)
		home = home.replace('\\', '/')
		
		root = ElementTree.fromstring(CPPCHECK_HTML_FILE)
		title = root.find('head/title')
		title.text = 'cppcheck - report - %s' % (name)

		body = root.find('body')
		for div in body.findall('div'):
			if div.get('id') == 'page':
				page = div
				break
		for div in page.findall('div'):
			if div.get('id') == 'header':
				h1 = div.find('h1')
				h1.text = 'cppcheck report - %s' % (name)
				
			if div.get('id') == 'menu':
				a = div.find('a')
				a.set('href', home.replace('\\', '/'))
				a = ElementTree.SubElement(div, 'a')
				a.text = 'Defect list'
				a.set('href', 'index.html')
				
			if div.get('id') == 'content':
				content = div
				srcnode = bld.root.find_node(source)
				hl_lines = [e.line for e in errors if getattr(e, 'line')]
				formatter = CppcheckHtmlFormatter(linenos=True, style='colorful', hl_lines=hl_lines, lineanchors='line')
				formatter.errors = [e for e in errors if getattr(e, 'line')]
				css_style_defs = formatter.get_style_defs('.highlight')
				
				# TODO: TEMP fix for pygments when using python3
				# only support C/C++ highlighting
				if sys.version_info[0] > 2:
					from pygments.lexers import CLexer
					lexer = CLexer()
				else:
					lexer = pygments.lexers.guess_lexer_for_filename(source, "")
				
				s = pygments.highlight(srcnode.read(), lexer, formatter)
				table = ElementTree.fromstring(s)
				content.append(table)

		content = ElementTree.tostring(root, method='html')
		content = self._html_clean(content)
		self._save_file(fname, content)
		return css_style_defs

	def _create_html_table(self, content, files):
		bld = self.bld
		table = ElementTree.fromstring(CPPCHECK_HTML_TABLE)
		
		for name, val in files.items():
			f = '%s/%s' % (bld.path.abspath(), val['htmlfile'])
			f = f.replace('\\', '/')
			s = '<tr><td colspan="4"><a href="%s">%s</a></td></tr>\n' % (f, name)
			s = minidom.parseString(s).toprettyxml(indent="\t")
			row = ElementTree.fromstring(s)
			table.append(row)

			errors = sorted(val['errors'], key=lambda e: int(e.line) if getattr(e, 'line') else sys.maxint)
			for e in errors:
				if not getattr(e, 'line'):
					s = '<tr><td></td><td>%s</td><td>%s</td><td>%s</td></tr>\n' % (e.id, e.severity, e.msg)
				else:
					attr = ''
					if e.severity == 'error':
						attr = 'class="error"'
					s = '<tr><td><a href="%s#line-%s">%s</a></td>' % (f, e.line, e.line)
					s+= '<td>%s</td><td>%s</td><td %s>%s</td></tr>\n' % (e.id, e.severity, attr, e.msg)
				s = minidom.parseString(s).toprettyxml(indent="\t")
				row = ElementTree.fromstring(s)
				table.append(row)
		content.append(table)


class CppcheckHtmlFormatter(pygments.formatters.HtmlFormatter):
	'''Formatter used for adding error messages to HTML report containing
	syntax highlighted source code.
	'''
	errors = []
	'''List of error messages. Contains the error message and line number.'''
	
	_fmt = '<span style="background: #ffaaaa;padding: 3px;">&lt;--- %s</span>\n'

	def wrap(self, source, outfile):
		'''Adds the error messages to the highlighted source code at the correct
		location.
		'''
		line_no = 1
		for i, t in super(CppcheckHtmlFormatter, self).wrap(source, outfile):
			# If this is a source code line we want to add a span tag at the end.
			if i == 1:
				for error in self.errors:
					if int(error.line) == line_no:
						t = t.replace('\n', self._fmt % error.msg)
				line_no = line_no + 1
			yield i, t


CPPCHECK_HTML_FILE = \
"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd" [<!ENTITY nbsp "&#160;">]>
<html>
    <head>
        <title>cppcheck - report - XXX</title>
        <link href="style.css" rel="stylesheet" type="text/css" />
        <style type="text/css" />
    </head>
    <body class="body">
        <div id="page-header">&nbsp;</div>
        <div id="page">
            <div id="header">
                <h1>cppcheck report - XXX</h1>
            </div>
            <div id="menu">
                <a href="index.html">Home</a>
            </div>
            <div id="content">
            </div>
            <div id="footer">
                <div>cppcheck - a tool for static C/C++ code analysis</div>
                <div>
                Internet: <a href="http://cppcheck.sourceforge.net">http://cppcheck.sourceforge.net</a><br/>
                Forum: <a href="http://apps.sourceforge.net/phpbb/cppcheck/">http://apps.sourceforge.net/phpbb/cppcheck/</a><br/>
                IRC: #cppcheck at irc.freenode.net
                </div>
                &nbsp;
            </div>
            &nbsp;
        </div>
        <div id="page-footer">&nbsp;</div>
    </body>
</html>
"""


CPPCHECK_HTML_TABLE = \
"""<table>
    <tr>
        <th>Line</th>
        <th>Id</th>
        <th>Severity</th>
        <th>Message</th>
    </tr>
</table>
"""


CPPCHECK_HTML_INDEX_TABLE = \
"""<table>
    <tr>
        <th>Component</th>
        <th>Severity</th>
    </tr>
</table>
"""


CPPCHECK_CSS_FILE = """
body.body {
    font-family: Arial;
    font-size: 13px;
    background-color: black;
    padding: 0px;
    margin: 0px;
}

.error {
    font-family: Arial;
    font-size: 13px;
    background-color: #ffb7b7;
    padding: 0px;
    margin: 0px;
}

th, td {
    min-width: 100px;
    text-align: left;
}

#page-header {
    clear: both;
    width: 1200px;
    margin: 20px auto 0px auto;
    height: 10px;
    border-bottom-width: 2px;
    border-bottom-style: solid;
    border-bottom-color: #aaaaaa;
}

#page {
    width: 1160px;
    margin: auto;
    border-left-width: 2px;
    border-left-style: solid;
    border-left-color: #aaaaaa;
    border-right-width: 2px;
    border-right-style: solid;
    border-right-color: #aaaaaa;
    background-color: White;
    padding: 20px;
}

#page-footer {
    clear: both;
    width: 1200px;
    margin: auto;
    height: 10px;
    border-top-width: 2px;
    border-top-style: solid;
    border-top-color: #aaaaaa;
}

#header {
    width: 100%;
    height: 70px;
    background-image: url(logo.png);
    background-repeat: no-repeat;
    background-position: left top;
    border-bottom-style: solid;
    border-bottom-width: thin;
    border-bottom-color: #aaaaaa;
}

#menu {
    margin-top: 5px;
    text-align: left;
    float: left;
    width: 100px;
    height: 300px;
}

#menu > a {
    margin-left: 10px;
    display: block;
}

#content {
    float: left;
    width: 1020px;
    margin: 5px;
    padding: 0px 10px 10px 10px;
    border-left-style: solid;
    border-left-width: thin;
    border-left-color: #aaaaaa;
}

#footer {
    padding-bottom: 5px;
    padding-top: 5px;
    border-top-style: solid;
    border-top-width: thin;
    border-top-color: #aaaaaa;
    clear: both;
    font-size: 10px;
}

#footer > div {
    float: left;
    width: 33%;
}

"""


