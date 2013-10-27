#! /usr/bin/env python
# -*- encoding: utf-8 -*-
# Michel Mooij, michel.mooij7@gmail.com

# shell colors
# @echo -e "[0;32m$2: $1[0m"

import os
import re
from waflib import Utils, Node, Tools

def export(bld):
	root = MakeRoot(bld)
	for gen, targets in bld.components.items():
		child = MakeChild(bld, gen, targets)
		child.export()
		root.add_child(child.get_data())
	root.export()


def cleanup(bld):
	root = MakeRoot(bld)
	for gen, targets in bld.components.items():
		child = MakeChild(bld, gen, targets)
		child.cleanup()
	root.cleanup()


class Make(object):
	def __init__(self, bld):
		self.bld = bld
		self.exp = bld.export

	def export(self):
		content = self.get_content()
		if not content:
			return
		node = self.make_node()
		if not node:
			return
		node.write(content)
			
	def cleanup(self): 
		node = self.find_node()
		if node:
			node.delete()

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
		
	def populate(self, content):
		s = content
		s = re.sub('==WAFVERSION==', self.exp.wafversion, s)
		s = re.sub('==VERSION==', self.exp.version, s)
		return s

	def get_name(self): 
		'''abstract operation to be define in child'''
		return None

	def get_content(self):
		'''abstract operation to be define in child'''
		return None


class MakeRoot(Make):
	def __init__(self, bld):
		super(MakeRoot, self).__init__(bld)
		self.childs = []

	def get_name(self):
		bld = self.bld
		return '%s/Makefile' % (bld.path.relpath().replace('\\', '/'))

	def get_content(self):
		prefix = os.path.abspath(self.exp.prefix)
		if prefix.startswith(os.getcwd()):
			prefix = '$(CURDIR)%s' % prefix[len(os.getcwd()):]

		out = os.path.abspath(self.exp.out)
		if out.startswith(os.getcwd()):
			out = '$(TOP)%s' % out[len(os.getcwd()):]
		
		s = MAKEFILE_ROOT
		s = super(MakeRoot, self).populate(s)
		s = re.sub('APPNAME:=', 'APPNAME:=%s' % self.exp.appname, s)
		s = re.sub('APPVERSION:=', 'APPVERSION:=%s' % self.exp.appversion, s)
		s = re.sub('OUT:=', 'OUT:=%s' % out, s)
		s = re.sub('BINDIR:=', 'BINDIR:=%s' % self.exp.bindir, s)
		s = re.sub('LIBDIR:=', 'LIBDIR:=%s' % self.exp.libdir, s)
		s = re.sub('AR:=', 'AR:=%s' % self.exp.ar, s)
		s = re.sub('CC:=', 'CC:=%s' % self.exp.cc, s)
		s = re.sub('CXX:=', 'CXX:=%s' % self.exp.cxx, s)
		s = re.sub('RPATH:=', 'RPATH:=%s' % self.exp.rpath, s)
		s = re.sub('CFLAGS:=', 'CFLAGS:=%s' % self.exp.cflags, s)
		s = re.sub('CXXFLAGS:=', 'CXXFLAGS:=%s' % self.exp.cxxflags, s)
		s = re.sub('DEFINES:=', 'DEFINES:=%s' % self.exp.defines, s)
		s = re.sub('==MODULES==', self._get_modules(), s)
		s = re.sub('==MODPATHS==', self._get_modpaths(), s)
		s = re.sub('==MODDEPS==', self._get_moddeps(), s)	
		s = re.sub(self.exp.prefix, '$(PREFIX)', s)
		s = re.sub('PREFIX:=', 'PREFIX:=%s' % prefix, s)
		return s

	def add_child(self, child):
		self.childs.append(child)
	
	def _get_modules(self):
		d = []
		for (name, _, _) in self.childs:
			d.append(name)
		s = ' \\\n\t'.join(d)
		return s

	def _get_modpaths(self):
		d = []
		for (name, makefile, _) in self.childs:
			s = '%s;%s' %(name, os.path.dirname(makefile))
			d.append(s)
		s = ' \\\n\t'.join(d)
		return s

	def _get_moddeps(self):
		d = []
		for (name, _, deps) in self.childs:
			s = '%s;' %(name)
			if len(deps):
				s += ','.join(deps)
			d.append(s)
		s = ' \\\n\t'.join(d)
		return s

	
class MakeChild(Make):
	def __init__(self, bld, gen, targets):
		super(MakeChild, self).__init__(bld)
		self.gen = gen
		self.targets = targets
		self._process()

	def get_name(self):
		gen = self.gen
		return '%s/Makefile' % (gen.path.relpath().replace('\\', '/'))

	def get_content(self):		
		if 'cprogram' in self.gen.features:
			return self._get_cprogram_content()
		elif 'cxxprogram' in self.gen.features:
			return self._get_cxxprogram_content()
		elif 'cstlib' in self.gen.features:
			return self._get_cstlib_content()
		elif 'cshlib' in self.gen.features:
			return self._get_cshlib_content()
		
		s = MAKEFILE_CHILD
		s = super(MakeChild, self).populate(s)		
		return s
		
	def get_data(self):
		gen = self.gen
		name = gen.get_name()
		makefile = self.get_name()
		deps = Utils.to_list(getattr(gen, 'use', []))
		return (name, makefile, deps)
	
	def _process(self):
		bld = self.bld
		self.lib = {}
		self.lib['static'] = { 'name' : [], 'path' : [] }
		self.lib['shared'] = { 'name' : [], 'path' : [] }
			
		for target in self.targets:
			if not isinstance(target, Tools.ccroot.link_task):
				continue
			for arg in target.cmd:
				if arg == bld.env.SHLIB_MARKER:
					key = 'shared'
				elif arg == bld.env.STLIB_MARKER:
					key = 'static'
				elif arg.startswith('-L'):
					self.lib[key]['path'].append(arg[2:])
				elif arg.startswith('-l'):
					self.lib[key]['name'].append(arg[2:])

	def _get_cprogram_content(self):
		bld = self.bld
		gen = self.gen
		source = self._get_genlist(gen, 'source')
		includes = self._get_genlist(gen, 'includes')
		defines = self._get_defines(gen)
		defines = [d for d in defines]
		s = MAKEFILE_CPROGRAM
		s = super(MakeChild, self).populate(s)
		name = bld.env.cprogram_PATTERN % gen.get_name()
		s = re.sub('BIN=', 'BIN=%s' % name, s)
		s = re.sub('SOURCES=', 'SOURCES= \\\n\t%s' % ' \\\n\t'.join(source), s)
		s = re.sub('INCLUDES\+=', 'INCLUDES+= \\\n\t%s' % ' \\\n\t'.join(includes),s)
		s = re.sub('DEFINES\+=', 'DEFINES+=%s' % ' '.join(defines),s)
		s = re.sub('CFLAGS\+=', 'CFLAGS+=%s' % self._get_cflags(gen),s)
		s = re.sub('LINKFLAGS\+=', 'LINKFLAGS+=%s' % self._get_linkflags(gen),s)
		s = re.sub('LIBPATH_ST\+=', 'LIBPATH_ST+=%s' % self._get_libpath('static'),s)
		s = re.sub('LIB_ST\+=', 'LIB_ST+=%s' % self._get_lib('static'),s)
		s = re.sub('LIBPATH_SH\+=', 'LIBPATH_SH+=%s' % self._get_libpath('shared'),s)
		s = re.sub('LIB_SH\+=', 'LIB_SH+=%s' % self._get_lib('shared'),s)
		return s
	
	def _get_cxxprogram_content(self):
		bld = self.bld
		gen = self.gen
		source = self._get_genlist(gen, 'source')
		includes = self._get_genlist(gen, 'includes')
		defines = self._get_defines(gen)
		defines = [d for d in defines]
		s = MAKEFILE_CXXPROGRAM
		s = super(MakeChild, self).populate(s)
		name = bld.env.cxxprogram_PATTERN % gen.get_name()
		s = re.sub('BIN=', 'BIN=%s' % name, s)
		s = re.sub('SOURCES=', 'SOURCES= \\\n\t%s' % ' \\\n\t'.join(source), s)
		s = re.sub('INCLUDES\+=', 'INCLUDES+= \\\n\t%s' % ' \\\n\t'.join(includes),s)
		s = re.sub('DEFINES\+=', 'DEFINES+=%s' % ' '.join(defines),s)
		s = re.sub('CXXFLAGS\+=', 'CXXFLAGS+=%s' % self._get_cxxflags(gen),s)
		s = re.sub('LINKFLAGS\+=', 'LINKFLAGS+=%s' % self._get_linkflags(gen),s)
		s = re.sub('LIBPATH_ST\+=', 'LIBPATH_ST+=%s' % self._get_libpath('static'),s)
		s = re.sub('LIB_ST\+=', 'LIB_ST+=%s' % self._get_lib('static'),s)
		s = re.sub('LIBPATH_SH\+=', 'LIBPATH_SH+=%s' % self._get_libpath('shared'),s)
		s = re.sub('LIB_SH\+=', 'LIB_SH+=%s' % self._get_lib('shared'),s)
		return s

	def _get_cstlib_content(self):
		bld = self.bld
		gen = self.gen
		source = self._get_genlist(gen, 'source')
		includes = self._get_genlist(gen, 'includes')
		defines = self._get_defines(gen)
		defines = [d for d in defines]
		s = MAKEFILE_CSTLIB
		s = super(MakeChild, self).populate(s)
		name = bld.env.cstlib_PATTERN % gen.get_name()
		s = re.sub('LIB=', 'LIB=%s' % name, s)
		s = re.sub('SOURCES=', 'SOURCES= \\\n\t%s' % ' \\\n\t'.join(source), s)
		s = re.sub('INCLUDES\+=', 'INCLUDES+= \\\n\t%s' % ' \\\n\t'.join(includes),s)
		s = re.sub('DEFINES\+=', 'DEFINES+=%s' % ' '.join(defines),s)
		s = re.sub('CFLAGS\+=', 'CFLAGS+=%s' % self._get_cflags(gen),s)
		s = re.sub('ARFLAGS=', 'ARFLAGS=%s' % bld.env.ARFLAGS, s)
		return s

	def _get_cshlib_content(self):
		bld = self.bld
		gen = self.gen
		source = self._get_genlist(gen, 'source')
		includes = self._get_genlist(gen, 'includes')
		defines = self._get_defines(gen)
		defines = [d for d in defines]
		s = MAKEFILE_CSHLIB
		s = super(MakeChild, self).populate(s)
		name = bld.env.cshlib_PATTERN % gen.get_name()
		vnum = getattr(gen, 'vnum', '')
		s = re.sub('LIB=', 'LIB=%s' % name, s)
		s = re.sub('VNUM=', 'VNUM=%s' % vnum, s)
		s = re.sub('SOURCES=', 'SOURCES= \\\n\t%s' % ' \\\n\t'.join(source), s)
		s = re.sub('INCLUDES\+=', 'INCLUDES+= \\\n\t%s' % ' \\\n\t'.join(includes),s)
		s = re.sub('DEFINES\+=', 'DEFINES+=%s' % ' '.join(defines),s)
		s = re.sub('CFLAGS\+=', 'CFLAGS+=%s' % self._get_cflags(gen),s)
		s = re.sub('LINKFLAGS\+=', 'LINKFLAGS+=%s' % self._get_linkflags(gen),s)
		s = re.sub('LIBPATH_ST\+=', 'LIBPATH_ST+=%s' % self._get_libpath('static'),s)
		s = re.sub('LIB_ST\+=', 'LIB_ST+=%s' % self._get_lib('static'),s)
		s = re.sub('LIBPATH_SH\+=', 'LIBPATH_SH+=%s' % self._get_libpath('shared'),s)
		s = re.sub('LIB_SH\+=', 'LIB_SH+=%s' % self._get_lib('shared'),s)
		return s
	
	def _get_genlist(self, gen, name):
		lst = Utils.to_list(getattr(gen, name, []))
		return [l.path_from(gen.path) if isinstance(l, Node.Nod3) else l for l in lst]

	def _get_defines(self, gen):
		defines = []
		defs = self._get_genlist(gen, 'defines')
		for d in defs:
			if d.count('"') == 2:
				(pre, val, post) = d.split('"')
				d = '%s\'"%s"\'%s' % (pre, val, post) 
			defines.append(d)
		return defines

	def _get_cflags(self, gen):
		cflags = getattr(gen, 'cflags', [])
		if 'cshlib' in gen.features:
			cflags.extend(self.bld.env.CFLAGS_cshlib)
		return ' '.join(cflags)

	def _get_cxxflags(self, gen):
		cxxflags = getattr(gen, 'cxxflags', [])
		if 'cxxshlib' in gen.features:
			cxxflags.extend(self.bld.env.CXXFLAGS_cxxshlib)
		return ' '.join(cxxflags)

	def _get_linkflags(self, gen):
		linkflags = getattr(gen, 'linkflags', [])
		if 'cshlib' in gen.features:
			linkflags.extend(self.bld.env.LINKFLAGS_cshlib)
		if 'cxxshlib' in gen.features:
			linkflags.extend(self.bld.env.LINKFLAGS_cxxshlib)
		return ' '.join(linkflags)

	def _get_libpath(self, kind):
		libpath = self.lib[kind]['path']
		return ' \\\n\t'.join(['$(TOP)/build/%s' % l for l in libpath])

	def _get_lib(self, kind):
		lib = self.lib[kind]['name']
		return ' '.join(lib)


MAKEFILE_ROOT = \
'''#------------------------------------------------------------------------------
# CHIHUAHUA generated makefile
# version: ==VERSION==
# waf: ==WAFVERSION==
#------------------------------------------------------------------------------

SHELL=/bin/sh

# commas, spaces and tabs:
sp:= 
sp+= 
tab:=$(sp)$(sp)$(sp)$(sp)
comma:=,

# token for separating dictionary keys and values:
dsep:=;

# token for separating list elements:
lsep:=,

export APPNAME:=
export APPVERSION:=
export PREFIX:=
export TOP:=$(CURDIR)
export OUT:=
export AR:=
export CC:=
export CXX:=
export CFLAGS:=
export CXXFLAGS:=
export DEFINES:=
export RPATH:=
export BINDIR:=
export LIBDIR:=

SEARCHPATH=components/
SEARCHFILE=Makefile

#------------------------------------------------------------------------------
# list of unique logical module names;
modules= \\
	==MODULES==

# dictionary of modules names (key) and paths to modules;
paths= \\
	==MODPATHS==

# dictionary of modules names (key) and module dependencies;
deps= \\
	==MODDEPS==

#------------------------------------------------------------------------------
# define targets
#------------------------------------------------------------------------------
build_targets=$(addprefix build_,$(modules))
clean_targets=$(addprefix clean_,$(modules))
install_targets=$(addprefix install_,$(modules))
uninstall_targets=$(addprefix uninstall_,$(modules))

cmds=build clean install uninstall
commands=$(sort $(cmds) all help find list modules $(foreach prefix,$(cmds),$($(prefix)_targets)))

.DEFAULT_GOAL:=all

#------------------------------------------------------------------------------
# recursive wild card implementation
#------------------------------------------------------------------------------
define rwildcard
$(wildcard $1$2) $(foreach d,$(wildcard $1*),$(call rwildcard,$d/,$2))
endef

#------------------------------------------------------------------------------
# returns the value from a dictionary
# $1 = key, where key is the functional name of the component.
# $2 = dictionary
#------------------------------------------------------------------------------
define getdval
$(subst $(lastword $(subst _,$(sp),$1))$(dsep),$(sp),$(filter $(lastword $(subst _,$(sp),$1))$(dsep)%,$2))
endef

#------------------------------------------------------------------------------
# returns path to makefile
# $1 = key, where key is the functional name of the component.
#------------------------------------------------------------------------------
define getpath
$(call getdval, $1, $(paths))
endef

#------------------------------------------------------------------------------
# returns component dependencies.
# $1 = key, where key is the functional name of the component.
#------------------------------------------------------------------------------
define getdeps
$(addprefix $(firstword $(subst _,$(sp),$1))_,$(subst $(lsep),$(sp),$(call getdval, $1, $(deps))))
endef

#------------------------------------------------------------------------------
# creates a make recipe
# $1 = key, where key is the functional recipe name (e.g. build_a).
#------------------------------------------------------------------------------
define domake
$1: $(call getdeps, $1)
	$(MAKE) -r -C $(call getpath,$1) $(firstword $(subst _,$(sp),$1))
endef

#------------------------------------------------------------------------------
# return files found in given search path
# $1 = search path
# $2 = file name so search
#------------------------------------------------------------------------------
define dofind
$(foreach path, $(dir $(call rwildcard,$1,$2)),echo "  $(path)";)
endef

#------------------------------------------------------------------------------
# definitions of recipes (i.e. make targets)
#------------------------------------------------------------------------------
all: build
	
build: $(build_targets)

clean: $(clean_targets)

install: build $(install_targets)

uninstall: $(uninstall_targets)

list:
	@echo ""
	@$(foreach cmd,$(commands),echo "  $(cmd)";)
	@echo ""

modules:
	@echo ""
	@$(foreach module,$(modules),echo "  $(module)";)
	@echo ""

find:
	@echo ""
	@echo "$@:"
	@echo "  path=$(SEARCHPATH) file=$(SEARCHFILE)"
	@echo ""
	@echo "result:"
	@$(call dofind,$(SEARCHPATH),$(SEARCHFILE))
	@echo ""

help:
	@echo ""
	@echo "$(APPNAME) version $(APPVERSION)"
	@echo ""
	@echo "usage:"
	@echo "  make [-r] [-s] [--jobs=N] [command] [VARIABLE=VALUE]"
	@echo ""
	@echo "commands:"
	@echo "  all                                 builds all modules"
	@echo "  build                               builds all modules"
	@echo "  build_a                             builds module 'a' and it's dependencies"
	@echo "  clean                               removes all build intermediates and outputs"
	@echo "  clean_a                             cleans module 'a' and it's dependencies"
	@echo "  install                             installs files in $(PREFIX)"
	@echo "  install_a                           installs module 'a' and it's dependencies"
	@echo "  uninstall                           removes all installed files from $(PREFIX)"
	@echo "  uninstall_a                         removes module 'a' and it's dependencies"
	@echo "  list                                list available make commands (i.e. recipes)"
	@echo "  modules                             list logical names of all modules"
	@echo "  find [SEARCHPATH=] [SEARCHFILE=]    searches for files default(path=$(SEARCHPATH),file=$(SEARCHFILE))"
	@echo "  help                                displays this help message."
	@echo ""
	@echo "remarks:"
	@echo "  use options '-r' and '--jobs=N' in order to improve speed"
	@echo "  use options '-s' to decrease verbosity"
	@echo ""

$(foreach t,$(build_targets),$(eval $(call domake,$t)))

$(foreach t,$(clean_targets),$(eval $(call domake,$t)))

$(foreach t,$(install_targets),$(eval $(call domake,$t)))

$(foreach t,$(uninstall_targets),$(eval $(call domake,$t)))

.PHONY: $(commands)

'''

MAKEFILE_CHILD = \
'''#------------------------------------------------------------------------------
# CHIHUAHUA generated makefile
# version: ==VERSION==
# waf: ==WAFVERSION==
#------------------------------------------------------------------------------

commands:= build clean install uninstall all

all: build
	
build:
	@echo BUILD $(abspath $(@D))

clean:
	@echo CLEAN $(abspath $(@D))

install:
	@echo INSTALL $(abspath $(@D))
	
uninstall:
	@echo UNINSTALL $(abspath $(@D))

.PHONY: $(commands)

'''

MAKEFILE_CPROGRAM = \
'''#------------------------------------------------------------------------------
# CHIHUAHUA generated makefile
# version: ==VERSION==
# waf: ==WAFVERSION==
#------------------------------------------------------------------------------

SHELL=/bin/sh

# commas, spaces and tabs:
sp:= 
sp+= 
tab:=$(sp)$(sp)$(sp)$(sp)
comma:=,

#------------------------------------------------------------------------------
# definition of build and install locations
#------------------------------------------------------------------------------
ifeq ($(TOP),)
TOP=$(CURDIR)
OUT=$(TOP)/build
else
OUT=$(subst $(sp),/,$(call rptotop) build $(call rpofcomp))
endif

PREFIX?=$(HOME)
BINDIR?=$(PREFIX)/bin
LIBDIR?=$(PREFIX)/lib

#------------------------------------------------------------------------------
# component data
#------------------------------------------------------------------------------
BIN=
OUTPUT=$(OUT)/$(BIN)

# REMARK: use $(wildcard src/*.c) to include all sources.
SOURCES=

OBJECTS=$(SOURCES:.c=.1.o)

DEFINES+=
DEFINES:=$(addprefix -D,$(DEFINES))

INCLUDES+=

HEADERS:=$(foreach inc,$(INCLUDES),$(wildcard $(inc)/*.h))
INCLUDES:=$(addprefix -I,$(INCLUDES))

CFLAGS+=

LINKFLAGS+=

RPATH+=
RPATH:= $(addprefix -Wl$(comma)-rpath$(comma),$(RPATH))

LIBPATH_ST+=
LIBPATH_ST:= $(addprefix -L,$(LIBPATH_ST))

LIB_ST+=
LIB_ST:= $(addprefix -l,$(LIB_ST))

LIBPATH_SH+=
LIBPATH_SH:= $(addprefix -L,$(LIBPATH_SH))

LINK_ST= -Wl,-Bstatic $(LIBPATH_ST) $(LIB_ST)

LIB_SH+=
LIB_SH:= $(addprefix -l,$(LIB_SH))

LINK_SH= -Wl,-Bdynamic $(LIBPATH_SH) $(LIB_SH)

#------------------------------------------------------------------------------
# returns the relative path of this component from the top directory
#------------------------------------------------------------------------------
define rpofcomp
$(subst $(subst ~,$(HOME),$(TOP))/,,$(CURDIR))
endef

#------------------------------------------------------------------------------
# returns the relative path of this component to the top directory
#------------------------------------------------------------------------------
define rptotop
$(foreach word,$(subst /,$(sp),$(call rpofcomp)),..)
endef

#------------------------------------------------------------------------------
# define targets
#------------------------------------------------------------------------------
commands= build clean install uninstall all

.DEFAULT_GOAL=all

#------------------------------------------------------------------------------
# definitions of recipes (i.e. make targets)
#------------------------------------------------------------------------------
all: build
	
build: $(OBJECTS)
	$(CC) $(LINKFLAGS) $(addprefix $(OUT)/,$(OBJECTS)) -o $(OUTPUT) $(RPATH) $(LINK_ST) $(LINK_SH)

clean:
	$(foreach obj,$(OBJECTS),rm -f $(OUT)/$(obj);)	
	rm -f $(OUTPUT)

install: build
	mkdir -p $(BINDIR)
	cp $(OUTPUT) $(BINDIR)
	
uninstall:
	rm -f $(BINDIR)/$(BIN)

$(OBJECTS): $(HEADERS)
	mkdir -p $(OUT)/$(dir $@)
	$(CC) $(CFLAGS) $(INCLUDES) $(DEFINES) $(subst .1.o,.c,$@) -c -o $(OUT)/$@

.PHONY: $(commands)

'''

MAKEFILE_CXXPROGRAM = \
'''#------------------------------------------------------------------------------
# CHIHUAHUA generated makefile
# version: ==VERSION==
# waf: ==WAFVERSION==
#------------------------------------------------------------------------------

SHELL=/bin/sh

# commas, spaces and tabs:
sp:= 
sp+= 
tab:=$(sp)$(sp)$(sp)$(sp)
comma:=,

#------------------------------------------------------------------------------
# definition of build and install locations
#------------------------------------------------------------------------------
ifeq ($(TOP),)
TOP=$(CURDIR)
OUT=$(TOP)/build
else
OUT=$(subst $(sp),/,$(call rptotop) build $(call rpofcomp))
endif

PREFIX?=$(HOME)
BINDIR?=$(PREFIX)/bin
LIBDIR?=$(PREFIX)/lib

#------------------------------------------------------------------------------
# component data
#------------------------------------------------------------------------------
BIN=
OUTPUT=$(OUT)/$(BIN)

SOURCES=

OBJECTS=$(SOURCES:.cpp=.1.o)

DEFINES+=
DEFINES:=$(addprefix -D,$(DEFINES))

INCLUDES+=

HEADERS:=$(foreach inc,$(INCLUDES),$(wildcard $(inc)/*.h))
INCLUDES:=$(addprefix -I,$(INCLUDES))

CXXFLAGS+=

LINKFLAGS+=

RPATH+=
RPATH:= $(addprefix -Wl$(comma)-rpath$(comma),$(RPATH))

LIBPATH_ST+=
LIBPATH_ST:= $(addprefix -L,$(LIBPATH_ST))

LIB_ST+=
LIB_ST:= $(addprefix -l,$(LIB_ST))

LIBPATH_SH+=
LIBPATH_SH:= $(addprefix -L,$(LIBPATH_SH))

LINK_ST= -Wl,-Bstatic $(LIBPATH_ST) $(LIB_ST)

LIB_SH+=
LIB_SH:= $(addprefix -l,$(LIB_SH))

LINK_SH= -Wl,-Bdynamic $(LIBPATH_SH) $(LIB_SH)

#------------------------------------------------------------------------------
# returns the relative path of this component from the top directory
#------------------------------------------------------------------------------
define rpofcomp
$(subst $(subst ~,$(HOME),$(TOP))/,,$(CURDIR))
endef

#------------------------------------------------------------------------------
# returns the relative path of this component to the top directory
#------------------------------------------------------------------------------
define rptotop
$(foreach word,$(subst /,$(sp),$(call rpofcomp)),..)
endef

#------------------------------------------------------------------------------
# define targets
#------------------------------------------------------------------------------
commands= build clean install uninstall all

.DEFAULT_GOAL=all

#------------------------------------------------------------------------------
# definitions of recipes (i.e. make targets)
#------------------------------------------------------------------------------
all: build
	
build: $(OBJECTS)
	$(CXX) $(LINKFLAGS) $(addprefix $(OUT)/,$(OBJECTS)) -o $(OUTPUT) $(RPATH) $(LINK_ST) $(LINK_SH)

clean:
	$(foreach obj,$(OBJECTS),rm -f $(OUT)/$(obj);)	
	rm -f $(OUTPUT)

install: build
	mkdir -p $(BINDIR)
	cp $(OUTPUT) $(BINDIR)
	
uninstall:
	rm -f $(BINDIR)/$(BIN)

$(OBJECTS): $(HEADERS)
	mkdir -p $(OUT)/$(dir $@)
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(DEFINES) $(subst .1.o,.cpp,$@) -c -o $(OUT)/$@

.PHONY: $(commands)

'''

MAKEFILE_CSTLIB = \
'''#------------------------------------------------------------------------------
# CHIHUAHUA generated makefile
# version: ==VERSION==
# waf: ==WAFVERSION==
#------------------------------------------------------------------------------

SHELL=/bin/sh

# commas, spaces and tabs:
sp:= 
sp+= 
tab:=$(sp)$(sp)$(sp)$(sp)
comma:=,

#------------------------------------------------------------------------------
# definition of build and install locations
#------------------------------------------------------------------------------
ifeq ($(TOP),)
TOP=$(CURDIR)
OUT=$(TOP)/build
else
OUT=$(subst $(sp),/,$(call rptotop) build $(call rpofcomp))
endif

#------------------------------------------------------------------------------
# component data
#------------------------------------------------------------------------------
LIB=
OUTPUT=$(OUT)/$(LIB)

# REMARK: use $(wildcard src/*.c) to include all sources.
SOURCES= 

OBJECTS=$(SOURCES:.c=.1.o)

DEFINES+=
DEFINES:=$(addprefix -D,$(DEFINES))

INCLUDES+=

HEADERS:=$(foreach inc,$(INCLUDES),$(wildcard $(inc)/*.h))
INCLUDES:=$(addprefix -I,$(INCLUDES))

CFLAGS+=

ARFLAGS=

#------------------------------------------------------------------------------
# returns the relative path of this component from the top directory
#------------------------------------------------------------------------------
define rpofcomp
$(subst $(subst ~,$(HOME),$(TOP))/,,$(CURDIR))
endef

#------------------------------------------------------------------------------
# returns the relative path of this component to the top directory
#------------------------------------------------------------------------------
define rptotop
$(foreach word,$(subst /,$(sp),$(call rpofcomp)),..)
endef

#------------------------------------------------------------------------------
# define targets
#------------------------------------------------------------------------------
commands= build clean install uninstall all

.DEFAULT_GOAL=all

#------------------------------------------------------------------------------
# definitions of recipes (i.e. make targets)
#------------------------------------------------------------------------------
all: build
	
build: $(OBJECTS)
	$(AR) $(ARFLAGS) $(OUTPUT) $(addprefix $(OUT)/,$(OBJECTS))

clean:
	$(foreach obj,$(OBJECTS),rm -f $(OUT)/$(obj);)	
	rm -f $(OUTPUT)

install:
	
uninstall:

$(OBJECTS): $(HEADERS)
	mkdir -p $(OUT)/$(dir $@)
	$(CC) $(CFLAGS) $(INCLUDES) $(DEFINES) $(subst .1.o,.c,$@) -c -o $(OUT)/$@

.PHONY: $(commands)

'''

MAKEFILE_CSHLIB = \
'''#------------------------------------------------------------------------------
# CHIHUAHUA generated makefile
# version: ==VERSION==
# waf: ==WAFVERSION==
#------------------------------------------------------------------------------

SHELL=/bin/sh

# commas, spaces and tabs:
sp:= 
sp+= 
tab:=$(sp)$(sp)$(sp)$(sp)
comma:=,

#------------------------------------------------------------------------------
# definition of build and install locations
#------------------------------------------------------------------------------
ifeq ($(TOP),)
TOP=$(CURDIR)
OUT=$(TOP)/build
else
OUT=$(subst $(sp),/,$(call rptotop) build $(call rpofcomp))
endif

PREFIX?=$(HOME)
LIBDIR?=$(PREFIX)/lib

#------------------------------------------------------------------------------
# component data
#------------------------------------------------------------------------------
LIB=
OUTPUT=$(OUT)/$(LIB)

VNUM=

# REMARK: use $(wildcard src/*.c) to include all sources.
SOURCES= 

OBJECTS=$(SOURCES:.c=.1.o)

DEFINES+=
DEFINES:=$(addprefix -D,$(DEFINES))

INCLUDES+=

HEADERS:=$(foreach inc,$(INCLUDES),$(wildcard $(inc)/*.h))
INCLUDES:=$(addprefix -I,$(INCLUDES))

CFLAGS+= 

LINKFLAGS+= 

RPATH+=
RPATH:= $(addprefix -Wl$(comma)-rpath$(comma),$(RPATH))

LIBPATH_ST+=
LIBPATH_ST:= $(addprefix -L,$(LIBPATH_ST))

LIB_ST+=
LIB_ST:= $(addprefix -l,$(LIB_ST))

LIBPATH_SH+=
LIBPATH_SH:= $(addprefix -L,$(LIBPATH_SH))

LINK_ST= -Wl,-Bstatic $(LIBPATH_ST) $(LIB_ST)

LIB_SH+=
LIB_SH:= $(addprefix -l,$(LIB_SH))

LINK_SH= -Wl,-Bdynamic $(LIBPATH_SH) $(LIB_SH)

#------------------------------------------------------------------------------
# returns the relative path of this component from the top directory
#------------------------------------------------------------------------------
define rpofcomp
$(subst $(subst ~,$(HOME),$(TOP))/,,$(CURDIR))
endef

#------------------------------------------------------------------------------
# returns the relative path of this component to the top directory
#------------------------------------------------------------------------------
define rptotop
$(foreach word,$(subst /,$(sp),$(call rpofcomp)),..)
endef

#------------------------------------------------------------------------------
# define targets
#------------------------------------------------------------------------------
commands= build clean install uninstall all

.DEFAULT_GOAL=all

#------------------------------------------------------------------------------
# definitions of recipes (i.e. make targets)
#------------------------------------------------------------------------------
all: build
	
build: $(OBJECTS)
	$(CC) $(LINKFLAGS) $(addprefix $(OUT)/,$(OBJECTS)) -o $(OUTPUT) $(RPATH) $(LINK_ST) $(LINK_SH)

clean:
	$(foreach obj,$(OBJECTS),rm -f $(OUT)/$(obj);)	
	rm -f $(OUTPUT)

install: build
	mkdir -p $(LIBDIR)
	cp $(OUTPUT) $(LIBDIR)
ifneq ($(VNUM),)
	ln -s -f $(LIBDIR)/$(LIB) $(LIBDIR)/$(LIB).$(VNUM)
endif

uninstall:
ifneq ($(VNUM),)
	rm -f $(LIBDIR)/$(LIB).$(VNUM)
endif
	rm -f $(LIBDIR)/$(LIB)

$(OBJECTS): $(HEADERS)
	mkdir -p $(OUT)/$(dir $@)
	$(CC) $(CFLAGS) $(INCLUDES) $(DEFINES) $(subst .1.o,.c,$@) -c -o $(OUT)/$@

.PHONY: $(commands)

'''

