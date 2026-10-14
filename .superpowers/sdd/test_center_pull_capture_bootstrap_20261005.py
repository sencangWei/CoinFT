"""Verify the capture script's real CLI import prefix without hardware or HTTP."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('capture_center_pull_full_diagnostic_20261005.py')


class BootstrapTests(unittest.TestCase):
    def test_nested_entrypoint_resolves_real_project_capture_module(self):
        probe = '''import ast,sys
from pathlib import Path
script=Path(sys.argv[1])
sys.path[0]=str(script.parent)
tree=ast.parse(script.read_text(encoding='utf-8'))
prefix=[]
for node in tree.body:
    if isinstance(node,ast.FunctionDef):
        break
    prefix.append(node)
namespace={'__file__':str(script),'__name__':'bootstrap_probe'}
exec(compile(ast.Module(body=prefix,type_ignores=[]),str(script),'exec'),namespace)
capture=namespace['capture']
assert callable(capture) and capture.__module__=='calibration.capture_demo_pose'
print('real capture import OK; no capture or device call performed')
'''
        with tempfile.TemporaryDirectory() as task_dir:
            result = subprocess.run([sys.executable, '-X', 'utf8', '-c', probe, str(SCRIPT)],
                                    cwd=task_dir, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('real capture import OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
