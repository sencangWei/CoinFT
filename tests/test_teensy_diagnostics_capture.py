import contextlib
import importlib
import io
import json
import sys
import types
import unittest
from unittest.mock import patch

try:
    observer = importlib.import_module('capture_teensy_diagnostics')
except ModuleNotFoundError as exc:
    if exc.name != 'capture_teensy_diagnostics':
        raise
    observer = None

NAMES = ('seq', 'uptime_ms', 'loop_count', 'uart_bytes', 'rx_data_reads',
         'rx_payload_bytes', 'rx_end_markers', 'rx_end_timeouts',
         'timer_ticks', 'usb_attempts', 'usb_accepted_bytes',
         'start_commands', 'stop_commands')


def heartbeat(values=range(13), ending=b'\n'):
    return b'CFD1,' + ','.join(map(str, values)).encode('ascii') + ending


class Transport:
    def __init__(self, chunks=(), error=None):
        self.chunks = iter(chunks)
        self.error = error
        self.opens = []
        self.read_sizes = []
        self.dtr = False
        self.closed = False

    def Serial(self, *args, **kwargs):
        self.opens.append((args, kwargs))
        if self.error:
            raise self.error
        return self

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def read(self, size):
        self.read_sizes.append(size)
        return next(self.chunks, b'')


class ObserverTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(observer, 'read-only diagnostic observer is missing')

    @contextlib.contextmanager
    def external(self, transport):
        tick = iter(i / 10 for i in range(1000))
        with patch.dict(sys.modules, serial=types.SimpleNamespace(Serial=transport.Serial)), \
                patch.object(observer.time, 'monotonic', side_effect=lambda: next(tick)), \
                patch.object(observer.time, 'time', side_effect=range(100, 200)):
            yield

    def test_valid_lf_crlf_and_uint32(self):
        self.assertEqual(observer.FIELD_NAMES, NAMES)
        for ending in (b'\n', b'\r\n'):
            self.assertEqual(observer.parse_heartbeat(heartbeat(ending=ending)), dict(zip(NAMES, range(13))))
        self.assertEqual(observer.parse_heartbeat(heartbeat([4294967295] * 13))['seq'], 4294967295)

    def test_rejects_malformed_records(self):
        valid = heartbeat()
        invalid = [valid.replace(b'CFD1', b'CFD2'), heartbeat(range(12)), heartbeat(range(14)),
                   valid.replace(b',0,', b',-1,'), valid.replace(b',0,', b',+1,'),
                   valid.replace(b',0,', b',a,'), valid.replace(b',0,', b', 0,'),
                   valid.replace(b',0,', b',4294967296,'), valid.replace(b',0,', b',\xff,'),
                   valid[:-1], valid + b'\n', heartbeat(['0' * 163] + [0] * 12)]
        for line in invalid:
            with self.subTest(line=line), self.assertRaises(ValueError):
                observer.parse_heartbeat(line)

    def test_capture_partial_invalid_overlong_resync_absolute_counters(self):
        first = heartbeat([4294967295] * 13)
        reset = heartbeat([0] * 13, b'\r\n')
        chunks = [first[:17], first[17:], b'bad\n', b'x' * 192,
                  heartbeat(), reset[:10], reset[10:]]
        transport = Transport(chunks)
        with self.external(transport):
            records = observer.capture('DIAGNOSTIC_CDC2', 2)
        self.assertEqual(records, [dict(zip(NAMES, [4294967295] * 13), host_observed_at=100),
                                   dict(zip(NAMES, [0] * 13), host_observed_at=101)])
        self.assertEqual(transport.opens, [(('DIAGNOSTIC_CDC2',), {'baudrate': 115200, 'timeout': 0.1})])
        self.assertTrue(transport.dtr)
        self.assertTrue(transport.closed)
        self.assertLessEqual(max(transport.read_sizes), 192)
        self.assertLessEqual(len(transport.read_sizes), 20)

    def test_invalid_duration_and_port_never_open(self):
        transport = Transport()
        with self.external(transport):
            for seconds in (0, -1, float('nan'), float('inf'), 60.01):
                with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                    observer.capture('DIAGNOSTIC_CDC2', seconds)
            for port in ('', '   '):
                with self.subTest(port=port), self.assertRaises(ValueError):
                    observer.capture(port, 1)
        self.assertEqual(transport.opens, [])

    def test_capture_serial_error_propagates(self):
        with self.external(Transport(error=OSError('diagnostic unavailable'))):
            with self.assertRaisesRegex(OSError, 'diagnostic unavailable'):
                observer.capture('DIAGNOSTIC_CDC2', 1)

    def test_cli_success_json(self):
        output = io.StringIO()
        with self.external(Transport([heartbeat()])), contextlib.redirect_stdout(output):
            result = observer.main(['--port', 'DIAGNOSTIC_CDC2', '--seconds', '1'])
        self.assertEqual(result, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload['port'], 'DIAGNOSTIC_CDC2')
        self.assertEqual(payload['records'], [dict(zip(NAMES, range(13)), host_observed_at=100)])
        self.assertIn('absolute', payload['note'].lower())
        self.assertIn('accepted', payload['note'].lower())
        self.assertIn('delivery', payload['note'].lower())

    def test_cli_empty_error_invalidduration_fail(self):
        for transport, seconds in ((Transport(), '1'), (Transport(error=OSError('unavailable')), '1'),
                                   (Transport(), 'nan')):
            with self.subTest(seconds=seconds, error=transport.error):
                with self.external(transport), contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()) as error:
                    result = observer.main(['--port', 'DIAGNOSTIC_CDC2', '--seconds', seconds])
                self.assertEqual(result, 1)
                if transport.error or seconds == 'nan':
                    self.assertTrue(error.getvalue())


if __name__ == '__main__':
    unittest.main()
