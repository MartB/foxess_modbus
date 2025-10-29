"""
Custom protocol handler for pyserial, which uses poll but doesn't have
https://github.com/pyserial/pyserial/issues/617
"""

import errno
import os
import select
from enum import Enum
from typing import Any

import serial
from serial import serialposix
from serial.serialutil import PortNotOpenError
from serial.serialutil import SerialException
from serial.serialutil import SerialTimeoutException
from serial.serialutil import Timeout
from serial.serialutil import to_bytes


class _PollResult(Enum):
    TIMEOUT = 0
    ABORT = 1
    READY = 2


class Serial(serialposix.Serial):
    """
    From https://github.com/pyserial/pyserial/blob/7aeea35429d15f3eefed10bbb659674638903e3a/serial/serialposix.py,
    but with https://github.com/pyserial/pyserial/pull/618 applied
    """

    @serial.Serial.port.setter  # type: ignore
    def port(self, value: str) -> None:
        if value is not None:
            serial.Serial.port.__set__(self, value.removeprefix("pollserial://"))

    def read(self, size: int = 1) -> bytes:
        """Read size bytes from the serial port using poll."""
        if not self.is_open:
            raise PortNotOpenError()

        read = bytearray()
        timeout = Timeout(self._timeout)

        poll = select.poll()
        poll.register(self.fd, select.POLLIN | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        poll.register(self.pipe_abort_read_r, select.POLLIN | select.POLLERR | select.POLLHUP | select.POLLNVAL)

        while len(read) < size:
            # Wait until device ready to read or timeout/abort occurs
            poll_timeout = None if timeout.is_infinite else int(timeout.time_left() * 1000)
            events = poll.poll(poll_timeout)

            result = _PollResult.TIMEOUT
            for fd, event in events:
                if fd == self.pipe_abort_read_r:
                    os.read(self.pipe_abort_read_r, 1000)
                    result = _PollResult.ABORT
                    break
                if event & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
                    raise SerialException("device reports error (poll)")
                if fd == self.fd:
                    result = _PollResult.READY

            if result == _PollResult.READY:
                buf = os.read(self.fd, size - len(read))
                read.extend(buf)
                if self._inter_byte_timeout and not buf:
                    break  # Stop if inter-byte timeout and no data
            elif result in (_PollResult.TIMEOUT, _PollResult.ABORT) or timeout.expired():
                break

        return bytes(read)

    def write(self, data: Any) -> int:
        """Write the given byte string over the serial port using poll."""
        if not self.is_open:
            raise PortNotOpenError()

        d = to_bytes(data)
        total_len = len(d)
        tx_remaining = total_len
        timeout = Timeout(self._write_timeout)

        poll = select.poll()
        poll.register(self.fd, select.POLLOUT | select.POLLERR | select.POLLHUP | select.POLLNVAL)
        poll.register(self.pipe_abort_write_r, select.POLLIN | select.POLLERR | select.POLLHUP | select.POLLNVAL)

        while tx_remaining > 0:
            try:
                n = os.write(self.fd, d)
                tx_remaining -= n
                d = d[n:]

                if timeout.is_non_blocking:
                    # Non-blocking: return bytes written immediately
                    return n

                if tx_remaining == 0:
                    break

                # Wait until ready to write again or timeout/abort occurs
                poll_timeout = None if timeout.is_infinite else int(timeout.time_left() * 1000)
                events = poll.poll(poll_timeout)

                result = _PollResult.TIMEOUT
                for fd, event in events:
                    if fd == self.pipe_abort_write_r:
                        os.read(self.pipe_abort_write_r, 1000)
                        result = _PollResult.ABORT
                        break
                    if event & (select.POLLERR | select.POLLHUP | select.POLLNVAL):
                        raise SerialException("device reports error (poll)")
                    if fd == self.fd:
                        result = _PollResult.READY

                if result == _PollResult.TIMEOUT:
                    raise SerialTimeoutException("Write timeout")
                if result == _PollResult.ABORT:
                    break

            except OSError as e:
                if e.errno not in (errno.EAGAIN, errno.EALREADY, errno.EWOULDBLOCK, errno.EINPROGRESS, errno.EINTR):
                    raise SerialException(f"write failed: {e}")  # noqa: B904

            if not timeout.is_non_blocking and timeout.expired():
                raise SerialTimeoutException("Write timeout")

        return total_len - len(d)

# This needs to have a very particular name, as it's registered by string in modbus_client
assert Serial.__module__ == "custom_components.foxess_modbus.client.protocol_pollserial"
assert Serial.__name__ == "Serial"
