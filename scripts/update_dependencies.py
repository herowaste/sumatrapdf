"""
Updates the dependency lists in makefile.msvc for all object files produced
from sources in utils and src, so that changing a header file always leads
to the recompilation of all the files depending on this header.
"""

import os, re, fnmatch
from util import verify_started_in_right_directory, group, uniquify
pjoin = os.path.join

DIRS = ["src", pjoin("src", "utils"), pjoin("src", "installer"), pjoin("src", "ifilter"), pjoin("src", "browserplugin"), pjoin("src", "previewer"), pjoin("src", "ebooktest"), pjoin("src", "ebooktest2"), pjoin("src", "mui")]
INCLUDE_DIRS = DIRS + [pjoin("mupdf", "fitz"), pjoin("mupdf", "pdf"), pjoin("mupdf", "xps")]
OBJECT_DIRS = { "src\\utils": "$(OU)", "src\\browserplugin": "$(ODLL)", "src\\ifilter": "$(ODLL)", "src\\previewer": "$(ODLL)", "src\\ebooktest": "$(OEB)", "src\\ebooktest2": "$(OE2)", "src\\mui": "$(OMUI)" } # default: "$(OS)"
MAKEFILE = "makefile.deps"
DEPENDENCIES_PER_LINE = 3

def memoize(func):
	memory = {}
	def __decorated(*args):
		if args not in memory:
			memory[args] = func(*args)
		return memory[args]
	return __decorated

def prependPath(files, basefile=None):
	result = []
	include_dirs = INCLUDE_DIRS
	if basefile:
		include_dirs = [os.path.split(basefile)[0]] + include_dirs
	
	for file in files:
		for dir in include_dirs:
			path = pjoin(dir, file)
			if os.path.exists(path):
				result.append(path)
				break
	return result

def getObjectPath(file):
	file = file.replace("/", "\\")
	for (path, odir) in OBJECT_DIRS.items():
		if file.startswith(path + "\\"):
			return odir
	return "$(OS)"

@memoize
def extractIncludes(file):
	content = open(file, "r").read()
	# filter out multi-line comments (could contain #include lines as examples)
	content = re.sub(r'(?s)/\*.*?\*/', '/* */', content)
	includes = re.findall(r'(?m)^#include ["<]([^">]+)[">]', content)
	includes = prependPath(includes, file)

	for inc in includes:
		includes += extractIncludes(inc)
	return uniquify(includes)

def createDependencyList():
	dependencies = {}
	for dir in DIRS:
		all_c_files = fnmatch.filter(os.listdir(dir), "*.c*")
		for file in all_c_files:
			file = pjoin(dir, file)
			dependencies[file] = extractIncludes(file)
	return dependencies

def flattenDependencyList(dependencies):
	flatlist = []
	for file in dependencies.keys():
		if dependencies[file]:
			opath = getObjectPath(file)
			filename = os.path.splitext(os.path.split(file)[1])[0]
			deplist = sorted(dependencies[file], key=str.lower)
			for depgroup in group(deplist, DEPENDENCIES_PER_LINE):
				flatlist.append("%s\\%s.obj: %s" % (opath, filename, " ".join(depgroup)))
	return flatlist

def normalizePaths(paths):
	return re.sub(r"( |\\)[^.\\\s]+\\..\\", r"\1", paths.replace("/", "\\"))

def injectDependencyList(flatlist):
	flatlist = "\n".join(sorted(flatlist, key=str.lower))
	flatlist = normalizePaths(flatlist)
	content = "## Header-dependencies for src\* and src\*\*\n"
	content +=  "### the list below is auto-generated by update_dependencies.py\n" 
	content += flatlist + "\n"
	
	open(MAKEFILE, "wb").write(content.replace("\n", "\r\n"))

def main():
	if os.path.exists("update_dependencies.py"):
		os.chdir("..")
	verify_started_in_right_directory()
	
	injectDependencyList(flattenDependencyList(createDependencyList()))

if __name__ == "__main__":
	main()
