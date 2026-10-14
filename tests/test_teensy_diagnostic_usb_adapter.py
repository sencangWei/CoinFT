import pathlib
import subprocess
import tempfile
import unittest
import importlib.util
import hashlib

SDK = pathlib.Path.home() / '.platformio/packages/framework-arduinoteensy/cores/teensy4/usb_serial2.c'
FIXTURE = pathlib.Path(__file__).parent / 'teensy_diag_fixture'
ADAPTER = pathlib.Path(__file__).resolve().parents[1] / 'firmware/teensy/scripts/diag_usb_nonblocking.py'

def load_adapter():
    spec = importlib.util.spec_from_file_location('adapter', ADAPTER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def functions(source):
    start = source.index(b'int usb_serial2_write(const void *buffer, uint32_t size)\n')
    end = source.index(b'void usb_serial2_flush_output(void)\n', start)
    callback_start = source.index(b'static void usb_serial2_flush_callback(void)\n{', end)
    callback_end = source.index(b'\n#endif', callback_start)
    return source[start:end] + source[callback_start:callback_end]

class UsbAdapterTests(unittest.TestCase):
    def run_scenario(self, scenario):
        with tempfile.TemporaryDirectory() as directory:
            work = pathlib.Path(directory)
            (work / 'usb_functions.inc').write_bytes(functions(load_adapter().transform(SDK.read_bytes())))
            binary = work / 'adapter.exe'
            result = subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-I', str(work),
                                     str(FIXTURE / 'test_usb_adapter.cpp'), '-o', str(binary)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = subprocess.run([str(binary), scenario], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_busy_head_never_yields(self): self.run_scenario('busy')
    def test_rejects_without_prefix_or_flag_changes(self): self.run_scenario('reject')
    def test_ready_exact_bytes_timer_and_flag(self): self.run_scenario('ready')
    def test_exact_full_wrap_dma_timer(self): self.run_scenario('full')
    def test_expiry_during_success_is_rearmed(self): self.run_scenario('expiry_success')
    def test_expiry_during_capacity_is_rearmed(self): self.run_scenario('expiry_capacity')
    def test_expiry_during_rejection_is_rearmed(self): self.run_scenario('expiry_reject')

    def test_guard_and_untouched_regions(self):
        adapter = load_adapter()
        source = SDK.read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest().upper(), adapter.UPSTREAM_SHA256)
        output = adapter.transform(source)
        start = source.index(adapter.WRITE_ANCHOR)
        end = source.index(adapter.END_ANCHOR)
        self.assertEqual(output[:start], source[:start])
        self.assertEqual(output[output.index(adapter.END_ANCHOR):], source[end:])
        for invalid in (source + b' ', source.replace(adapter.WRITE_ANCHOR, b''), source + adapter.FREE_ANCHOR):
            with self.assertRaises(ValueError): adapter.transform(invalid)
        self.assertEqual(SDK.read_bytes(), source)
