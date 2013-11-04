#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

import os
import sys
import xml.etree.ElementTree as ElementTree
from xml.dom import minidom
import pygments
from pygments import formatters, lexers
from waflib import TaskGen, Task, Context, Logs


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
		default='20', action='store',
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
	check = self.bld.env.CPPCHECK_EXECUTE
	if not bool(check) and not bld.options.cppcheck:
		return
	if getattr(self, 'cppcheck_skip', False):
		return
	
	task = self.create_task('Cppcheck')
	task.fatal = []
	if not bld.options.cppcheck_err_resume:
		task.fatal.append('error')


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


class CppcheckDefect(object):
	pass


class Cppcheck(Task.Task):		
	def run(self):
		bld = self.generator.bld
		cmd = self._get_cmd()
		stderr = bld.cmd_and_log(cmd, quiet=Context.STDERR, output=Context.STDERR)
		
		path = 'reports/cppcheck'
		if not os.path.exists(path):
			os.makedirs(path)

		self._save_xml_report(stderr, cmd, path)
		defects = self._get_defects(stderr)
		index = self._create_html_report(defects, path)
		self._defects_evaluate(defects, index)
		return 0

	def _get_cmd(self):
		gen = self.generator
		env = self.env
		bld = self.generator.bld
		
		features = getattr(gen, 'features', [])
		std_c = env.CPPCHECK_STD_C
		std_cxx = env.CPPCHECK_STD_CXX
		max_configs = env.CPPCHECK_MAX_CONFIGS
		bin_enable = env.CPPCHECK_BIN_ENABLE
		lib_enable = env.CPPCHECK_LIB_ENABLE

		cmd  = '%s' % env.CPPCHECK
		args = ['-q', '-v', '--xml', '--xml-version=2']
		args.append('--report-progress')	
		args.append('--max-configs=%s' % max_configs)

		if 'cxx' in features:
			args.append('--language=c++')
			args.append('--std=%s' % std_cxx)
		else:
			args.append('--language=c')
			args.append('--std=%s' % std_c)

		if bld.options.cppcheck_check_config:
			args.append('--check-config')

		if set(['cprogram','cxxprogram']) & set(features):
			args.append('--enable=%s' % bin_enable)
		else:
			args.append('--enable=%s' % lib_enable)

		for src in gen.to_list(gen.source):
			args.append('%r' % src)
		for inc in gen.to_incnodes(gen.to_list(getattr(gen, 'includes', []))):
			args.append('-I%r' % inc)
		for inc in gen.to_incnodes(gen.to_list(gen.env.INCLUDES)):
			args.append('-I%r' % inc)
		return [cmd] + args

	def _save_file(self, fname, content):
		bld = self.generator.bld
		path = os.path.dirname(fname)
		
		if not os.path.exists(path):
			os.makedirs(path)
			
		node = bld.path.make_node(fname)
		node.write(content)
		return node

	def _xml_clean(self, content):
		s = minidom.parseString(content).toprettyxml(indent="\t", encoding="utf-8")
		lines = [l for l in s.splitlines() if len(l.strip())]
		return '\n'.join(lines)

	def _html_clean(self, content):
		h = '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">'
		lines = [l for l in content.splitlines() if len(l.strip())]
		lines.insert(0, h)
		return '\n'.join(lines)

	def _save_xml_report(self, stderr, cmd, path):
		gen = self.generator

		root = ElementTree.fromstring(stderr)
		element = ElementTree.SubElement(root.find('cppcheck'), 'cmd')
		element.text = str(' '.join(cmd))
		
		content = self._xml_clean(ElementTree.tostring(root))
		fname = '%s/%s/%s.xml' % (path, gen.path.relpath(), gen.get_name())		
		self._save_file(fname, content)

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
				defect.line = str(int(location.get('line')) - 1)

			defects.append(defect)
		return defects

	def _create_html_report(self, defects, path):
		files, css_style_defs = self._create_html_files(defects, path)
		index = self._create_html_index(files, path)
		self._create_css_file(css_style_defs, path)
		return index

	def _create_html_files(self, defects, path):
		sources = {}
		defects = [d for d in defects if getattr(d, 'file', None)]
		for defect in defects:
			name = defect.file
			if not sources.has_key(name):
				sources[name] = [defect]
			else:
				sources[name].append(defect)
		
		gen = self.generator
		files = {}
		css_style_defs = None
		names = sources.keys()
		path = '%s/%s/%s' % (path, gen.path.relpath(), gen.get_name())
		
		for i in range(0,len(names)):
			src = names[i]
			fname = '%s/%i.html' % (path, i)
			errors = sources[src]
			files[src] = { 'htmlfile': fname, 'errors': errors }
			css_style_defs = self._create_html_file(fname, src, errors)
		return files, css_style_defs

	def _create_html_file(self, fname, sourcefile, errors):
		gen = self.generator
		bld = self.generator.bld
		name = gen.get_name()
		
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
			if div.get('id') == 'content':
				content = div
				srcnode = bld.root.find_node(sourcefile)
				hl_lines = [e.line for e in errors if getattr(e, 'line')]
				formatter = CppcheckHtmlFormatter(linenos=True, style='colorful', hl_lines=hl_lines, lineanchors='line')
				formatter.errors = [e for e in errors if getattr(e, 'line')]
				css_style_defs = formatter.get_style_defs('.highlight')
				lexer = pygments.lexers.guess_lexer_for_filename(sourcefile, "")
				s = pygments.highlight(srcnode.read(), lexer, formatter)
				table = ElementTree.fromstring(s)
				content.append(table)

		content = ElementTree.tostring(root, method='html')
		content = self._html_clean(content)
		self._save_file(fname, content)		
		return css_style_defs

	def _create_html_index(self, files, path):
		gen = self.generator
		name = gen.get_name()

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
				h1.text = 'cppcheck report - %s' % name
			if div.get('id') == 'content':
				content = div
				self._create_html_table(content, files)

		fname = '%s/%s/%s/index.html' % (path, gen.path.relpath(), gen.get_name())
		content = ElementTree.tostring(root, method='html')
		content = self._html_clean(content)
		return self._save_file(fname, content)

	def _create_html_table(self, content, files):
		bld = self.generator.bld
		table = ElementTree.fromstring(CPPCHECK_HTML_TABLE)
		for name, val in files.items():
			f = '%s/%s' % (bld.path.abspath().replace('\\', '/'), val['htmlfile'])
			s = '<tr><td colspan="4"><a href="%s">%s</a></td></tr>\n' % (f,name)
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

	def _create_css_file(self, css_style_defs, path):
		gen = self.generator
		css = str(CPPCHECK_CSS_FILE)

		if css_style_defs:
			css = "%s\n%s\n" % (css, css_style_defs)

		fname = '%s/%s/%s/style.css' % (path, gen.path.relpath(), gen.get_name())
		self._save_file(fname, css)

	def _defects_evaluate(self, defects, http_index):
		gen = self.generator
		bld = self.generator.bld
		
		name = gen.get_name()
		fatal = self.fatal
		severity = [d.severity for d in defects]
		problems = [d for d in defects if d.severity != 'information']

		if set(fatal) & set(severity):
			exc  = "\n"
			exc += "\nccpcheck detected fatal error(s) in task '%s', see report for details:" % (name)
			exc += "\n    file://%r" % (http_index)
			exc += "\n"
			bld.fatal(exc)

		elif len(problems):
			msg =  "\nccpcheck detected (possible) problem(s) in task '%s', see report for details:" % (name)
			msg += "\n    file://%r" % (http_index)
			msg += "\n"
			Logs.error(msg)


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
				<a href="index.html">Defect list</a>
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

	