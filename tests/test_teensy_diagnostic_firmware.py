import pathlib
import subprocess
import tempfile
import unittest

FIXTURE = pathlib.Path(__file__).parent / 'teensy_diag_fixture'

class FirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.binaries = {}
        for mode, flags in [('legacy', []), ('diag', ['-DUSB_DUAL_SERIAL'])]:
            binary = pathlib.Path(cls.temp.name) / (mode + '.exe')
            command = ['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', *flags,
                       '-I', str(FIXTURE), str(FIXTURE / 'test_firmware.cpp'), '-o', str(binary)]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            cls.binaries[mode] = binary

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_scenario(self, scenario, mode='diag'):
        result = subprocess.run([str(self.binaries[mode]), scenario], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_legacy_protocol(self): self.run_scenario('legacy', 'legacy')
    def test_diagnostic_protocol(self): self.run_scenario('protocol')
    def test_heartbeat(self): self.run_scenario('heartbeat')
    def test_closed_full_port(self): self.run_scenario('skip')
    def test_actual_short_returns(self): self.run_scenario('short')
    def test_failed_usb_returns(self): self.run_scenario('failure')
    def test_timeout_garbage(self): self.run_scenario('timeout')
    def test_interrupt_and_timestamp_rollover(self): self.run_scenario('irq_wrap')
    def test_counter_wrap_and_max_csv(self): self.run_scenario('counter_wrap')
