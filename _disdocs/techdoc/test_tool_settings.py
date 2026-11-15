import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch


REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / 'QSP.sublime-package'

# Block Sublime imports and bytecode writes even when invoked through discovery.
_old_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
sys.path.insert(0, str(PACKAGE))
try:
    with patch.dict(sys.modules, {'sublime': None, 'sublime_plugin': None}):
        from qSpy import builder, const, function as qsp, plugtypes as ts
        from qSpy.converter import converters
        from qSpy.project import QspProject
finally:
    sys.path.pop(0)
    sys.dont_write_bytecode = _old_bytecode


class TemporaryProjectTestCase(unittest.TestCase):
    def setUp(self):
        original_cwd = os.getcwd()
        temporary = tempfile.TemporaryDirectory(prefix='qsp tool settings ')
        self.addCleanup(temporary.cleanup)
        # QspProject changes cwd; restore it before Windows removes the temp tree.
        self.addCleanup(os.chdir, original_cwd)
        self.root = Path(temporary.name).resolve()
        self.work = self.root / 'project with spaces'
        self.bin = self.root / 'path tools'
        self.home = self.root / 'home'
        for directory in (self.work, self.bin, self.home):
            directory.mkdir()
        environment = {
            'PATH': str(self.bin),
            'PATHEXT': '.EXE;.COM;.BAT;.CMD',
            'HOME': str(self.home),
            'USERPROFILE': str(self.home),
        }
        self.environment = patch.dict(os.environ, environment)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.source = self.work / 'start.qsps'
        self.source.write_text("# start\n*pl 'test'\n--- start\n", encoding='utf-8')
        self.game = self.work / 'game with spaces.qsp'
        self.game.write_bytes(b'')
        self.project_file = self.work / const.PROJECT_FILE_NAME
        self.stdout = io.StringIO()
        capture = contextlib.redirect_stdout(self.stdout)
        capture.__enter__()
        self.addCleanup(capture.__exit__, None, None, None)
        self.log = self.start_patch(patch.object(qsp, 'write_error_log'))
        self.converter_log = self.start_patch(patch.object(converters, 'write_error_log'))
        self.popen = self.start_patch(patch.object(subprocess, 'Popen'))
        self.process_run = self.start_patch(patch.object(
            subprocess, 'run',
            return_value=SimpleNamespace(returncode=0, stdout='', stderr=''),
        ))

    def start_patch(self, patcher):
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def executable(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'not a real executable\n')
        path.chmod(0o755)
        self.assertTrue(os.access(path, os.X_OK))
        return str(path)

    def write_project(self, fields=None):
        data = {
            'project': [{'module': self.game.name, 'files': [{'path': self.source.name}]}],
            'start': self.game.name,
        }
        data.update(fields or {})
        self.project_file.write_text(json.dumps(data), encoding='utf-8')

    def project(self, fields=None, settings=None, mode='--build'):
        self.write_project(fields)
        args = {
            'point_file': str(self.project_file),
            'qsp_mode': mode,
            'player_path': '',
            'converter_path': '',
        }
        args.update(settings or {})
        return QspProject(args, [str(self.work)])

    def assert_builtin(self, project):
        self.assertFalse(project.scheme_is_wrong(), self.stdout.getvalue())
        self.assertEqual(project.get_scheme()['converter'], {
            'capi': 'builtin', 'path': '', 'args': '',
        })

    def assert_paths(self, project, player, converter, params=''):
        self.assertFalse(project.scheme_is_wrong(), self.stdout.getvalue())
        scheme = project.get_scheme()
        self.assertEqual(os.path.normcase(scheme['player']), os.path.normcase(player))
        self.assertEqual(scheme['player_error'], '')
        self.assertEqual(scheme['converter']['capi'], 'outer')
        self.assertEqual(os.path.normcase(scheme['converter']['path']), os.path.normcase(converter))
        self.assertEqual(scheme['converter']['args'], params)


class ProjectSettingsTests(TemporaryProjectTestCase):
    def test_package_defaults_are_empty(self):
        text = (PACKAGE / 'QSP.sublime-settings').read_text(encoding='utf-8')
        settings = json.loads('\n'.join(
            line for line in text.splitlines() if not line.lstrip().startswith('//')
        ))
        self.assertEqual(settings['player_path'], '')
        self.assertEqual(settings['converter_path'], '')

    def test_omitted_settings_do_not_require_sublime_or_bundled_tools(self):
        for platform in ('windows', 'linux', 'osx'):
            with self.subTest(platform=platform):
                with patch.dict(sys.modules, {'sublime': None, 'sublime_plugin': None}):
                    project = QspProject({
                        'point_file': str(self.source), 'platform': platform,
                        'packages_path': str(self.root / 'nonexistent packages'),
                    }, [])
                    self.assert_builtin(project)
                    self.assertEqual(project.get_scheme()['player'], '')
                    self.assertEqual(project.get_scheme()['player_error'], '')
                    builder.BuildQSP(project.get_scheme())
        self.assertEqual(self.stdout.getvalue(), '')
        self.log.assert_not_called()

    def test_empty_defaults_select_builtin_and_no_player(self):
        project = self.project()
        self.assert_builtin(project)
        self.assertEqual(project.get_scheme()['player'], '')
        self.assertEqual(project.get_scheme()['player_error'], '')

    def test_global_absolute_paths_with_spaces(self):
        player = self.executable(self.bin / 'player with spaces.exe')
        converter = self.executable(self.bin / 'converter with spaces.exe')
        project = self.project(settings={'player_path': player, 'converter_path': converter})
        self.assert_paths(project, player, converter)

    def test_global_tilde_uses_temporary_home(self):
        player = self.executable(self.home / 'tools' / 'player.exe')
        converter = self.executable(self.home / 'tools' / 'converter.exe')
        project = self.project(settings={
            'player_path': '~/tools/player.exe', 'converter_path': '~/tools/converter.exe',
        })
        self.assert_paths(project, player, converter)

    def test_global_bare_names_search_actual_path(self):
        player = self.executable(self.bin / 'qsp-test-player.exe')
        converter = self.executable(self.bin / 'qsp-test-converter.exe')
        project = self.project(settings={
            'player_path': Path(player).name, 'converter_path': Path(converter).name,
        })
        self.assert_paths(project, player, converter)

    def test_global_path_search_does_not_implicitly_use_project_directory(self):
        local = self.executable(self.work / 'tool.exe')
        path_tool = self.executable(self.bin / 'tool.exe')
        with patch.dict(os.environ):
            os.environ.pop('NoDefaultCurrentDirectoryInExePath', None)
            project = self.project(settings={'player_path': 'tool.exe', 'converter_path': 'tool.exe'})
            self.assert_paths(project, path_tool, path_tool)
            Path(path_tool).unlink()
            project = self.project(settings={'player_path': 'tool.exe'})
            self.assertFalse(project.scheme_is_wrong())
            self.assertTrue(project.get_scheme()['player_error'])
            self.assertNotEqual(project.get_scheme()['player'], local)

    def test_path_command_without_extension_uses_native_suffix(self):
        name = 'qsp-test-tool'
        filename = name + '.exe' if os.name == 'nt' else name
        tool = self.executable(self.bin / filename)
        project = self.project(settings={'player_path': name, 'converter_path': name})
        self.assert_paths(project, tool, tool)

    def test_global_relative_paths_with_directory_are_rejected_even_if_existing(self):
        self.executable(self.work / 'tools' / 'tool.exe')
        for key in ('player_path', 'converter_path'):
            for value in ('tools/tool.exe', './tools/tool.exe'):
                with self.subTest(key=key, value=value):
                    project = self.project(settings={key: value})
                    if key == 'converter_path':
                        self.assertTrue(project.scheme_is_wrong())
                        self.assertIn('converter_path in QSP.sublime-settings', self.stdout.getvalue())
                    else:
                        self.assertFalse(project.scheme_is_wrong())
                        self.assertEqual(project.get_scheme()['player'], '')
                        self.assertIn('player_path in QSP.sublime-settings',
                                      project.get_scheme()['player_error'])
        self.log.assert_not_called()

    def test_project_relative_paths_are_anchored_to_work_dir(self):
        player = self.executable(self.work / 'tools' / 'player.exe')
        converter = self.executable(self.work / 'tools' / 'converter.exe')
        os.chdir(self.home)
        project = self.project({'player': 'tools/player.exe', 'converter': './tools/converter.exe'})
        self.assertEqual(project.get_work_dir(), str(self.work))
        self.assert_paths(project, player, converter)

    def test_project_existing_bare_file_wins_over_path(self):
        player = self.executable(self.work / 'player.exe')
        converter = self.executable(self.work / 'converter.exe')
        self.executable(self.bin / 'player.exe')
        self.executable(self.bin / 'converter.exe')
        project = self.project({'player': 'player.exe', 'converter': 'converter.exe'})
        self.assert_paths(project, player, converter)

    def test_project_bare_names_fall_back_to_path(self):
        player = self.executable(self.bin / 'player.exe')
        converter = self.executable(self.bin / 'converter.exe')
        project = self.project({'player': 'player.exe', 'converter': 'converter.exe'})
        self.assert_paths(project, player, converter)

    def test_missing_project_relative_paths_do_not_fall_back_to_global_or_path(self):
        tool = self.executable(self.bin / 'tool.exe')
        for key in ('player', 'converter'):
            with self.subTest(key=key):
                project = self.project({key: 'missing/tool.exe'}, {key + '_path': tool})
                if key == 'converter':
                    self.assertTrue(project.scheme_is_wrong())
                else:
                    self.assertFalse(project.scheme_is_wrong())
                    self.assertEqual(project.get_scheme()['player'], '')
                    self.assertIn('player in qsp-project.json', project.get_scheme()['player_error'])

    def test_project_paths_override_valid_global_paths(self):
        local = self.executable(self.work / 'local.exe')
        global_tool = self.executable(self.bin / 'global.exe')
        project = self.project(
            {'player': local, 'converter': local},
            {'player_path': global_tool, 'converter_path': global_tool},
        )
        self.assert_paths(project, local, local)

    def test_project_overrides_ignore_malformed_global_values(self):
        tool = self.executable(self.work / 'local.exe')
        for invalid in (None, False, 42, 1.5, [], [tool, '-x'], {'path': tool}, '\x00'):
            for fields in ({'player': tool, 'converter': tool}, {'player': '', 'converter': ''}):
                with self.subTest(invalid=invalid, fields=fields):
                    project = self.project(fields, {'player_path': invalid, 'converter_path': invalid})
                    if fields['converter']:
                        self.assert_paths(project, tool, tool)
                    else:
                        self.assert_builtin(project)
                        self.assertEqual(project.get_scheme()['player'], '')
                        self.assertEqual(project.get_scheme()['player_error'], '')
        self.assertEqual(self.stdout.getvalue(), '')
        self.log.assert_not_called()

    def test_project_empty_or_builtin_string_overrides_global_converter(self):
        external = self.executable(self.bin / 'converter.exe')
        for value in ('', const.CONVERTER):
            with self.subTest(value=value):
                self.assert_builtin(self.project({'converter': value}, {'converter_path': external}))

    def test_builtin_string_ignores_real_files_with_reserved_name(self):
        self.executable(self.work / const.CONVERTER)
        self.executable(self.bin / const.CONVERTER)
        self.executable(self.bin / (const.CONVERTER + '.exe'))
        external = self.executable(self.bin / 'external.exe')
        self.assert_builtin(self.project({'converter': const.CONVERTER}, {'converter_path': external}))
        self.assert_builtin(self.project(settings={'converter_path': const.CONVERTER}))
        self.process_run.assert_not_called()

    def test_project_converter_array_preserves_one_parameter_string(self):
        converter = self.executable(self.work / 'converter.exe')
        params = '--flag two words "quoted" & literal'
        project = self.project({'converter': ['converter.exe', params]})
        self.assert_paths(project, '', converter, params)

    def test_project_converter_array_with_reserved_filename_stays_external(self):
        converter = self.executable(self.work / const.CONVERTER)
        project = self.project({'converter': [const.CONVERTER, '--literal params']})
        self.assert_paths(project, '', converter, '--literal params')

    def test_project_converter_arrays_require_exactly_two_strings(self):
        converter = self.executable(self.bin / 'converter.exe')
        for value in ([], [converter], [converter, '', 'extra'], [converter, None],
                      [converter, 42], [converter, []], [False, ''], [None, '']):
            with self.subTest(value=value):
                project = self.project({'converter': value}, {'converter_path': converter})
                self.assertTrue(project.scheme_is_wrong())
        self.assertIn('converter in qsp-project.json', self.stdout.getvalue())
        self.process_run.assert_not_called()

    def test_global_converter_rejects_arrays_and_other_nonstring_types(self):
        tool = self.executable(self.bin / 'converter.exe')
        for value in (None, True, False, 42, 1.5, [], [tool, '-x'], (tool, '-x'), {'path': tool}):
            with self.subTest(value=value):
                project = self.project(settings={'converter_path': value})
                self.assertTrue(project.scheme_is_wrong())
        self.assertIn('converter_path in QSP.sublime-settings', self.stdout.getvalue())
        self.process_run.assert_not_called()

    def test_invalid_converter_paths_fail_without_fallback(self):
        for key in ('project', 'global'):
            for value in (str(self.bin / 'missing.exe'), str(self.bin), '\x00', 'not-on-path.exe'):
                with self.subTest(source=key, value=value):
                    project = (self.project({'converter': value}) if key == 'project'
                               else self.project(settings={'converter_path': value}))
                    self.assertTrue(project.scheme_is_wrong())
        self.process_run.assert_not_called()

    def test_invalid_player_is_deferred_without_scheme_error_or_logging(self):
        for source in ('project', 'global'):
            for value in (None, False, 42, 1.5, [], ['tool.exe', '-x'], {}, '\x00',
                          str(self.bin), str(self.bin / 'missing.exe')):
                with self.subTest(source=source, value=value):
                    project = (self.project({'player': value}) if source == 'project'
                               else self.project(settings={'player_path': value}))
                    self.assertFalse(project.scheme_is_wrong())
                    self.assertEqual(project.get_scheme()['player'], '')
                    origin = ('player in qsp-project.json' if source == 'project'
                              else 'player_path in QSP.sublime-settings')
                    self.assertIn(origin, project.get_scheme()['player_error'])
        self.assertEqual(self.stdout.getvalue(), '')
        self.log.assert_not_called()

    @unittest.skipIf(os.name == 'nt', 'Windows does not enforce POSIX executable mode bits')
    def test_nonexecutable_local_file_does_not_fall_back_to_path(self):
        local = Path(self.executable(self.work / 'tool.exe'))
        local.chmod(0o644)
        self.executable(self.bin / 'tool.exe')
        for key in ('player', 'converter'):
            with self.subTest(key=key):
                project = self.project({key: 'tool.exe'})
                if key == 'converter':
                    self.assertTrue(project.scheme_is_wrong())
                else:
                    self.assertFalse(project.scheme_is_wrong())
                    self.assertTrue(project.get_scheme()['player_error'])

    def test_run_mode_ignores_invalid_converter_from_both_sources(self):
        player = self.executable(self.bin / 'player.exe')
        for value in (None, False, [], ['bad'], '\x00', str(self.bin / 'missing.exe')):
            for source in ('project', 'global'):
                with self.subTest(value=value, source=source):
                    fields = {'converter': value} if source == 'project' else {}
                    project = self.project(fields, {'player_path': player, 'converter_path': value}, '--run')
                    self.assert_builtin(project)
                    self.assertEqual(project.get_scheme()['player'], player)
        self.assertEqual(self.stdout.getvalue(), '')
        self.log.assert_not_called()

    def test_macos_requires_contents_macos_binary_not_app_directory(self):
        app = self.bin / 'Player.app'
        executable = self.executable(app / 'Contents' / 'MacOS' / 'player')
        for key in ('player_path', 'converter_path'):
            with self.subTest(key=key):
                invalid = self.project(settings={key: str(app), 'platform': 'osx'})
                if key == 'converter_path':
                    self.assertTrue(invalid.scheme_is_wrong())
                else:
                    self.assertFalse(invalid.scheme_is_wrong())
                    self.assertTrue(invalid.get_scheme()['player_error'])
        project = self.project(settings={
            'platform': 'osx', 'player_path': executable, 'converter_path': executable,
        })
        self.assert_paths(project, executable, executable)
        builder.BuildQSP(project.get_scheme()).run_game()
        self.popen.assert_called_once_with([executable, str(self.game)])

    def test_quick_project_template_inherits_global_tools(self):
        template = dict(const.QSP_PROJECT_JSON)
        self.assertNotIn('player', template)
        self.assertNotIn('converter', template)
        tool = self.executable(self.bin / 'tool.exe')
        project = self.project(template, {'player_path': tool, 'converter_path': tool})
        self.assert_paths(project, tool, tool)


class BuilderSettingsTests(TemporaryProjectTestCase):
    def test_build_with_invalid_player_succeeds_without_player_diagnostic(self):
        project = self.project(settings={'player_path': ['invalid']})
        self.assertFalse(project.scheme_is_wrong())
        self.assertTrue(project.get_scheme()['player_error'])
        builder.BuildQSP(project.get_scheme()).build_project()
        self.assertTrue(self.game.read_bytes().startswith('QSPGAME'.encode('utf-16le')))
        self.assertNotIn('player', self.stdout.getvalue().lower())
        self.log.assert_not_called()
        self.converter_log.assert_not_called()
        self.popen.assert_not_called()
        self.process_run.assert_not_called()

    def test_run_with_deferred_player_error_logs_and_never_spawns(self):
        project = self.project({'player': str(self.bin / 'missing.exe')})
        builder.BuildQSP(project.get_scheme()).run_game()
        self.log.assert_called_once_with('[106] ' + project.get_scheme()['player_error'])
        self.popen.assert_not_called()
        self.process_run.assert_not_called()

    def test_run_without_configured_player_explains_both_setting_sources(self):
        builder.BuildQSP(self.project().get_scheme()).run_game()
        self.log.assert_called_once()
        diagnostic = self.log.call_args.args[0]
        for text in ('[106]', 'player', 'qsp-project.json', 'player_path', 'QSP.sublime-settings'):
            self.assertIn(text, diagnostic)
        self.popen.assert_not_called()

    def test_run_rechecks_player_file_before_spawning(self):
        player = self.executable(self.bin / 'player.exe')
        project = self.project(settings={'player_path': player})
        Path(player).unlink()
        builder.BuildQSP(project.get_scheme()).run_game()
        self.log.assert_called_once()
        self.assertIn('[106]', self.log.call_args.args[0])
        self.popen.assert_not_called()

    def test_run_missing_start_file_never_spawns(self):
        player = self.executable(self.bin / 'player.exe')
        project = self.project(settings={'player_path': player})
        self.game.unlink()
        builder.BuildQSP(project.get_scheme()).run_game()
        self.log.assert_called_once()
        self.assertIn('[107]', self.log.call_args.args[0])
        self.popen.assert_not_called()

    def test_run_uses_argv_not_shell_and_waits_briefly(self):
        player = self.executable(self.bin / 'player with spaces.exe')
        project = self.project(settings={'player_path': player})
        builder.BuildQSP(project.get_scheme()).run_game()
        self.popen.assert_called_once_with([player, str(self.game)])
        self.popen.return_value.wait.assert_called_once_with(0.1)
        self.log.assert_not_called()

    def test_player_timeout_does_not_kill_the_game(self):
        player = self.executable(self.bin / 'player.exe')
        self.popen.return_value.wait.side_effect = subprocess.TimeoutExpired([player], 0.1)
        builder.BuildQSP(self.project(settings={'player_path': player}).get_scheme()).run_game()
        self.popen.return_value.wait.assert_called_once_with(0.1)
        self.popen.return_value.kill.assert_not_called()
        self.popen.return_value.terminate.assert_not_called()
        self.log.assert_not_called()

    def test_external_converter_preserves_argv_and_one_parameter_token(self):
        converter = self.executable(self.work / 'converter with spaces.exe')
        for params in ('', '--flag two words "quoted" & literal'):
            with self.subTest(params=params):
                self.process_run.reset_mock()
                project = self.project({'converter': [converter, params]})
                builder.BuildQSP(project.get_scheme()).build_project()
                argv = [converter, str(self.game.with_suffix('.txt')), str(self.game)]
                if params:
                    argv.append(params)
                self.process_run.assert_called_once_with(argv, capture_output=True, text=True)
                self.assertFalse(self.game.with_suffix('.txt').exists())
        self.popen.assert_not_called()
        self.log.assert_not_called()
        self.converter_log.assert_not_called()


# Compile only the command class, never QSP.py's Sublime/workspace import hooks.
def command_class(name, namespace):
    path = PACKAGE / 'QSP.py'
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == name)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


class BuildCommandSettingsTests(TemporaryProjectTestCase):
    def setUp(self):
        super().setUp()
        self.write_project()
        self.settings = {}
        self.sublime = SimpleNamespace(
            load_settings=Mock(return_value=self.settings),
            platform=Mock(return_value='windows'),
            packages_path=Mock(return_value=str(self.root / 'packages')),
        )
        self.window = SimpleNamespace(
            extract_variables=Mock(return_value={'file': str(self.project_file)}),
            folders=Mock(return_value=[str(self.work)]),
        )
        self.build = Mock(spec=builder.BuildQSP)
        self.build_factory = Mock(return_value=self.build)
        self.project_factory = Mock(wraps=QspProject)
        self.namespace = {
            'os': os, 'ts': ts, 'Path': ts.Path, 'qsp': qsp, 'const': const,
            'sublime': self.sublime,
            'sublime_plugin': SimpleNamespace(WindowCommand=object),
            'QspProject': self.project_factory, 'BuildQSP': self.build_factory,
        }
        self.command = command_class('QspBuildCommand', self.namespace)()
        self.command.window = self.window

    def test_modes_forward_defaults_and_call_only_requested_operations(self):
        for mode, expected in (
            ('--build', [call.build_project()]),
            ('--run', [call.run_game()]),
            ('--br', [call.build_project(), call.run_game()]),
        ):
            with self.subTest(mode=mode):
                self.build.reset_mock()
                self.command.run(mode)
                self.assertEqual(self.build.method_calls, expected)
                args, folders = self.project_factory.call_args.args
                self.assertEqual(args, {
                    'point_file': str(self.project_file), 'qsp_mode': mode,
                    'platform': 'windows', 'packages_path': str(self.root / 'packages'),
                    'player_path': '', 'converter_path': '',
                })
                self.assertEqual(folders, [str(self.work)])
        self.assertEqual(self.sublime.load_settings.call_args_list,
                         [call('QSP.sublime-settings')] * 3)
        self.log.assert_not_called()

    def test_default_mode_builds_then_runs(self):
        self.command.run()
        self.assertEqual(self.build.method_calls, [call.build_project(), call.run_game()])
        self.assertEqual(self.project_factory.call_args.args[0]['qsp_mode'], '--br')

    def test_runtime_setting_changes_are_read_each_invocation(self):
        first = self.executable(self.bin / 'first.exe')
        second = self.executable(self.bin / 'second.exe')
        self.settings.update(player_path=first, converter_path=first)
        self.command.run('--build')
        first_scheme = self.build_factory.call_args.args[0]
        self.sublime.load_settings.return_value = {'player_path': second, 'converter_path': second}
        self.command.run('--build')
        second_scheme = self.build_factory.call_args.args[0]
        self.assertEqual(first_scheme['player'], first)
        self.assertEqual(first_scheme['converter']['path'], first)
        self.assertEqual(second_scheme['player'], second)
        self.assertEqual(second_scheme['converter']['path'], second)
        self.assertEqual(self.sublime.load_settings.call_args_list, [call('QSP.sublime-settings')] * 2)

    def test_raw_malformed_settings_are_passed_through_for_project_override(self):
        tool = self.executable(self.work / 'local.exe')
        self.write_project({'player': tool, 'converter': tool})
        self.settings.update(player_path=['not a global path'], converter_path={'invalid': True})
        self.command.run('--build')
        args = self.project_factory.call_args.args[0]
        self.assertIs(args['player_path'], self.settings['player_path'])
        self.assertIs(args['converter_path'], self.settings['converter_path'])
        scheme = self.build_factory.call_args.args[0]
        self.assertEqual(scheme['player'], tool)
        self.assertEqual(scheme['converter']['path'], tool)
        self.build.build_project.assert_called_once_with()
        self.log.assert_not_called()

    def test_invalid_converter_aborts_build_modes_before_builder_creation(self):
        self.settings['converter_path'] = ['invalid global array', '-x']
        for mode in ('--build', '--br'):
            with self.subTest(mode=mode):
                self.log.reset_mock()
                self.command.run(mode)
                self.build_factory.assert_not_called()
                self.log.assert_called_once_with(const.QSP_ERROR_MSG.EMPTY_PROJECT)
        self.popen.assert_not_called()
        self.process_run.assert_not_called()

    def test_run_mode_does_not_validate_or_use_converter(self):
        self.settings['converter_path'] = ['invalid']
        self.write_project({'converter': None})
        self.command.run('--run')
        self.assertEqual(self.build.method_calls, [call.run_game()])
        self.log.assert_not_called()
        self.assertEqual(self.stdout.getvalue(), '')

    def test_build_mode_defers_invalid_player_without_diagnostic(self):
        self.settings['player_path'] = {'invalid': True}
        self.command.run('--build')
        self.assertTrue(self.build_factory.call_args.args[0]['player_error'])
        self.assertEqual(self.build.method_calls, [call.build_project()])
        self.log.assert_not_called()
        self.assertEqual(self.stdout.getvalue(), '')

    def test_build_oserror_aborts_before_running_or_saving_project(self):
        with patch.object(QspProject, 'save_json') as save:
            for error in (FileNotFoundError('converter disappeared'), PermissionError('access denied')):
                with self.subTest(error=error):
                    self.build.reset_mock()
                    self.log.reset_mock()
                    self.build.build_project.side_effect = error
                    self.command.run('--br')
                    self.assertEqual(self.build.method_calls, [call.build_project()])
                    self.log.assert_called_once_with(f'[QSP] Build/run failed: {error}')
                    save.assert_not_called()
        self.popen.assert_not_called()

    def test_run_oserror_is_reported(self):
        error = OSError('player failed to start')
        self.build.run_game.side_effect = error
        self.command.run('--run')
        self.assertEqual(self.build.method_calls, [call.run_game()])
        self.log.assert_called_once_with(f'[QSP] Build/run failed: {error}')

    def test_real_converter_spawn_oserror_prevents_game_launch(self):
        converter = self.executable(self.bin / 'converter.exe')
        player = self.executable(self.bin / 'player.exe')
        self.settings.update(converter_path=converter, player_path=player)
        self.namespace['BuildQSP'] = builder.BuildQSP
        self.process_run.side_effect = OSError('converter spawn failed')
        self.command.run('--br')
        self.process_run.assert_called_once()
        self.popen.assert_not_called()
        self.log.assert_called_once_with('[QSP] Build/run failed: converter spawn failed')

    def test_direct_single_file_conversion_remains_builtin_and_ignores_settings(self):
        builtin = Mock()
        self.namespace['QspsToQspBuiltinConv'] = builtin
        direct = command_class('QspsToQspCommand', self.namespace)()
        direct.window = self.window
        self.settings.update(player_path=['invalid'], converter_path=['invalid'])
        for extension in ('qsps', 'qsp-txt', 'txt-qsp'):
            with self.subTest(extension=extension):
                builtin.reset_mock()
                source = self.work / ('single file.' + extension)
                source.write_text(self.source.read_text(encoding='utf-8'), encoding='utf-8')
                self.window.extract_variables.return_value = {
                    'file': str(source), 'file_extension': extension,
                }
                direct.run()
                output = str(source.with_suffix('.qsp'))
                builtin.assert_called_once_with(output, False)
                builtin.return_value.convert_file.assert_called_once_with(str(source), output)
        self.sublime.load_settings.assert_not_called()
        self.project_factory.assert_not_called()
        self.build_factory.assert_not_called()
        self.popen.assert_not_called()
        self.process_run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
