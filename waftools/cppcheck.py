#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

import os
import sys
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
import pygments
from pygments import formatters, lexers
from waflib import TaskGen, Context, Logs

CPPCHECK_PATH = 'reports/cppcheck'
CPPCHECK_FATALS = ['error']

def options(opt):
	opt.add_option('--cppcheck', dest='cppcheck', default=False,
		action='store_true', help='check C/C++ sources (default=False)')

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
	if conf.options.cppcheck:
		conf.env.CPPCHECK_EXECUTE = [1]
		
	conf.env.CPPCHECK_STD_C = conf.options.cppcheck_std_c
	conf.env.CPPCHECK_STD_CXX = conf.options.cppcheck_std_cxx
	conf.env.CPPCHECK_MAX_CONFIGS = conf.options.cppcheck_max_configs
	conf.env.CPPCHECK_BIN_ENABLE = conf.options.cppcheck_bin_enable
	conf.env.CPPCHECK_LIB_ENABLE = conf.options.cppcheck_lib_enable
	conf.find_program('cppcheck', var='CPPCHECK')


@TaskGen.feature('c')
@TaskGen.feature('cxx')
def cppcheck_execute(self):
	bld = self.bld
	check = bld.env.CPPCHECK_EXECUTE
	
	# check if this task generator should checked
	if not bool(check) and not bld.options.cppcheck:
		return
	if getattr(self, 'cppcheck_skip', False):
		return

	if not hasattr(bld, 'cppcheck_catalog'):
		bld.cppcheck_catalog = []
		bld.add_post_fun(cppcheck_postfun)

	fatals = CPPCHECK_FATALS
	if bld.options.cppcheck_err_resume:
		fatals = []

	cppcheck = CppcheckGen(self, CPPCHECK_PATH, fatals)
	cppcheck.execute()
	
	index = cppcheck.get_html_index()
	severities = cppcheck.severities

	catalog = bld.cppcheck_catalog
	catalog.append( (self.get_name(), index, severities) )


def cppcheck_postfun(bld):
	catalog = bld.cppcheck_catalog
	if not len(catalog):
		bld.fatal('CPPCHECK EMPTY CATALOG')
		return
		
	cppcheck = Cppcheck(bld, CPPCHECK_PATH)
	cppcheck.create_html_index(catalog)
	
	index = cppcheck.get_html_index()
	
	msg =  "\nccpcheck completed, report can be found at:"
	msg += "\n    file://%s" % (index)
	msg += "\n"
	Logs.warn(msg)


class CppcheckDefect(object):
	pass


class Cppcheck(object):
	def __init__(self, bld, root):
		self.bld = bld
		self.root = root

	def get_html_index(self):
		name = '%s/%s/index.html' % (self.bld.path.abspath(), self.root)
		return name.replace('\\', '/')

	def save_file(self, name, content):
		name = '%s/%s' % (self.root, name)
				
		path = os.path.dirname(name)
		if not os.path.exists(path):
			os.makedirs(path)

		node = self.bld.path.make_node(name)
		node.write(content)
		return node

	def html_clean(self, content):
		h = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
		lines = [l for l in content.splitlines() if len(l.strip())]
		lines.insert(0, h)
		return '\n'.join(lines)
	
	def create_css_file(self, name):
		css = str(CPPCHECK_CSS_FILE)
		if hasattr(self, 'css_style_defs'):
			css += "\n%s\n" % (self.css_style_defs)
		self.save_file(name, css)

	def create_html_index(self, catalog):
		# save the CSS file for the top page of problem report
		self.create_css_file('style.css')

		name = getattr(Context.g_module, Context.APPNAME)
		version = getattr(Context.g_module, Context.VERSION)

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
				self.create_index_table(content, catalog)

		content = ElementTree.tostring(root, method='html')
		content = self.html_clean(content)
		return self.save_file('index.html', content)

	def create_index_table(self, content, catalog):
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
	def __init__(self, taskgen, root, fatals):
		super(CppcheckGen, self).__init__(taskgen.bld, root)
		self.taskgen = taskgen
		self.severities = []
		self.fatals = fatals

	def execute(self):
		bld = self.taskgen.bld
		cmd = self.get_command()
		stderr = bld.cmd_and_log(cmd, quiet=Context.BOTH, output=Context.STDERR)
		
		# save the result from command line to a XML report
		self.save_xml_report(stderr, cmd)

		# process and convert the results from command line
		defects = self.get_defects(stderr)
		
		# create a HTML report using the converted defects
		index = self.create_html_report(defects)
		
		# report defects to standard output including a link to the report
		self.print_defects(defects, index)
		
		# create and return a list of severities
		self.severities = [defect.severity for defect in defects]
		return self.severities
		
	def get_command(self):
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

	def save_xml_report(self, stderr, cmd):
		# create a XML tree from the command result 
		root = ElementTree.fromstring(stderr)
		element = ElementTree.SubElement(root.find('cppcheck'), 'cmd')
		element.text = str(' '.join(cmd))

		# clean up the indentation of the XML tree
		s = ElementTree.tostring(root)
		s = minidom.parseString(s).toprettyxml(indent="\t", encoding="utf-8")
		content = '\n'.join([l for l in s.splitlines() if len(l.strip())])

		gen = self.taskgen
		name = '%s/%s.xml' % (gen.path.relpath(), gen.get_name())
		self.save_file(name, content)

	def get_html_index(self):
		bld = self.bld
		gen = self.taskgen 
		name = '%s/%s/%s/%s/index.html' % (bld.path.abspath(), self.root, gen.path.relpath(), gen.get_name())
		return name.replace('\\', '/')

	def get_defects(self, stderr):
		defects = []
		for error in ElementTree.fromstring(stderr).iter('error'):
			defect = CppcheckDefect()
			defect.id = error.get('id')
			defect.severity = error.get('severity')
			defect.msg = str(error.get('msg')).replace('<','&lt;')
			defect.verbose = error.get('verbose')
			
			for location in error.findall('location'):
				defect.file = location.get('file')
				defect.line = str(int(location.get('line')) - 1)
			defects.append(defect)
		return defects

	def create_html_report(self, defects):
		# create a HTML for each source file
		files = self.create_html_files(defects)
		
		# create a HTML top page for this task generator
		index = self.create_html_index(files)

		# create a CSS file used by the HTML files of this task generator
		gen = self.taskgen
		name = '%s/%s/style.css' % (gen.path.relpath(), gen.get_name())
		self.create_css_file(name)
		return index

	def print_defects(self, defects, index):
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

	def create_html_files(self, defects):
		# group the defects per source file
		sources = {}
		defects = [d for d in defects if getattr(d, 'file', None)]
		for defect in defects:
			name = defect.file
			if not sources.has_key(name):
				sources[name] = [defect]
			else:
				sources[name].append(defect)

		gen = self.taskgen
		files = {}
		names = sources.keys()

		for i in range(0,len(names)):
			name = names[i]
			html = '%s/%s/%i.html' % (gen.path.relpath(), gen.get_name(), i)
			errs = sources[name]

			# create a HTML report for each source file
			self.css_style_defs = self.create_html_file(html, name, errs)

			# add location of HTML report including errors to files dictionary
			# this dictionary will be used on the HTML index to list all
			# source files
			files[name] = { 'htmlfile': '%s/%s' % (self.root, html), 'errors': errs }
			
		return files

	def create_html_file(self, fname, source, errors):
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
				lexer = pygments.lexers.guess_lexer_for_filename(source, "")
				s = pygments.highlight(srcnode.read(), lexer, formatter)
				table = ElementTree.fromstring(s)
				content.append(table)

		content = ElementTree.tostring(root, method='html')
		content = self.html_clean(content)
		self.save_file(fname, content)
		return css_style_defs

	def create_html_index(self, files):
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
				self.create_html_table(content, files)

		name = '%s/%s/index.html' % (gen.path.relpath(), gen.get_name())
		content = ElementTree.tostring(root, method='html')
		content = self.html_clean(content)
		return self.save_file(name, content)

	def create_html_table(self, content, files):
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
	errors = []
	fmt = '<span style="background: #ffaaaa;padding: 3px;">&lt;--- %s</span>\n'

	def wrap(self, source, outfile):
		line_no = 1
		for i, t in super(CppcheckHtmlFormatter, self).wrap(source, outfile):
			# If this is a source code line we want to add a span tag at the end.
			if i == 1:
				for error in self.errors:
					if int(error.line) == line_no:
						t = t.replace('\n', self.fmt % error.msg)
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


