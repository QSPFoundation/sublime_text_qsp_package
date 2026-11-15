import os

from typing import List, Tuple, Optional

Ext = str
from .plugtypes import (
	Path, FileName
)

# standart funcs for

def safe_mk_fold(folder:Path) -> None:
	""" Safe make dir with making all chain of dir """
	os.makedirs(folder, exist_ok=True)

def write_error_log(error_text:str) -> None:
	""" Write message in console. """
	print(error_text)

def get_files_list(folder:Path, filters:Optional[List[Ext]]=None) -> List[Path]:
	""" Create list of files in folder and includes folders. """
	if filters is None: filters = ['.qsps', '.qsp-txt', '.txt-qsp']
	build_files:List[Path] = []
	for abs_path, _, files in os.walk(folder):
		for file in files:
			sp = os.path.splitext(file)
			if (not filters) or (sp[1] in filters):
				build_files.append(os.path.join(abs_path, file))
	if not build_files:
		write_error_log(f'[200] Folder is empty. Prove path «{folder}».')
	return build_files

def compare_paths(path1:Path, path2:Path) -> Tuple[Path, Path]:
	"""	Compare two paths and return tail relative to shared folder. """
	start = os.path.commonpath([path1, path2])
	path1 = os.path.relpath(path1, start)
	path2 = os.path.relpath(path2, start)
	return path1, path2

def search_project_folder(point_file:Path, project_file:FileName='qsp-project.json') -> Path:
	"""
		Find project-file and return folder path whith project.
		In other return None.
	"""
	project_folder = (os.path.split(point_file)[0] if os.path.isfile(point_file) else point_file)
	while not os.path.isfile(os.path.join(project_folder, project_file)):
		if os.path.ismount(project_folder):
			raise FileNotFoundError(f"[202] not found '{project_file}' "+
					f"file. Prove path {point_file}.")
		project_folder = os.path.split(project_folder)[0]
	else:
		return project_folder

def del_first_pref(lines:List[str]) -> List[str]:
	"""
		Delete first preformatted symbols from start of lines
	"""
	common:List[str] = []
	for chars in zip(*lines):
		if len(set(chars)) == 1 and chars[0] in (' ', '\t'):
			common.append(chars[0])
		else:
			break
	if not common: return lines
	return [line[len(common):] for line in lines]

def is_path_in_project_folders(path:Optional[Path],
								project_folders:List[Path]) -> bool:
	"""
		Prove that path is existed in project_folders.
	"""
	if path is None: return False
	abs_path = os.path.normcase(os.path.abspath(path))
	for folder in project_folders:
		try:
			abs_folder = os.path.normcase(os.path.abspath(folder))
			if os.path.commonpath([abs_path, abs_folder]) == abs_folder:
				return True
		except ValueError as e: # если файлы лежат на разных дисках. TODO: убрать вывод в консоль
			write_error_log(f'[203] Different pathes of folder and file. Error "{str(e)}". path: {path}. folder: {folder}.')
			continue
	return False

def is_path_excluded(file_path:Path, exclude_pathes:Optional[List[Path]]=None) -> bool:
	"""
		Prove that file_path is excluded by exclude_pathes.
		exclude_pathes — absolute paths of folders/files to skip.
		Returns True if file_path equals one of excludes or lies inside an exclude folder.
	"""
	if not exclude_pathes: return False
	abs_file = os.path.normcase(os.path.abspath(file_path))
	for excl in exclude_pathes:
		abs_excl = os.path.normcase(os.path.abspath(excl))
		try:
			if abs_file == abs_excl or os.path.commonpath([abs_file, abs_excl]) == abs_excl:
				return True
		except ValueError: # разные диски — не вложенность
			continue
	return False

if __name__=="__main__":
	...
