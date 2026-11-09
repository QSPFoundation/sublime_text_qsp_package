import sublime  # type: ignore

from typing import List, Literal, Tuple, TypedDict, cast

Point = int

class FindOverlapMb(TypedDict):
	separator_name: List[Literal['assign', 'while', 'brace']]
	separator_region: List[sublime.Region]
	separator_instr: List[Point]


def scan_vars(view: sublime.View) -> Tuple[List[sublime.Region], List[sublime.Region]]:
	""" Скан регионов локальных/глобальных пользовательских переменных в одном вью (4.5).
		Чистая функция без состояния: регионы не хранятся в WS (2.4). """
	def _find_overlap_main(start_find: int):
		maximal = view.size() + 1
		mini_data_base: FindOverlapMb = {
			"separator_name": [
				'assign',
				'while',
				'brace'
			],
			"separator_region":
			[
				view.find('=', start_find, flags=sublime.LITERAL | sublime.IGNORECASE),
				view.find('while', start_find, flags=sublime.LITERAL | sublime.IGNORECASE),
				view.find('}', start_find, flags=sublime.LITERAL | sublime.IGNORECASE)
			],
			"separator_instr":
			[]
		}
		for i, _ in enumerate(mini_data_base['separator_name']):
			region = mini_data_base['separator_region'][i]
			mini_data_base['separator_instr'].append(
				region.begin() if region.begin() != -1 else maximal)
		minimal = min(mini_data_base['separator_instr'])
		if minimal != maximal:
			i = mini_data_base['separator_instr'].index(minimal)
			sprtr_type = mini_data_base['separator_name'][i]
			sprtr_region = mini_data_base['separator_region'][i]
			return sprtr_type, sprtr_region
		else:
			return None, None

	def _safe_f(x: str, y: sublime.Region, z: Point) -> bool:
		""" Selector, """
		return view.match_selector(y.begin(), x) and y.begin() < z

	kw_regions = view.find_all('local', flags=sublime.IGNORECASE)
	vars_regions: List[sublime.Region] = []

	for r in kw_regions:
		if not view.match_selector(r.begin(), 'keyword.declaration.variables.qsp'):
			continue
		# not use 'local' in string and comment scopes
		start_region = r.end()
		end_line = view.line(r).end()
		end_region = end_line
		start_find = start_region
		while start_find < end_line:
			sprtr_type, sprtr_region = _find_overlap_main(start_find)
			if sprtr_type == 'assign':
				if _safe_f('keyword.operator.one-sign.qsp', cast(sublime.Region, sprtr_region), end_line):
					end_region = sprtr_region.begin() - 1
					break
				else:
					start_find = sprtr_region.end()
			elif sprtr_type == 'while':
				if _safe_f('keyword.control.qsp', cast(sublime.Region, sprtr_region), end_line):
					end_region = sprtr_region.begin() - 1
					break
				else:
					start_find = sprtr_region.end()
			elif sprtr_type == 'brace':
				if _safe_f('avs_brace_end', cast(sublime.Region, sprtr_region), end_line):
					end_region = sprtr_region.begin() - 1
					break
				else:
					start_find = sprtr_region.end()
			else:
				end_region = end_line
				break
		vars_regions.append(sublime.Region(start_region, end_region))
	if len(vars_regions) == 0:
		return [], []

	user_variable = r'\$?[A-Za-zА-Яа-я_][\w\.]*'
	start_point = vars_regions[0].begin()
	edge_point = vars_regions[0].end()
	end_point = vars_regions[-1].end()
	i = 1
	local_vars: List[sublime.Region] = []
	# 2.3: без искусственного потолка итераций — естественная остановка по границам/неудачному find
	while start_point < end_point:
		find_var = view.find(user_variable, start_point, flags=sublime.IGNORECASE)
		if find_var.begin() == -1:
			break
		if find_var.begin() < edge_point:
			for var in view.find_all(view.substr(find_var).replace('$', r'\$') + r'\b', flags=sublime.IGNORECASE):
				if not find_var.begin() > var.begin() and view.match_selector(var.begin(), 'meta.user-variables.qsp'):
					local_vars.append(var)
		start_point = find_var.end() + 1
		if start_point > edge_point:
			if i < len(vars_regions):
				start_point = vars_regions[i].begin()
				edge_point = vars_regions[i].end()
				i += 1
			else:
				break
	global_vars: List[sublime.Region] = []
	for var in view.find_all(user_variable, flags=sublime.IGNORECASE):
		if not var in local_vars and view.match_selector(var.begin(), 'meta.user-variables.qsp'):
			global_vars.append(var)
	return local_vars, global_vars
