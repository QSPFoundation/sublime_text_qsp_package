"""Автотесты логики ядра QSP (конвертер, билдер, воркспейс).

Запуск вне поставки пакета:
    python -B _disdocs/techdoc/test_core_logic.py
"""
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch
import unittest

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / 'QSP.sublime-package'

# Блокируем запись байткода и импорты Sublime.
_old_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
sys.path.insert(0, str(PACKAGE))


# ---------------------------------------------------------------------------
# Fake sublime — позволяет импортировать qSpy.workspace и тестировать его без ST.
# ---------------------------------------------------------------------------
class _FakeSettings:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = dict(data)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeWindow:
    def __init__(self, wid: int) -> None:
        self.id = lambda: wid
        self._folders: List[str] = []
        self._project_file: str = ''

    def folders(self) -> List[str]:
        return list(self._folders)

    def project_file_name(self) -> str:
        return self._project_file


class _FakeView:
    def __init__(self, vid: int, file_name: str = '', syntax_name: str = 'QSP') -> None:
        self.id = lambda: vid
        self._file_name = file_name
        self._syntax_name = syntax_name

    def file_name(self) -> str:
        return self._file_name

    def syntax(self) -> Any:
        class _Syn:
            name = self._syntax_name
        return _Syn()

    def symbol_regions(self) -> List[Any]:
        return []


class FakeSublime:
    class Window:
        pass

    class View:
        pass

    class Region:
        def __init__(self, a: int, b: int) -> None:
            self.a = a
            self.b = b

    def __init__(self, cache_dir: str) -> None:
        self._cache_dir = cache_dir
        self._settings: Dict[str, Dict[str, Any]] = {
            'QSP.sublime-settings': {'player_path': '', 'converter_path': ''},
        }
        self._windows: List[_FakeWindow] = []
        self._project_history: List[Any] = []
        self._next_wid = 1

    def cache_path(self) -> str:
        return self._cache_dir

    def load_settings(self, base_name: str) -> _FakeSettings:
        return _FakeSettings(self._settings.get(base_name, {}))

    def project_history(self) -> List[Any]:
        return list(self._project_history)

    def windows(self) -> List[_FakeWindow]:
        return list(self._windows)

    def new_window(self) -> _FakeWindow:
        wid = self._next_wid
        self._next_wid += 1
        w = _FakeWindow(wid)
        self._windows.append(w)
        return w


_fake = None


def _install_fake(cache_dir: str) -> FakeSublime:
    global _fake
    _fake = FakeSublime(cache_dir)
    fake_modules = {
        'sublime': _fake,
        'sublime_plugin': MagicMock(),
    }
    for name, mod in fake_modules.items():
        sys.modules[name] = mod
    return _fake


try:
    _install_fake(tempfile.mkdtemp(prefix='qsp-core-tests-sublime-cache-'))
    from qSpy.converter.converters import QspsToQspBuiltinConv, QspsToQspOuterConv
    from qSpy.converter.qsps_file import QspsFile
    from qSpy.workspace import QspWorkspace, cache_file_path, WS_VERSION, ORPHAN_MAX_AGE_DAYS, PRUNE_INTERVAL_DAYS
    from qSpy.builder import BuildQSP
    from qSpy import const, function as qsp, plugtypes as ts
finally:
    sys.path.pop(0)
    sys.dont_write_bytecode = _old_bytecode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_qsps(path: Path, locations: List[str]) -> None:
    """Записать .qsps-файл с заданными локациями (каждая — строка '# имя ... --')."""
    lines: List[str] = []
    for loc in locations:
        lines.append(f'# {loc}\n')
        lines.append('*pl \'test\'\n')
        lines.append(f'-- {loc}\n')
    path.write_text(''.join(lines), encoding='utf-8')


def _make_scheme(tmp: Path, modules: List[Dict[str, Any]]) -> ts.ProjectScheme:
    """Собрать ProjectScheme для BuildQSP из списка модулей."""
    project: List[ts.QspModule] = []
    for m in modules:
        project.append({
            'module': str((tmp / m['output']).resolve()),
            'folders': [{'path': str((tmp / m['folder']).resolve())}] if m.get('folder') else [],
            'files': [{'path': str((tmp / m['file']).resolve())}] if m.get('file') else [],
            'start_qsploc_file': '',
        })
    start = str((tmp / modules[0]['output']).resolve()) if modules else ''
    scheme: ts.ProjectScheme = {
        'project': project,
        'start': start,
        'converter': {'capi': 'builtin', 'path': '', 'args': ''},
        'player': '',
        'player_error': '',
        'save_temp_files': False,
        'preprocessor': 'Off',
        'assets': [],
        'scans': {},
    }
    return scheme


# ---------------------------------------------------------------------------
# Converter tests
# ---------------------------------------------------------------------------

class ConverterBuiltinTests(unittest.TestCase):
    def _enc(self, s: str) -> str:
        return QspsToQspBuiltinConv.encode_qsps_line(s)

    def test_encode_qsps_line_shifts_chars(self) -> None:
        from qSpy.converter.converters import QSP_CODREMOV
        encoded = QspsToQspBuiltinConv.encode_qsps_line('ABC')
        expected = ''.join(chr(ord(ch) - QSP_CODREMOV) for ch in 'ABC')
        self.assertEqual(encoded, expected)

    def test_convert_lines_single_location(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix='qsp-conv-test-'))
        out = tmp / 'out.qsp'
        qsps_lines = [
            '# loc1\n',
            '*pl \'hello\'\n',
            '-- loc1\n',
        ]
        conv = QspsToQspBuiltinConv(str(out), False)
        result = conv.convert_lines(qsps_lines)
        conv.save_to_file()
        self.assertTrue(out.is_file())
        data = out.read_text(encoding='utf-16le', newline='')
        self.assertTrue(data.startswith('QSPGAME\r\n'))
        self.assertIn(self._enc('loc1'), data)

    def test_convert_lines_multiple_locations(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix='qsp-conv-test-'))
        out = tmp / 'out.qsp'
        qsps_lines = [
            '# loc1\n',
            '*pl \'a\'\n',
            '-- loc1\n',
            '# loc2\n',
            '*pl \'b\'\n',
            '-- loc2\n',
        ]
        conv = QspsToQspBuiltinConv(str(out), False)
        result = conv.convert_lines(qsps_lines)
        conv.save_to_file()
        data = out.read_text(encoding='utf-16le', newline='')
        self.assertIn(self._enc('loc1'), data)
        self.assertIn(self._enc('loc2'), data)
        self.assertEqual(data.count('QSPGAME'), 1)

    def test_convert_file_reads_and_writes(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix='qsp-conv-file-test-'))
        src = tmp / 'src.qsps'
        _write_qsps(src, ['locA'])
        out = tmp / 'out.qsp'
        conv = QspsToQspBuiltinConv(str(out), False)
        conv.convert_file(str(src), str(out))
        self.assertTrue(out.is_file())
        data = out.read_text(encoding='utf-16le', newline='')
        self.assertIn(self._enc('locA'), data)

    def test_save_to_file_uses_crlf_and_utf16le(self) -> None:
        tmp = Path(tempfile.mkdtemp(prefix='qsp-crlf-test-'))
        out = tmp / 'out.qsp'
        conv = QspsToQspBuiltinConv(str(out), False)
        conv.convert_lines(['# loc\n', '*pl \'x\'\n', '-- loc\n'])
        conv.save_to_file()
        raw = out.read_bytes()
        self.assertIn('\r\n'.encode('utf-16le'), raw)
        self.assertTrue(raw.startswith('QSPGAME'.encode('utf-16le')))


# ---------------------------------------------------------------------------
# Workspace tests
# ---------------------------------------------------------------------------

class WorkspaceCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='qsp-ws-test-'))
        self.cache_dir = str(self.tmp / 'cache')
        _install_fake(self.cache_dir)
        os.makedirs(self.cache_dir, exist_ok=True)
        self.identity = str((self.tmp / 'project.sublime-project').resolve())
        self.cache_path = cache_file_path(self.identity)

    def _write_cache(self, data: Dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, 'w', encoding='utf-8') as fp:
            json.dump(data, fp, ensure_ascii=False, indent=4)

    def _make_ws(self) -> QspWorkspace:
        ws = QspWorkspace(identity=self.identity, scope=[str(self.tmp)])
        return ws

    def test_load_from_cache_valid_v2(self) -> None:
        # Создаём живой файл, чтобы кэш принял его пути.
        live_file = self.tmp / 'live.qsps'
        live_file.write_text('# live\n-- live\n', encoding='utf-8')
        md5 = hashlib.md5(live_file.read_bytes()).hexdigest()
        stat = os.stat(live_file)
        data = {
            'version': WS_VERSION,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': True,
            'files': {
                str(live_file): {
                    'mtime': stat.st_mtime,
                    'size': stat.st_size,
                    'md5': md5,
                },
            },
            'locations': {
                str(live_file): [
                    ['live', [0, 10]],
                ],
            },
        }
        self._write_cache(data)
        ws = self._make_ws()
        ok = ws.load_from_cache()
        self.assertTrue(ok)
        self.assertTrue(ws.qsps_file_is_exist(str(live_file)))
        locs = ws.get_locs_names()
        self.assertIn('live', locs)

    def test_load_from_cache_root_not_dict(self) -> None:
        self._write_cache([1, 2, 3])
        ws = self._make_ws()
        self.assertFalse(ws.load_from_cache())

    def test_load_from_cache_wrong_version(self) -> None:
        data = {
            'version': 99,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': True,
            'files': {},
            'locations': {},
        }
        self._write_cache(data)
        ws = self._make_ws()
        self.assertFalse(ws.load_from_cache())

    def test_load_from_cache_not_built(self) -> None:
        data = {
            'version': WS_VERSION,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': False,
            'files': {},
            'locations': {},
        }
        self._write_cache(data)
        ws = self._make_ws()
        self.assertFalse(ws.load_from_cache())

    def test_load_from_cache_files_not_dict(self) -> None:
        data = {
            'version': WS_VERSION,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': True,
            'files': ['not', 'a', 'dict'],
            'locations': {},
        }
        self._write_cache(data)
        ws = self._make_ws()
        self.assertFalse(ws.load_from_cache())

    def test_load_from_cache_locations_not_dict(self) -> None:
        data = {
            'version': WS_VERSION,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': True,
            'files': {},
            'locations': ['not', 'a', 'dict'],
        }
        self._write_cache(data)
        ws = self._make_ws()
        self.assertFalse(ws.load_from_cache())

    def test_load_from_cache_dead_paths_dropped(self) -> None:
        dead_file = str(self.tmp / 'does_not_exist.qsps')
        data = {
            'version': WS_VERSION,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': True,
            'files': {
                dead_file: {'mtime': 1.0, 'size': 1, 'md5': 'abc'},
            },
            'locations': {
                dead_file: [['ghost', [0, 5]]],
            },
        }
        self._write_cache(data)
        ws = self._make_ws()
        ok = ws.load_from_cache()
        self.assertTrue(ok)
        self.assertFalse(ws.qsps_file_is_exist(dead_file))
        self.assertNotIn('ghost', ws.get_locs_names())

    def test_load_from_cache_bad_region_skipped(self) -> None:
        live_file = self.tmp / 'live2.qsps'
        live_file.write_text('# live2\n-- live2\n', encoding='utf-8')
        md5 = hashlib.md5(live_file.read_bytes()).hexdigest()
        stat = os.stat(live_file)
        data = {
            'version': WS_VERSION,
            'identity': self.identity,
            'scope': [str(self.tmp)],
            'built': True,
            'files': {
                str(live_file): {'mtime': stat.st_mtime, 'size': stat.st_size, 'md5': md5},
            },
            'locations': {
                str(live_file): [
                    ['good', [0, 5]],
                    ['bad1', [0]],               # не список из 2
                    ['bad2', [0, 5, 9]],         # не список из 2
                    ['bad3', ['a', 'b']],        # не int
                    ['bad4', 'not-a-list'],      # не список
                ],
            },
        }
        self._write_cache(data)
        ws = self._make_ws()
        ok = ws.load_from_cache()
        self.assertTrue(ok)
        names = ws.get_locs_names()
        self.assertIn('good', names)
        self.assertNotIn('bad1', names)
        self.assertNotIn('bad2', names)
        self.assertNotIn('bad3', names)
        self.assertNotIn('bad4', names)

    def test_cache_payload_structure(self) -> None:
        ws = self._make_ws()
        payload = ws.cache_payload()
        self.assertEqual(payload['version'], WS_VERSION)
        self.assertEqual(payload['identity'], self.identity)
        self.assertEqual(payload['built'], False)
        self.assertEqual(payload['scope'], [str(self.tmp)])
        self.assertEqual(payload['files'], {})
        self.assertEqual(payload['locations'], {})


# ---------------------------------------------------------------------------
# Builder tests
# ---------------------------------------------------------------------------

class BuilderTests(unittest.TestCase):
    def _enc(self, s: str) -> str:
        return QspsToQspBuiltinConv.encode_qsps_line(s)

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix='qsp-build-test-'))
        self.work = self.tmp / 'project'
        self.work.mkdir()
        self.src_folder = self.work / 'src'
        self.src_folder.mkdir()
        _write_qsps(self.src_folder / 'game.qsps', ['level1', 'level2'])

    def test_build_single_module_from_folder(self) -> None:
        out = self.work / 'game.qsp'
        scheme = _make_scheme(self.work, [{
            'output': 'game.qsp',
            'folder': 'src',
        }])
        builder = BuildQSP(scheme)
        builder.build_project()
        self.assertTrue(out.is_file())
        data = out.read_text(encoding='utf-16le', newline='')
        self.assertIn(self._enc('level1'), data)
        self.assertIn(self._enc('level2'), data)

    def test_build_single_module_from_file(self) -> None:
        src_file = self.src_folder / 'single.qsps'
        _write_qsps(src_file, ['onlyone'])
        out = self.work / 'single.qsp'
        scheme = _make_scheme(self.work, [{
            'output': 'single.qsp',
            'file': 'src/single.qsps',
        }])
        builder = BuildQSP(scheme)
        builder.build_project()
        self.assertTrue(out.is_file())
        data = out.read_text(encoding='utf-16le', newline='')
        self.assertIn(self._enc('onlyone'), data)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main()
