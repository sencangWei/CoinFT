import argparse
import json
import math
import sys
import time

FIELD_NAMES = ('seq', 'uptime_ms', 'loop_count', 'uart_bytes', 'rx_data_reads',
               'rx_payload_bytes', 'rx_end_markers', 'rx_end_timeouts',
               'timer_ticks', 'usb_attempts', 'usb_accepted_bytes',
               'start_commands', 'stop_commands')


def parse_heartbeat(line: bytes) -> dict:
    if len(line) > 192 or not line.endswith(b'\n'):
        raise ValueError('heartbeat must be a complete record of at most 192 bytes')
    body = line[:-1]
    if body.endswith(b'\r'):
        body = body[:-1]
    fields = body.split(b',')
    if len(fields) != 14 or fields[0] != b'CFD1':
        raise ValueError('invalid CFD1 heartbeat schema')
    values = []
    for field in fields[1:]:
        if not field or any(byte < 48 or byte > 57 for byte in field):
            raise ValueError('heartbeat counters must be unsigned decimal integers')
        value = int(field)
        if value > 4294967295:
            raise ValueError('heartbeat counter exceeds uint32')
        values.append(value)
    return dict(zip(FIELD_NAMES, values))


def capture(port: str, seconds: float) -> list[dict]:
    if not port or not port.strip():
        raise ValueError('an explicit diagnostic port is required')
    if not math.isfinite(seconds) or not 0 < seconds <= 60:
        raise ValueError('seconds must be finite and greater than 0, at most 60')
    import serial

    records = []
    buffer = bytearray()
    discarding = False
    with serial.Serial(port, baudrate=115200, timeout=0.1) as connection:
        connection.dtr = True
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            for byte in connection.read(192):
                if discarding:
                    if byte == 10:
                        discarding = False
                    continue
                if len(buffer) == 192:
                    buffer.clear()
                    discarding = byte != 10
                    continue
                buffer.append(byte)
                if byte == 10:
                    try:
                        record = parse_heartbeat(bytes(buffer))
                    except ValueError:
                        pass
                    else:
                        record['host_observed_at'] = time.time()
                        records.append(record)
                    buffer.clear()
    return records


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Read the separate Teensy diagnostic CDC port')
    parser.add_argument('--port', required=True)
    parser.add_argument('--seconds', type=float, default=10)
    args = parser.parse_args(argv)
    try:
        records = capture(args.port, args.seconds)
    except Exception as exc:
        print(f'Diagnostic capture failed: {exc}', file=sys.stderr)
        return 1
    print(json.dumps({
        'port': args.port,
        'records': records,
        'note': 'Absolute uint32 counters; accepted USB bytes do not prove PC delivery. '
                'host_observed_at is observer wall time, not acquisition time or verified link latency.',
    }))
    return 0 if records else 1


if __name__ == '__main__':
    raise SystemExit(main())
