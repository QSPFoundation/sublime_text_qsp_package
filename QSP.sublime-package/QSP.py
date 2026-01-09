import sublime			# type: ignore
import sublime_plugin   # type: ignore

import os
import re
import json
from typing import Union, List, Tuple, cast, Dict, Literal
# import time

# Importing my modules from qSpy package.
from .qSpy.builder import BuildQSP
from .qSpy.qsp_to_qsps import QspToQsps
from .qSpy.qsps_to_qsp import NewQspsFile
from .qSpy.qsp_splitter import (QspSplitter, FinderSplitter)
from .qSpy.workspace import QspWorkspace
from .qSpy import function as qsp
# Import constants
from .qSpy import const

# My typing
import qSpy.plugtypes as ts

class QspBuildCommand(sublime_plugin.WindowCommand):
	"""
		QSP-Game Builder. Build and run QSP-game from sources. Need a qsp-project.json.
	"""
	def run(self, qsp_mode:str = "--br") -> None:
		# Three commands from arguments.
		argv = self.window.extract_variables()
		if not 'file' in argv:
			qsp.write_error_log(const.QSP_ERROR_MSG.NEED_SAVE_FILE)
			return None
		# -----------------------------------------------------------------------
		args:ts.BuilderArgs = {}

		args['build'] = (qsp_mode in ('--br', '--build'))  # - command for build the project
		args['run'] = (qsp_mode in ('--br', '--run'))      # - command for run the project
		args['point_file'] = os.path.abspath(argv['file']) # - start point for search `qsp-project.json`
		args['qgc_path'] = ''                              # - path to win-converter

		if sublime.platform() == 'windows':
			qgc_path = os.path.join(sublime.packages_path(),
				'QSP', 'qgc', 'app', 'QGC.exe')
			if os.path.isfile(qgc_path):
				args['qgc_path'] = qgc_path
		# -----------------------------------------------------------------------
				
		# old_time = time.time()
		builder = BuildQSP(args) # Initialise of Builder.
		builder.build_and_run()  # Run the Builder to work.
		# new_time = time.time()
		# print(new_time - old_time)

class QspToQspsCommand(sublime_plugin.WindowCommand):
	""" Command to start converting QSP-Game to qsps """
	def run(self) -> None:
		argv = self.window.extract_variables()
		file = argv['file']
		if argv['file_extension'] == 'qsp':
			qsp_to_qsps = QspToQsps()
			qsp_to_qsps.convert_file(file)
		else:
			qsp.write_error_log(const.QSP_ERROR_MSG.WRONG_EXTENSION_QSP)

class QspsToQspCommand(sublime_plugin.WindowCommand):
	""" Comand to start converting qsps-file to QSP-Game """
	def run(self) -> None:
		argv = self.window.extract_variables()
		if argv['file_extension'] in ('qsps', 'qsp-txt', 'txt-qsp'):
			qsps_file = NewQspsFile()
			qsps_file.convert_file(argv['file'])
		else:
			qsp.write_error_log(const.QSP_ERROR_MSG.WRONG_EXTENSION_QSPS)

class QspSplitterCommand(sublime_plugin.WindowCommand):
	"""
		Start command of split QSP-Game or qsps-file
		at some qsps-files.
	"""
	def run(self) -> None:
		argv = self.window.extract_variables()
		if argv['file_extension'] in ('qsps', 'qsp-txt', 'txt-qsp'):
			QspSplitter().split_file(argv['file'], mode='txt')
		elif argv['file_extension'] == 'qsp':
			QspSplitter().split_file(argv['file'], mode='game')
		else:
			qsp.write_error_log(const.QSP_ERROR_MSG.WRONG_EXTENSION_SPLITTER)

class QspSplitProjectCommand(sublime_plugin.WindowCommand):
	""" Start command of convert and split QSP-pproject """
	def run(self) -> None:
		argv = self.window.extract_variables()
		FinderSplitter().search_n_split(folder_path = argv['file_path'])

class QspNewProjectCommand(sublime_plugin.WindowCommand):
	""" Create New Standart QSP-project """
	def run(self) -> None:
		argv = self.window.extract_variables()
		if not 'folder' in argv: return None
		_jont = os.path.join
		qsp.safe_mk_fold(_jont(argv['folder'],'_disdocs'))
		assets_folder = _jont(argv['folder'], '_output_game', 'assets')
		qsp.safe_mk_fold(_jont(assets_folder, 'img'))
		qsp.safe_mk_fold(_jont(assets_folder, 'snd'))
		qsp.safe_mk_fold(_jont(assets_folder, 'vid'))
		qsp.safe_mk_fold(_jont(argv['folder'], '_output_game', 'lib'))
		qsp.safe_mk_fold(_jont(argv['folder'], '_src'))
		# crete qsp-project.json
		project_json_path = _jont(argv['folder'], '_src', 'qsp-project.json')
		if not os.path.isfile(project_json_path):
			with open(project_json_path, 'w', encoding='utf-8') as file:
				json.dump(dict(const.QSP_PROJECT_JSON), file, indent=4)
		# create sublime-project
		_, fname = os.path.split(argv['folder'])
		sublproj_path = _jont(argv['folder'], fname + '.sublime-project')
		if not os.path.isfile(sublproj_path):
			with open(sublproj_path, 'w', encoding='utf-8') as file:
				json.dump(dict(const.QSP_SUBLIME_PROJECT), file, indent=4)
		# create startfile
		start_file_path = _jont(argv['folder'], '_src', '00_start.qsps')
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
		window = self.window
		view = window.active_view()
		if view is None: return None
		if QspWorkspace.view_syntax_is_wrong(view): return None
		text = view.substr(sublime.Region(0, view.size()))
		masked = _mask_strings_and_braces(text)
		g = _read_grammar_keywords()
		print(g)
		# Extract locations and labels (by convention and grammar respectively)
		loc_names = []
		for m in re.finditer(r'(?mi)^\#\s*([^\r\n]+?)\s*$', text):
			loc_names.append(m.group(1))
		labels = []
		for m in re.finditer(r'(?mi)^\:\s*([^\r\n&]+?)\s*$', masked):
			labels.append(m.group(1))
		# User calls
		user_statements = re.findall(r'(?mi)@@([A-Za-z_][A-Za-z0-9_]*)', masked)
		user_functions = re.findall(r'(?mi)(?<!@)@([A-Za-z_][A-Za-z0-9_]*)', masked)
		# Statements and functions
		stmts = {}
		if len(g['statements']) > 0:
			stmts_alt = '|'.join(sorted(map(re.escape, g['statements']), key=len, reverse=True))
			pattern_stmt = re.compile(rf'(?mi)(?<![\w])(?:{stmts_alt})(?=(?:\s|[&\'\"\(\)\[\]=!<>+\-\/*:,\{{\}}]|$))')
			for m in pattern_stmt.finditer(masked):
				name = m.group(0).lower()
				stmts[name] = stmts.get(name, 0) + 1
		funcs = {}
		if len(g['functions']) > 0:
			funcs_alt = '|'.join(sorted(map(re.escape, g['functions']), key=len, reverse=True))
			pattern_func = re.compile(rf'(?mi)(?<![\w])[#\$%]?((?:{funcs_alt}))\b')
			for m in pattern_func.finditer(masked):
				name = m.group(1).lower()
				funcs[name] = funcs.get(name, 0) + 1
		# Variables (rough extraction: identifiers not in keywords)
		keywords = set().union(g['functions'], g['statements'], g['markers'])
		vars_found = set()
		for m in re.finditer(r'(?mi)(?<![\w])[#\$%]?[A-Za-z_][\w\.]*', masked):
			name = m.group(0)
			root = name.lstrip('#$%').split('.')[0].lower()
			if root not in keywords and not root.startswith('_'):
				vars_found.add(name)
		# Blocks: if/act/loop ... end (approximate)
		line_starts = _pos_to_line_index_map(text)
		blocks = []
		stack = []
		for m in re.finditer(r'(?mi)(?<![\w])(if|act|loop|end)\b', masked):
			tok = m.group(1).lower()
			ln = _line_number_at(m.start(), line_starts)
			if tok in ('if', 'act', 'loop'):
				stack.append((tok, ln))
			elif tok == 'end' and len(stack) > 0:
				start_tok, start_ln = stack.pop()
				blocks.append({'type': start_tok, 'start_line': start_ln, 'end_line': ln})
		# Prepare output
		data = {
			'file': (view.file_name() or f'untitled:{view.id()}'),
			'locations': sorted(loc_names),
			'labels': sorted(labels),
			'user_calls': {
				'statements': sorted(user_statements),
				'functions': sorted(user_functions)
			},
			'counts': {
				'statements': stmts,
				'functions': funcs
			},
			'variables': sorted(vars_found),
			'blocks': blocks
		}
		panel = window.create_output_panel('qsp_analyzer')
		panel.set_syntax_file('Packages/JavaScript/JSON.sublime-syntax')
		panel.run_command('append', {'characters': json.dumps(data, indent=2, ensure_ascii=False)})
		window.run_command('show_panel', {'panel': 'output.qsp_analyzer'})

class QspReplicStructCommand(sublime_plugin.WindowCommand):
	""" Generate folder with md-files as links structure """
	def run(self) -> None:
		...

class QspLocalVarsHighlightCommand(sublime_plugin.TextCommand):
	""" Find and high light local variables command """

	def run(self, edit:sublime.Edit) -> None:
		view = self.view
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		project_folder = QspWorkspace.project_folder(view)
		qsp_ws = QSP_WORKSPACES.get(project_folder) or QspWorkspace(QSP_WORKSPACES)
		qsp_ws.refresh_vars(view)
		view.run_command('qsp_hide_highlight')
		view.add_regions('local_vars', qsp_ws.get_local_vars(), 'region.orangish', flags=256)

class QspGlobalVarsHighlightCommand(sublime_plugin.TextCommand):
	""" Find and high light global variables command """

	def run(self, edit:sublime.Edit) -> None:
		view = self.view
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		project_folder = QspWorkspace.project_folder(view)
		qsp_ws = QSP_WORKSPACES.get(project_folder) or QspWorkspace(QSP_WORKSPACES)
		qsp_ws.refresh_vars(view)
		view.run_command('qsp_hide_highlight')
		view.add_regions('global_vars', qsp_ws.get_global_vars(), 'region.yellowish', flags=256)

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
		all_views = window.views()
		project_folders = window.folders()
		project_folder = (project_folders[0] if project_folders else None)
		qsp_ws = (QSP_WORKSPACES.get(project_folder) or QspWorkspace(QSP_WORKSPACES))
		qsp_ws.refresh_from_views(all_views, project_folders)
		qsp_locs = qsp_ws.locs_dupl()
		popup_msg = ''
		for i, qsp_loc in enumerate(qsp_locs): # int, tuple in list[qsp_loc]
			qsp_loc_name, qsp_loc_region, qsp_loc_place = qsp_loc
			if not isinstance(qsp_loc_place, int) and os.path.isfile(qsp_loc_place):
				count = ''
				with open(qsp_loc_place, 'r', encoding='utf-8') as file:
					string = file.read()
				match = re.search(
					r'^\#\s*'+re.escape(qsp_loc_name)+'$', 
					string, 
					flags=re.MULTILINE)
				if match is not None: count = ':'+str(len(string[:match.start()].split('\n')))
				file_name = os.path.basename(qsp_loc_place)
				popup_msg += f'{i+1}. {qsp_loc_name}. <a href="f:{qsp_loc_place}{count}">'
				popup_msg += f'{file_name}{count}</a><br>'
			elif not isinstance(qsp_loc_place, int) and not os.path.isfile(qsp_loc_place):
				qsp_ws.del_all_locs_by_place(qsp_loc_place)
				continue
			else:
				for v in all_views:
					if v.id() == qsp_loc_place:
						popup_msg += f'{i+1}. {qsp_loc_name}. <a href="v:{v.id()}?'
						popup_msg += f'{qsp_loc_region[0]}">untitled ({v.id()})</a><br>'
						break
		w = view.viewport_extent()[0]/1.5
		vr = view.visible_region().begin()
		view.show_popup(popup_msg, max_width=w, location=vr, on_navigate=self.on_navigate)

	def on_navigate(self, link:str) -> None: # link - relpath or abspath
		window = self.view.window()
		current_view = window.active_view()
		if link.startswith('f:'):
			link = link[2:]
			if current_view is not None and current_view.file_name() == link:
				window.focus_view(current_view)
				point = current_view.text_point(int(link.split(':')[1]), 0)
				current_view.sel().clear()
				current_view.sel().add(sublime.Region(point, point))
			else:
				window.run_command('open_file', {'file': link, 'encoded_position': True})
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
		project_folder = QspWorkspace.project_folder(view)
		if project_folder is None: return None
		qsp_ws = QSP_WORKSPACES.get(project_folder, None)
		if qsp_ws is None: return None
		begin = view.sel()[0].begin()
		end = view.sel()[0].end()
		sr_locname = view.expand_to_scope(begin, 'meta.start_location.qsp')
		sr_lblname = view.expand_to_scope(begin, 'entity.name.qlabel.qsp')
		
		if begin == end and sr_locname is not None:
			input_region = (sr_locname.begin(), sr_locname.end())
			input_text = view.substr(sr_locname)
			current_qsps = view.file_name()
			project_folders = cast(sublime.Window, view.window()).folders()
			if qsp.is_path_in_project_folders(current_qsps, project_folders):
				qsps_file_path = current_qsps
			else:
				qsps_file_path = view.id()
			_filting_qsplocs = (lambda qsp_loc:
				qsp_loc[1] != input_region or qsp_loc[2] != qsps_file_path)
			all_locations = qsp_ws.get_locs()
			all_locations = list(filter(_filting_qsplocs, all_locations))
			loc_names, _, _ = zip(*all_locations) if len(all_locations)>0 else ([], [], [])
			loc_names = list(loc_names)
			if not input_text in loc_names:
				return None
			content = sublime.expand_variables(const.QSP_MSG.WRONG_LOC, {"input_text": input_text})
			view.add_regions('wrong_location', [sr_locname],
				scope="region.redish",
				annotations=[content],
				flags=2048+256+32)
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
					flags=2048+256+32)

class QspAutocomplete(sublime_plugin.EventListener):
	""" Autocomplete and helptips. """

	def on_query_completions(self,
		view:sublime.View,
		prefix:str,
		locations:List[int]) -> Tuple[List[sublime.CompletionItem], sublime.AutoCompleteFlags]:
		""" Append completions in editor."""
		if locations[0]-1 < 0: return None
		if QspWorkspace.view_syntax_is_wrong(view):	return None
		project_folders = view.window().folders()
		project_folder = (project_folders[0] if project_folders else None)
		if project_folder is None: return None # If project is not exist -> completions not work.
		qsp_ws = QSP_WORKSPACES.get(project_folder, None)
		if qsp_ws is None: return None
		qsp_completions = []
		# if syntshugarfunc
		if view.match_selector(locations[0]-1, 'variable.function.qsp'):
			qsp_ws.refresh_from_views(view.window().views(), project_folders)
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
			return (qsp_completions, 24)
		# if calable operator call location
		elif view.match_selector(locations[0]-1, 'callable_locs.qsp'):
			qsp_ws.refresh_from_views(view.window().views(), project_folders)
			qsp_loc_names = qsp_ws.get_locs_names() # -> list of loc names
			scope_region = view.expand_to_scope(locations[0]-1, 'callable_locs.qsp')
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
			return (qsp_completions, 24)
		elif view.match_selector(locations[0]-1, 'label_to_jump.qsp'):
			qsp_all_lbls = QspWorkspace.get_qsplbls(view)
			scope_region = view.expand_to_scope(locations[0]-1, 'label_to_jump.qsp')
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
			return (qsp_completions, 24)
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

class QspWorkspaceHandlers(sublime_plugin.EventListener):
	""" Manage a qsp-workspace in ram and in files """

	_log_it = False

	def _log(self, string:str) -> None:
		if self._log_it:
			log_file = 'D:\\my\\GameDev\\QuestSoftPlayer\\projects\\JAD\\qsp-workspace-log.log'
			with open(log_file, 'a', encoding='utf-8') as fp:
				fp.write(string + '\n')

	def _get_qsp_ws(self, project_folder:str) -> QspWorkspace:
		""" Create qsp workspace or return already exists """
		if project_folder in QSP_WORKSPACES:
			# if ws exist in dict of wss
			qsp_ws = QSP_WORKSPACES[project_folder]
		else:
			# if ws dont exist in dict of wss
			qsp_ws = QSP_WORKSPACES[project_folder] = QspWorkspace(QSP_WORKSPACES)
		return qsp_ws

	def _extract_qsp_ws(self, project_folder:str=None) -> Union[QspWorkspace, None]:
		""" extract ws from file if file is exist, and load in ram """
		self._log('try extract WS from file')
		project_folder = (project_folder or QspWorkspace.current_project_folder())
		if not project_folder: return None
		ws_file_path = os.path.join(project_folder, 'qsp-project-workspace.json')
		if os.path.isfile(ws_file_path):
			# если файл существует, извлекаем из файла ws
			qsp_ws = QSP_WORKSPACES[project_folder] = QspWorkspace(QSP_WORKSPACES)
			qsp_ws.extract_from_file(ws_file_path)
			self._log('extract fin!')
			return qsp_ws
		return None
	
	def _refresh_ws(self, window:sublime.Window) -> None:
		"""
			Refresh workspace if it is exist.
		"""
		folders = window.folders()
		if not folders or len(folders) == 0: return None
		project_folder = folders[0]
		qsp_ws = self._extract_qsp_ws(project_folder) # try to extract workspace from file
		if qsp_ws is not None:
			qsp_ws.refresh_qsps_files(folders)
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

	# When project is closing, set workspace in closing project's status and save WS to file.
	def on_pre_close_project(self, window:sublime.Window) -> None:
		"""
			Event of pre closing the project.
		"""
		project_folder = window.folders()[0]
		if project_folder is None: return None
		qsp_ws = self._get_qsp_ws(project_folder)
		if qsp_ws is None: return None
		qsp_ws.close_project() # set WS in closing project status
		qsp_ws.save_to_file(project_folder) # сохранение при закрытии проекта обязательно

# ----------------------------------- Events of work with project -----------------------------------

# ------------------------------------ Events of work with files ------------------------------------

	# Work with WS in RAM.

	def on_load_async(self, view:sublime.View) -> None:
		"""
			Event of load file (view).
			When file is loading, refresh vars and locs in ws.
		"""
		if QspWorkspace.view_syntax_is_wrong(view): return None
		current_qsps, project_folder = QspWorkspace.get_main_pathes(view)
		if None in (current_qsps, project_folder): return None
		if not qsp.is_path_in_project_folders(current_qsps, view.window().folders()):
			return None
		qsp_ws = self._get_qsp_ws(project_folder)
		qsp_ws.refresh_qsplocs(view, current_qsps)
		qsp_ws.refresh_vars(view)

	def on_pre_close(self, view:sublime.View) -> None:
		"""
			Event of pre close the view.
			Runed before closing the window, if you close window!
		"""
		# TODO: почему-то выполняется после закрывания окна!
		if QspWorkspace.view_syntax_is_wrong(view): return None
		current_qsps, project_folder = QspWorkspace.get_main_pathes(view)
		if project_folder is None: return None
		qsp_ws = self._get_qsp_ws(project_folder)
		if qsp_ws is None or qsp_ws.project_is_closing(): return None # if not WS or project closing!
		folders = view.window().folders()
		# close the untitled view
		if current_qsps is None:
			qsp_ws.del_all_locs_by_place(view.id())
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
		current_qsps, project_folder = QspWorkspace.get_main_pathes(view)
		if None in (current_qsps, project_folder): return None
		qsp_ws = self._get_qsp_ws(project_folder)
		qsp_ws.refresh_qsplocs(view, current_qsps) # TODO: возможно стоит удалить
		if qsp_ws.qsps_file_is_exist(current_qsps):
			qsp_ws.refresh_md5(current_qsps)
		else:
			qsp_ws.add_qsps_file(current_qsps, qsp_ws.get_hash(current_qsps))
		qsp_ws.refresh_from_views(view.window().views(), view.window().folders())

	def on_associate_buffer_async(self, buffer:sublime.Buffer) -> None:
		"""
			This event is runed after renaming or creating a new file.
			refresh files list in workspace
		"""
		if QSP_MARKERS['rename_path']:
			window = buffer.primary_view().window()
			folders = window.folders()
			project_folder = folders[0]
			qsp_ws = self._get_qsp_ws(project_folder)
			qsp_ws.refresh_from_views(window.views(), folders)
			qsp_ws.refresh_qsps_files(folders)
			QSP_MARKERS['rename_path'] = False

# ------------------------------------ Events of work with files ------------------------------------

# ---------------------------------- Events for action recognition ----------------------------------

	def on_window_command(self, window:sublime.Window, command_name:str, args:dict) -> None:
		if command_name in ('rename_path'):
			QSP_MARKERS[command_name] = True
		elif command_name in ('delete_file'):
			QSP_MARKERS['delete_files'] = args['files']

# ---------------------------------- Events for action recognition ----------------------------------


# variables
QSP_WORKSPACES = {} # all qsp WSs add to this dict, if you open project
QSP_MARKERS = {
	# editing files commands and events
	'rename_path': False,
	'delete_files': [],
	'save_log_file': False
}

class QspDeveloperTestCommand(sublime_plugin.WindowCommand):
	""" Testing and proving datas """
	def run(self):
		project_folder = sublime.active_window().folders()[0]
		qsp_ws = QSP_WORKSPACES[project_folder]
		print(qsp_ws.get_locs())
		print(qsp_ws.get_qsps_files())
