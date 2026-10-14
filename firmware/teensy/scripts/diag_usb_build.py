"""Project-local middleware; installed Teensy SDK remains untouched."""
from pathlib import Path
import importlib.util

Import('env')

if env['PIOENV'] != 'teensy40_diag':
    raise RuntimeError('CDC2 adaptation is restricted to teensy40_diag')

scripts = Path(env.subst('$PROJECT_DIR')) / 'scripts'
adapter_path = scripts / 'diag_usb_nonblocking.py'
spec = importlib.util.spec_from_file_location('diag_usb_nonblocking', adapter_path)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
core = Path(env.PioPlatform().get_package_dir('framework-arduinoteensy')) / 'cores' / 'teensy4'
upstream = core / 'usb_serial2.c'
# Validate even when SCons would otherwise consider a generated target current.
adapter.transform(upstream.read_bytes())
env.Append(CPPPATH=[str(core)])

def generate(target, source, env):
    destination = Path(target[0].get_abspath())
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(adapter.transform(Path(source[0].get_abspath()).read_bytes()))

def substitute(build_env, node):
    if Path(node.srcnode().get_abspath()).resolve() != upstream.resolve():
        return node
    generated = build_env.Command(
        str(Path(build_env.subst('$BUILD_DIR')) / 'diag_sdk' / 'usb_serial2.c'),
        str(upstream), generate)[0]
    build_env.Depends(generated, str(adapter_path))
    print('Diagnostic CDC2 source substitute: ' + generated.get_abspath())
    return generated

env.AddBuildMiddleware(substitute)
