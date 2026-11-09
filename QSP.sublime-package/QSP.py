import sublime
import sublime_plugin
import subprocess

import os
import re
import json
from typing import Dict, Optional, Union, List, Tuple, cast

# Importing my modules from qSpy package.
from .qSpy.builder import BuildQSP
from .qSpy.converter import (
	QspToQspsBuiltinConv, QspsToQspBuiltinConv,
	QspSplitter, FinderSplitter
)
from .qSpy.workspace import (
	FilePlace, LocHash, QspWorkspace, ViewPlace,
	QSP_WORKSPACES, cache_file_path, flush_workspaces_on_exit, for_window, identity_of,
	peek_for_window, prune_orphan_caches, remove_index_entry,
)
from .qSpy.vars_scanner import scan_vars
from .qSpy import function as qsp
from .qSpy.project import QspProject
# Import constants
from .qSpy import const

# My typing
from .qSpy import plugtypes as ts
Path = ts.Path
Value = Union[bool, str, int, float, List['Value'], Dict[str, 'Value'], None]
CommandArgs = Optional[Dict[str, Value]]

class QspBuildCommand(sublime_plugin.WindowCommand):
	"""
		QSP-Game Builder. Build and run QSP-game from sources. Need a qsp-project.json.
	"""
	def run(self, qsp_mode:ts.QspMode = "--br") -> None:
		# Three commands from arguments.
		argv = self.window.extract_variables()
		window_folders:List[Path] = self.window.folders()

		if not ('file' in argv or window_folders):
			# If not point file or opened folder in window (empty window)
			qsp.write_error_log(const.QSP_ERROR_MSG.NEED_SAVE_FILE)
			return None

		# -----------------------------------------------------------------------
		args:ts.SchemeArgs = {}

		args['point_file'] = os.path.abspath(argv.get('file', '')) # - start point for search `qsp-project.json`
		args['platform'] = sublime.platform()
		args['packages_path'] = sublime.packages_path()
		# -----------------------------------------------------------------------

		qsp_proj = QspProject(args, window_folders)
		if qsp_proj.scheme_is_wrong():
			qsp.write_error_log(const.QSP_ERROR_MSG.EMPTY_PROJECT)
			return None

		# old_time = time.time()
		builder = BuildQSP(qsp_proj.get_scheme()) # Initialise of Builder.
		if (qsp_mode in ('--br', '--build')): builder.build_project()
		if (qsp_mode in ('--br', '--run')): builder.run_game()

		if not os.path.isfile(qsp_proj.get_project_file()):
			qsp_proj.save_json()
		# new_time = time.time()
		# print(new_time - old_time)

class QspToQspsCommand(sublime_plugin.WindowCommand):
	""" Command to start converting QSP-Game to qsps """
	def run(self) -> None:
		argv = self.window.extract_variables()
		if not 'file' in argv:
			qsp.write_error_log(const.QSP_ERROR_MSG.NOT_CHOOSING_FILE)
			return
		if argv['file_extension'] != 'qsp':
			qsp.write_error_log(const.QSP_ERROR_MSG.WRONG_EXTENSION_QSP)
			return
		qsp_to_qsps = QspToQspsBuiltinConv()
		qsp_to_qsps.convert_file(argv['file'])


class QspsToQspCommand(sublime_plugin.WindowCommand):
	""" Comand of converting qsps-file to QSP-Game """
	def run(self) -> None:
		argv = self.window.extract_variables()
		if not 'file' in argv:
			qsp.write_error_log(const.QSP_ERROR_MSG.NOT_CHOOSING_FILE)
			return
		if not argv.get('file_extension', '') in ('qsps', 'qsp-txt', 'txt-qsp'):
			qsp.write_error_log(const.QSP_ERROR_MSG.WRONG_EXTENSION_QSPS)
			return

		output_file = os.path.splitext(argv['file'])[0]+'.qsp'
		qsps_to_qsp= QspsToQspBuiltinConv(output_file, False)
		qsps_to_qsp.convert_file(argv['file'], output_file) # TODO: extras output_path

class DecodeQspLineCommand(sublime_plugin.WindowCommand):
	""" Comand of converting qsp-line to qsps-line """
	# set cursor at line, or select the text
	def run(self) -> None:
		view = self.window.active_view()
		if not view: return
		lines:List[str] = [] # decodes lines
		n:str = QspsToQspBuiltinConv.encode_qsps_line('\n')
		rn:str = QspsToQspBuiltinConv.encode_qsps_line('\r\n')
		for region in cast(List[sublime.Region], view.sel()):
			if region.empty():
				# add line to lines list
				l = QspToQspsBuiltinConv.decode_qsp_line(view.substr(view.line(region.begin())))
				lines.append(l)
			else:
				l = view.substr(region).replace('\n', n).replace(rn, n)
				l = QspToQspsBuiltinConv.decode_qsp_line(l)
				lines.append(l)
		new_view = self.window.new_file()
		self.window.focus_view(new_view)
		new_view.run_command(
			'qsp_insert_decoded_lines',
			{'lines': lines, 'insert_at': 0} # atract the arguments
		)

class QspInsertDecodedLinesCommand(sublime_plugin.TextCommand):
	""" Insert the prepared lines. """
	def run(self, edit:sublime.Edit, lines:List[str], insert_at:int=0) -> None:
		self.view.insert(edit, insert_at, '\n'.join(lines))

class QspSplitterCommand(sublime_plugin.WindowCommand):
	"""
		Start command of split QSP-Game or qsps-file
		at some qsps-files.
	"""
	def run(self) -> None:
		argv = self.window.extract_variables()
		if argv['file_extension'] in ('qsps', 'qsp-txt', 'txt-qsp'):
			QspSplitter('txt').split_file(argv['file'])
		elif argv['file_extension'] == 'qsp':
			QspSplitter('game').split_file(argv['file'])
		else:
			qsp.write_error_log(const.QSP_ERROR_MSG.WRONG_EXTENSION_SPLITTER)

class QspSplitProjectCommand(sublime_plugin.WindowCommand):
	""" Start command of convert and split QSP-pproject """
	def run(self) -> None:
		argv = self.window.extract_variables()
		# argv['file_path'] - is folder of file, abspath
		FinderSplitter().search_n_split(folder_path = argv['file_path'])

class QspNewProjectCommand(sublime_plugin.WindowCommand):
	""" Create New Standart QSP-project """
	def run(self) -> None:
		argv = self.window.extract_variables()
		if not 'folder' in argv: return None # нет папок в проекте
		first_folder = argv['folder']
		_jont = os.path.join
		os.makedirs(_jont(first_folder,'_disdocs'), exist_ok=True)
		os.makedirs(_jont(first_folder,'_output_game'), exist_ok=True)
		# assets_folder = _jont(first_folder, '_output_game', 'assets')
		# os.makedirs(_jont(assets_folder, 'img'), exist_ok=True)
		# os.makedirs(_jont(assets_folder, 'snd'), exist_ok=True)
		# os.makedirs(_jont(assets_folder, 'vid'), exist_ok=True)
		# os.makedirs(_jont(first_folder, '_output_game', 'lib'), exist_ok=True)
		os.makedirs(_jont(first_folder, '_src'), exist_ok=True)
		# crete qsp-project.json
		project_json_path = _jont(first_folder, 'qsp-project.json')
		if not os.path.isfile(project_json_path):
			with open(project_json_path, 'w', encoding='utf-8') as file:
				json.dump(dict(const.QSP_PROJECT_JSON), file, indent=4)
		# create sublime-project
		_, fname = os.path.split(first_folder)
		sublproj_path = _jont(first_folder, fname + '.sublime-project')
		if not os.path.isfile(sublproj_path):
			with open(sublproj_path, 'w', encoding='utf-8') as file:
				json.dump(dict(const.QSP_SUBLIME_PROJECT), file, indent=4)
		# переоткрываем quick-project
		subprocess.Popen(
			[sublime.executable_path(), "--project", sublproj_path],
			startupinfo=subprocess.STARTUPINFO(dwFlags=subprocess.STARTF_USESHOWWINDOW)
			if sublime.platform() == "windows" else None,
		)
		self.window.run_command("close_window")
		# create startfile
		start_file_path = _jont(first_folder, '_src', '00_start.qsps')
		if not os.path.isfile(start_file_path):
			with open(start_file_path, 'w', encoding='utf-8') as file:
				file.writelines(const.QSP_START_TEMPLATE)
			self.window.open_file(start_file_path)

class QspNewGameHeadCommand(sublime_plugin.TextCommand):
	""" Generate New game Head and insert in viewport """
	def run(self, edit:sublime.Edit) -> None:
		qsps_text = ''.join(const.QSP_START_TEMPLATE)
		self.view.insert(edit, 0, qsps_text)

class QspNewGameCommand(sublime_plugin.WindowCommand):
	""" Generate new viewport with QSP-syntax """
	def run(self) -> None:
		new_view = self.window.new_file(syntax='Packages/QSP/qsp.sublime-syntax')
		self.window.focus_view(new_view)
		self.window.run_command('qsp_new_game_head')

class QspAnalyzerCommand(sublime_plugin.WindowCommand):
	""" Analyse of code, and search errors, locations names, varnames etc. """
	def run(self) -> None:
		# window = self.window
		# view = window.active_view()
		# if view is None: return None
		# if QspWorkspace.view_syntax_is_wrong(view): return None
		# text = view.substr(sublime.Region(0, view.size()))
		# masked = _mask_strings_and_braces(text)
		# g = _read_grammar_keywords()
		# print(g)
		# # Extract locations and labels (by convention and grammar respectively)
		# loc_names = []
		# for m in re.finditer(r'(?mi)^\#\s*([^\r\n]+?)\s*$', text):
		# 	loc_names.append(m.group(1))
		# labels = []
		# for m in re.finditer(r'(?mi)^\:\s*([^\r\n&]+?)\s*$', masked):
		# 	labels.append(m.group(1))
		# # User calls
		# user_statements = re.findall(r'(?mi)@@([A-Za-z_][A-Za-z0-9_]*)', masked)
		# user_functions = re.findall(r'(?mi)(?<!@)@([A-Za-z_][A-Za-z0-9_]*)', masked)
		# # Statements and functions
		# stmts = {}
		# if len(g['statements']) > 0:
		# 	stmts_alt = '|'.join(sorted(map(re.escape, g['statements']), key=len, reverse=True))
		# 	pattern_stmt = re.compile(rf'(?mi)(?<![\w])(?:{stmts_alt})(?=(?:\s|[&\'\"\(\)\[\]=!<>+\-\/*:,\{{\}}]|$))')
		# 	for m in pattern_stmt.finditer(masked):
		# 		name = m.group(0).lower()
		# 		stmts[name] = stmts.get(name, 0) + 1
		# funcs = {}
		# if len(g['functions']) > 0:
		# 	funcs_alt = '|'.join(sorted(map(re.escape, g['functions']), key=len, reverse=True))
		# 	pattern_func = re.compile(rf'(?mi)(?<![\w])[#\$%]?((?:{funcs_alt}))\b')
		# 	for m in pattern_func.finditer(masked):
		# 		name = m.group(1).lower()
		# 		funcs[name] = funcs.get(name, 0) + 1
		# # Variables (rough extraction: identifiers not in keywords)
		# keywords = set().union(g['functions'], g['statements'], g['markers'])
		# vars_found = set()
		# for m in re.finditer(r'(?mi)(?<![\w])[#\$%]?[A-Za-z_][\w\.]*', masked):
		# 	name = m.group(0)
		# 	root = name.lstrip('#$%').split('.')[0].lower()
		# 	if root not in keywords and not root.startswith('_'):
		# 		vars_found.add(name)
		# # Blocks: if/act/loop ... end (approximate)
		# line_starts = _pos_to_line_index_map(text)
		# blocks = []
		# stack = []
		# for m in re.finditer(r'(?mi)(?<![\w])(if|act|loop|end)\b', masked):
		# 	tok = m.group(1).lower()
		# 	ln = _line_number_at(m.start(), line_starts)
		# 	if tok in ('if', 'act', 'loop'):
		# 		stack.append((tok, ln))
		# 	elif tok == 'end' and len(stack) > 0:
		# 		start_tok, start_ln = stack.pop()
		# 		blocks.append({'type': start_tok, 'start_line': start_ln, 'end_line': ln})
		# # Prepare output
		# data = {
		# 	'file': (view.file_name() or f'untitled:{view.id()}'),
		# 	'locations': sorted(loc_names),
		# 	'labels': sorted(labels),
		# 	'user_calls': {
		# 		'statements': sorted(user_statements),
		# 		'functions': sorted(user_functions)
		# 	},
		# 	'counts': {
		# 		'statements': stmts,
		# 		'functions': funcs
		# 	},
		# 	'variables': sorted(vars_found),
		# 	'blocks': blocks
		# }
		# panel = window.create_output_panel('qsp_analyzer')
		# panel.set_syntax_file('Packages/JavaScript/JSON.sublime-syntax')
		# panel.run_command('append', {'characters': json.dumps(data, indent=2, ensure_ascii=False)})
		# window.run_command('show_panel', {'panel': 'output.qsp_analyzer'})
		...

class QspReplicStructCommand(sublime_plugin.WindowCommand):
	""" Generate folder with md-files as links structure """
	def run(self) -> None:
		...

class QspLocalVarsHighlightCommand(sublime_plugin.TextCommand):
	""" Find and highlight local variables command """

	def run(self, edit:sublime.Edit) -> None:
		view = self.view
		if QspWorkspace.view_syntax_is_wrong(view): return None
		local_vars, _ = scan_vars(view)
		view.run_command('qsp_hide_highlight')
		view.add_regions('local_vars', local_vars, 'region.orangish', flags=sublime.DRAW_NO_OUTLINE)

class QspGlobalVarsHighlightCommand(sublime_plugin.TextCommand):
	""" Find and high light global variables command """

	def run(self, edit:sublime.Edit) -> None:
		view = self.view
		if QspWorkspace.view_syntax_is_wrong(view): return None
		_, global_vars = scan_vars(view)
		view.run_command('qsp_hide_highlight')
		view.add_regions('global_vars', global_vars, 'region.yellowish', flags=sublime.DRAW_NO_OUTLINE)

class QspHideHighlightCommand(sublime_plugin.TextCommand):

	def run(self, edit:sublime.Edit) -> None:
		view = self.view
		if len(view.get_regions('wrong_location'))>0: view.erase_regions('wrong_location')
		if len(view.get_regions('local_vars'))>0: view.erase_regions('local_vars')
		if len(view.get_regions('global_vars'))>0: view.erase_regions('global_vars')

class QspShowDuplLocsCommand(sublime_plugin.TextCommand):

	def run(self, edit:sublime.Edit) -> None:
		""" Show duplicates of locations in project. """
		del edit
		view = self.view
		window = view.window()
		if not window: return
		all_views = window.views()
		project_folders = window.folders()
		qsp_ws = for_window(window)
		qsp_ws.refresh_from_views(all_views, project_folders)
		qsp_locs = qsp_ws.locs_dupl()
		popup_msg = ''
		for i, qsp_loc in enumerate(qsp_locs): # int, tuple in list[qsp_loc]
			qsp_loc_name, qsp_loc_region, qsp_loc_place = qsp_loc
			if isinstance(qsp_loc_place, FilePlace):
				file_path = qsp_loc_place.path
				if os.path.isfile(file_path):
					count = ''
					with open(file_path, 'r', encoding='utf-8') as file:
						string = file.read()
					match = re.search(
						r'^\#\s*'+re.escape(qsp_loc_name)+'$',
						string,
						flags=re.MULTILINE)
					if match is not None: count = ':'+str(len(string[:match.start()].split('\n')))
					file_name = os.path.basename(file_path)
					popup_msg += f'{i+1}. {qsp_loc_name}. <a href="f:{file_path}{count}">'
					popup_msg += f'{file_name}{count}</a><br>'
				else:
					qsp_ws.del_all_locs_by_place(qsp_loc_place)
					continue
			else:
				for v in all_views:
					if v.id() == qsp_loc_place.vid:
						popup_msg += f'{i+1}. {qsp_loc_name}. <a href="v:{v.id()}?'
						popup_msg += f'{qsp_loc_region[0]}">untitled ({v.id()})</a><br>'
						break
		w = int(view.viewport_extent()[0]/1.5)
		vr = view.visible_region().begin()
		view.show_popup(popup_msg, max_width=w, location=vr, on_navigate=self.on_navigate)

	def on_navigate(self, link:str) -> None: # link - relpath or abspath
		window = self.view.window()
		if not window: return
		current_view = window.active_view()
		if link.startswith('f:'):
			link = link[2:]
			# Separator can only be ':': the href is Sublime's own "file:line" format.
			# A qsp path always ends with an extension, so a trailing ':<digits>' is only
			# ever the line number (rsplit from the right -> safe on win/*nix alike).
			head, sep, tail = link.rpartition(':')
			line = tail if sep and tail.isdigit() else ''
			path = head if line else link
			if current_view is not None and current_view.file_name() == path:
				window.focus_view(current_view)
				if line:
					point = current_view.text_point(int(line)-1, 0) # 1-based line -> 0-based row
					current_view.sel().clear()
					current_view.sel().add(sublime.Region(point, point))
			elif line:
				window.run_command('open_file', {'file': f'{path}:{line}', 'encoded_position': True})
			else:
				window.run_command('open_file', {'file': path})
		elif link.startswith('v:'):
			link = link[2:]
			parts = link.split('?')
			view_id = int(parts[0])
			region_begin = int(parts[1])
			if current_view is not None and current_view.id() == view_id:
				window.focus_view(current_view)
				current_view.sel().clear()
				current_view.sel().add(sublime.Region(region_begin, region_begin))
				current_view.hide_popup()
			else:
				for v in window.views():
					if v.id() == view_id:
						window.focus_view(v)
						v.sel().clear()
						v.sel().add(sublime.Region(region_begin, region_begin))
						break

class QspHideHightlight(sublime_plugin.EventListener):
	"""
		Where entering the text, hide all temp hightlights of QSP-regions.
	"""
	def on_modified(self, view:sublime.View) -> None:
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		view.run_command('qsp_hide_highlight')

class QspInvalidInput(sublime_plugin.EventListener):
	"""
		Wrong input of qsp-locs names or labels names
	"""
	def on_modified(self, view:sublime.View) -> None:
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		window = view.window()
		if not window: return None
		qsp_ws = peek_for_window(window)
		if qsp_ws is None: return None
		begin = view.sel()[0].begin()
		end = view.sel()[0].end()
		sr_locname = view.expand_to_scope(begin, 'meta.start_location.qsp')
		sr_lblname = view.expand_to_scope(begin, 'entity.name.qlabel.qsp')

		if begin == end and sr_locname is not None:
			input_region = (sr_locname.begin(), sr_locname.end())
			input_text = view.substr(sr_locname)
			current_qsps = view.file_name()
			project_folders = window.folders()
			if qsp.is_path_in_project_folders(current_qsps, project_folders):
				qsps_file_place = FilePlace(cast(Path, current_qsps))
			else:
				qsps_file_place = ViewPlace(view.id())
			def _filting_qsplocs(qsp_loc:LocHash) -> bool:
				return qsp_loc[1] != input_region or qsp_loc[2] != qsps_file_place
			all_locations = qsp_ws.get_locs()
			loc_names = [loc[0] for loc in filter(_filting_qsplocs, all_locations)]
			if not input_text in loc_names:
				return None
			content = sublime.expand_variables(const.QSP_MSG.WRONG_LOC, {"input_text": input_text})
			view.add_regions('wrong_location', [sr_locname],
				scope="region.redish",
				annotations=[content],
				flags=sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)
			# sublime.message_dialog(content)
		elif begin == end and sr_lblname is not None:
			input_text = view.substr(sr_lblname)
			qsp_labels = QspWorkspace.get_qsplbls(view, exclude_inputting=sr_lblname)
			if input_text in qsp_labels:
				content = sublime.expand_variables(const.QSP_MSG.WRONG_LBL, {"input_text": input_text})
				# view.show_popup(content, flags=sublime.HTML, location=-1, max_width=250)
				# sublime.message_dialog(content)
				view.add_regions('wrong_location', [sr_lblname],
					scope="region.redish",
					annotations=[content],
					flags=sublime.DRAW_SQUIGGLY_UNDERLINE | sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)

class QspAutocomplete(sublime_plugin.EventListener):
	""" Autocomplete and helptips. """

	def on_query_completions(self,
			view:sublime.View,
			prefix:str,
			locations:List[int]
		) -> Optional[Tuple[List[sublime.CompletionItem], sublime.AutoCompleteFlags]]:
		""" Append completions in editor."""
		if locations[0]-1 < 0: return None
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		window = view.window()
		if not window: return
		project_folders = window.folders()
		if not project_folders: return None # If project is not exist -> completions not work.
		qsp_ws = peek_for_window(window)
		if qsp_ws is None: return None
		qsp_completions:List[sublime.CompletionItem] = []
		# if syntshugarfunc
		if view.match_selector(locations[0]-1, 'variable.function.qsp'):
			qsp_loc_names = qsp_ws.get_locs_names() # -> list of loc names
			for loc_name in qsp_loc_names:
				if prefix.lower() in loc_name.lower():
					d = sublime.CompletionItem(
						loc_name,
						annotation="Локация",
						completion=loc_name,
						completion_format=sublime.COMPLETION_FORMAT_TEXT,
						kind=sublime.KIND_FUNCTION
					)
					qsp_completions.append(d)
			return (qsp_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		# if calable operator call location
		elif view.match_selector(locations[0]-1, 'callable_locs.qsp'):
			qsp_loc_names = qsp_ws.get_locs_names() # -> list of loc names
			scope_region = view.expand_to_scope(locations[0]-1, 'callable_locs.qsp')
			if not scope_region: return
			input_text = view.substr(scope_region)
			for loc_name in qsp_loc_names:
				if str(input_text[1:-1].lower()) in loc_name.lower():
					d = sublime.CompletionItem(
						loc_name,
						annotation="Локация",
						completion=loc_name,
						completion_format=sublime.COMPLETION_FORMAT_TEXT,
						kind=sublime.KIND_FUNCTION
					)
					qsp_completions.append(d)
			return (qsp_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		elif view.match_selector(locations[0]-1, 'label_to_jump.qsp'):
			qsp_all_lbls = QspWorkspace.get_qsplbls(view)
			scope_region = view.expand_to_scope(locations[0]-1, 'label_to_jump.qsp')
			if not scope_region: return
			input_text = view.substr(scope_region)
			for qsp_lb in qsp_all_lbls:
				if str(input_text[1:-1].lower()) in qsp_lb.lower():
					d = sublime.CompletionItem(
						qsp_lb,
						annotation="Метка",
						completion=qsp_lb,
						completion_format=sublime.COMPLETION_FORMAT_TEXT,
						kind=sublime.KIND_MARKUP
					)
					qsp_completions.append(d)
			return (qsp_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
		else:
			return None

class QspTips(sublime_plugin.EventListener):
	""" Listener of stand caret to keyword of QSP-syntax """
	def on_selection_modified(self, view:sublime.View) -> None:
		""" Show tips in statusbar """
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		word_coords = view.word(view.sel()[0].begin()) # Region
		word = view.substr(word_coords).lower() # str
		p = word_coords.begin()-1 # int (Point)
		pref = (view.substr(p) if p > -1 else '') # str
		keywords = const.QSP_CMD_TIPS.keys()
		if pref == '*' and ('*' + word in keywords):
			word = '*' + word
			match = re.match(r'^\*\w+\b$', word)
		elif pref == '$' and ('$' + word in keywords):
			word = '$' + word
			match = re.match(r'^\$\w+\b$', word)
		elif pref == '%' and ('%' + word in keywords):
			word = '%' + word
			match = re.match(r'^\%\w+\b$', word)
		else:
			match = re.match(r'^\w+\b$', word)
		if (match is not None) and (word in keywords):
			sublime.status_message(const.QSP_CMD_TIPS[word])



class QspShowWorkspaceCacheCommand(sublime_plugin.WindowCommand):
	""" Показать файл кэша воркспейса активного окна (R3). """

	def run(self) -> None:
		identity = identity_of(self.window)
		if identity is None:
			sublime.status_message('[QSP] Файл кэша не ведётся: окну не сопоставлен .sublime-project (И2).')
			return
		path = cache_file_path(identity)
		if path and os.path.isfile(path):
			self.window.open_file(path)
			sublime.status_message(f'[QSP] Файл кэша: {path}')
		else:
			sublime.status_message(f'[QSP] Файла кэша нет: {path}')


class QspResetWorkspaceCacheCommand(sublime_plugin.WindowCommand):
	""" Сбросить кэш воркспейса активного окна и пересобрать индекс (R3). """

	def run(self) -> None:
		window = self.window
		identity = identity_of(window)
		path = cache_file_path(identity) if identity else None
		if path and os.path.isfile(path):
			try:
				os.remove(path)
			except OSError as e:
				sublime.status_message(f'[QSP] Не удалось удалить кэш: {e}')
				return
			if identity:
				remove_index_entry(identity)
		# Пересборка RAM-индекса тем же путём, что восстановление окна (R1/R4/R5, Д11).
		qsp_ws = for_window(window)
		qsp_ws.rebind(identity, list(window.folders()))
		qsp_ws.reset()
		folders = window.folders()
		if folders:
			qsp_ws.refresh_qsps_files(folders)
			qsp_ws.refresh_from_views(window.views(), folders)
		if identity is not None:
			saved = qsp_ws.save_to_cache()
			if saved:
				sublime.status_message(f'[QSP] Кэш воркспейса пересобран и сохранён: {saved}')
			else:
				sublime.status_message('[QSP] Кэш воркспейса пересобран, но сохранить файл не удалось.')
		else:
			sublime.status_message('[QSP] Кэш воркспейса пересобран в памяти. Для сохранения кэша на диск нужен .sublime-project (И2).')


class QspWorkspaceHandlers(sublime_plugin.EventListener):
	""" Manage a qsp-workspace in ram and in files """

	_log_it = False

	# Живой индекс локаций (2.8, R5/И3): дебаунс per-view счётчиком поколений таймеров.
	# Задержка — кандидат, подтвердить замером при ручной приёмке (handoff §4.3).
	_LOCS_DEBOUNCE_MS = 250
	_locs_gen:Dict[int, int] = {} # view.id() -> поколение последнего таймера; чистится его же колбэком

	def _log(self, string:str) -> None:
		if self._log_it:
			print('[QSP WS] ' + string)

	def _refresh_ws(self, window:sublime.Window) -> None:
		"""
			Восстановить WS окна (R3/R4/R5, 4.7): загрузить v2-кэш из cache_path, затем
			инкрементально сверить с диском по mtime/size/md5. Окно без папок пропускаем.
		"""
		folders = window.folders()
		if not folders: return None
		qsp_ws = for_window(window)
		qsp_ws.load_from_cache() # принимает кэш v2 (или остаётся пустым/не built)
		qsp_ws.refresh_qsps_files(folders) # инкрементальный скан, выставляет built
		qsp_ws.refresh_from_views(window.views(), folders)

# ----------------------------------- Events of work with project -----------------------------------

	# When plugin or project are loading, extract workspaces from files and refresh all workspaces.
	def on_init(self, views:List[sublime.View]) -> None: # all views of ST
		"""
			Event of init the plugin (start programm, or reload plugin).
		"""
		for window in sublime.windows(): # many windows may be open
			self._refresh_ws(window)

	def on_load_project_async(self, window:sublime.Window) -> None:
		"""
			Event of loading the project.
		"""
		self._refresh_ws(window)

	# When project is closing, save the already-built WS to cache and drop it from the registry.
	def on_pre_close_project(self, window:sublime.Window) -> None:
		"""
			Event of pre closing the project.
			Флаш-точка (R5): сохраняем уже построенный WS окна в cache_path и убираем запись из реестра.
			Никогда НЕ создаёт WS (2.1); путь берётся из identity WS (cache_path подготовлен заранее).
		"""
		qsp_ws = peek_for_window(window)
		if qsp_ws is None: return None # живого WS этого окна нет — сохранять нечего, фантом не плодим
		qsp_ws.save_to_cache() # v2 в cache_path; None для без identity/unbuilt — безопасно (И2/R4)
		QSP_WORKSPACES.pop(window.id(), None) # убрать запись, иначе реестр течёт при закрытии (Д10)
		sublime.set_timeout_async(prune_orphan_caches, 0) # R6: чистка сироток не чаще раза в 7 дней, async

	# Closing the whole window. Для окна с проектом запись уже снята on_pre_close_project,
	# которое приходит раньше (Д23); этот хук нужен лишь для безпроектных окон — к ним
	# приходит только он (Д24). На диск ничего не пишется: файл кэша таким окнам не положен (И2).
	def on_pre_close_window(self, window:sublime.Window) -> None:
		"""
			Event of pre closing the window (4050): чистка RAM-реестра по window.id().
		"""
		QSP_WORKSPACES.pop(window.id(), None)
		sublime.set_timeout_async(prune_orphan_caches, 0) # R6: и при закрытии безпроектного окна

# ----------------------------------- Events of work with project -----------------------------------

# ------------------------------------ Events of work with files ------------------------------------

	# Work with WS in RAM.

	def on_load_async(self, view:sublime.View) -> None:
		"""
			Event of load file (view).
			When file is loading, refresh locs in ws (vars — on-demand через scan_vars, 2.4/4.5).
		"""
		if QspWorkspace.view_syntax_is_wrong(view): return None
		window = view.window()
		if not window: return
		current_qsps = view.file_name()
		folders = window.folders()
		if not folders or not current_qsps: return None
		if not qsp.is_path_in_project_folders(current_qsps, folders):
			return None
		qsp_ws = for_window(window)
		qsp_ws.refresh_qsplocs(view, current_qsps)

	def on_modified_async(self, view:sublime.View) -> None:
		""" Живой индекс локаций (2.8, R5/И3): изменение текста сдвигает срок перескана этого вью.
			Дебаунс per-view счётчиком поколений: каждая правка планирует свой таймер, устаревшие
			гасятся в колбэке (отмены таймеров API не даёт). Пересканируется только этот вью. """
		if QspWorkspace.view_syntax_is_wrong(view): return None
		vid = view.id()
		gen = self._locs_gen.get(vid, 0) + 1
		self._locs_gen[vid] = gen
		sublime.set_timeout_async(lambda: self._refresh_qsplocs_debounced(view, gen), self._LOCS_DEBOUNCE_MS)

	def _refresh_qsplocs_debounced(self, view:sublime.View, gen:int) -> None:
		""" Перескан локаций одного вью тем же refresh_qsplocs, если правка была последней. """
		vid = view.id()
		if self._locs_gen.get(vid) != gen: return None # таймер устарел: есть более новая правка
		self._locs_gen.pop(vid, None) # последний таймер вью: чистим, чтобы словарь не рос
		if QspWorkspace.view_syntax_is_wrong(view): return None
		window = view.window()
		if not window: return None # вью/окно уже закрыто (Д15)
		qsp_ws = peek_for_window(window)
		if qsp_ws is None: return None # accessor без создания (R5): WS этого окна ещё не строили
		current_qsps = view.file_name()
		# И1: именованный файл вне папок окна не индексируем; безымянный буфер — в RAM (place=view.id())
		if current_qsps is not None and not qsp.is_path_in_project_folders(current_qsps, window.folders()):
			return None
		qsp_ws.refresh_qsplocs(view, current_qsps)

	def on_pre_close(self, view:sublime.View) -> None:
		"""
			Event of pre close the view.
			Runed before closing the window, if you close window!
		"""
		# Д15: при закрытии окна с проектом хук приходит после on_pre_close_project,
		# и view.window() уже None; pop уже снят — peek не воссоздаёт фантом (2.5).
		if QspWorkspace.view_syntax_is_wrong(view): return None
		window = view.window()
		if not window: return
		current_qsps = view.file_name()
		folders = window.folders()
		if not folders: return None
		qsp_ws = peek_for_window(window)
		if qsp_ws is None: return None # проекта уже нет в реестре, либо WS ещё не строили
		# close the untitled view
		if current_qsps is None:
			qsp_ws.del_all_locs_by_place(ViewPlace(view.id()))
		elif not qsp.is_path_in_project_folders(current_qsps, folders):
			return None
		if current_qsps in QSP_MARKERS['delete_files']:
			sublime.set_timeout_async(lambda: qsp_ws.refresh_qsps_files(folders), 250)
			QSP_MARKERS['delete_files'] = []
		elif qsp_ws.qsps_files_number() == 0:
			qsp_ws.refresh_qsps_files(folders)

	def on_post_save_async(self, view:sublime.View) -> None:
		"""
			Event post saving of file.
		"""
		self._log('on_post_save_async')
		if QspWorkspace.view_syntax_is_wrong(view): return None
		window = view.window()
		if not window: return None
		current_qsps = view.file_name()
		folders = window.folders()
		if not folders or not current_qsps: return None
		if not qsp.is_path_in_project_folders(current_qsps, folders):
			return None # И1 (2.7): файл вне папок окна не индексируем, как в on_load_async
		qsp_ws = for_window(window)
		qsp_ws.refresh_qsplocs(view, current_qsps) # TODO: возможно стоит удалить
		qsp_ws.touch_file(current_qsps) # 4.7: перечитать локации файла и обновить mtime/size/md5
		qsp_ws.refresh_from_views(window.views(), folders)

	def on_exit(self) -> None:
		""" Выход из ST (4050): флаш всех живых WS чистым IO без sublime-API (R5, Д20-Д22). """
		flush_workspaces_on_exit(QSP_WORKSPACES)

	def on_associate_buffer_async(self, buffer:sublime.Buffer) -> None:
		"""
			This event is runed after renaming or creating a new file.
			refresh files list in workspace
		"""
		if QSP_MARKERS['rename_path']:
			window = buffer.primary_view().window()
			if not window: return
			folders = window.folders()
			if not folders: return # окно без папок (2.2): folders[0] недоступен
			qsp_ws = for_window(window)
			qsp_ws.refresh_from_views(window.views(), folders)
			qsp_ws.refresh_qsps_files(folders)
			QSP_MARKERS['rename_path'] = False

# ------------------------------------ Events of work with files ------------------------------------

# ---------------------------------- Events for action recognition ----------------------------------

	def on_window_command(self, window:sublime.Window, command_name:str,
																args:CommandArgs) -> None:
		if command_name in ('rename_path'):
			QSP_MARKERS[command_name] = True
		elif command_name in ('delete_file') and args:
			QSP_MARKERS['delete_files'] = cast(List[Path], args.get('files',[]))

# ---------------------------------- Events for action recognition ----------------------------------


# variables
# RAM-реестр (4.1/4.4): QSP_WORKSPACES в qSpy.workspace; доступ только через for_window/peek_for_window.
QSP_MARKERS:ts.QspPluginCommandMarkers = {
	# editing files commands and events
	'rename_path': False,
	'delete_files': [],
	'save_log_file': False
}

def foo():

	w = sublime.active_window()
	print("win_id", w.id())
	print("folders", w.folders())
	print("project", w.project_file_name())
	print("keys", list(QSP_WORKSPACES.keys()))
	ws = QSP_WORKSPACES.get(w.id())
	if ws:
		print("identity", ws.identity)
		print("scope", ws.scope)
	else:
		print("no WS for this window")