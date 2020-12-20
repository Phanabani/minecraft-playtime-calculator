from __future__ import annotations

import datetime as dt
from io import TextIOBase, SEEK_END
import gzip
import logging
import os
import re
from pathlib import Path
import sys
from typing import *
from typing import Pattern

logger = logging.getLogger('minecraft_logs_analyzer.minecraft_logs')

T_PlaytimePerDay = List[Tuple[dt.date, dt.timedelta]]
T_ScanResult = Tuple[dt.timedelta, T_PlaytimePerDay]

log_name_pattern = re.compile(r'(?P<date>\d{4}-\d\d-\d\d)-\d+\.log(?:\.gz)?')
time_pattern = re.compile(
    r'\[(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\]'
)


def get_default_logs_path() -> Optional[Path]:
    platform = sys.platform
    error_msg = (
        "Could not automatically find your .minecraft/logs folder. Please "
        "enter it manually."
    )

    if platform == 'win32':
        appdata = os.environ['APPDATA']
        path = Path(appdata, '.minecraft/logs')
        if not path.exists():
            logger.error(error_msg)
            return
        return path

    if platform == 'darwin':
        path = Path('~/Library/Application Support/minecraft/logs')
        if not path.exists():
            logger.error(error_msg)
            return
        return path

    if platform == 'linux':
        path = Path('~/.minecraft/logs')
        if not path.exists():
            logger.error(error_msg)
            return
        return path


def read_backward_until(
        stream: TextIO, delimiter: Union[str, Pattern], buf_size: int = 32,
        stop_after: int = 1, trim_start: int = 0
) -> Optional[str]:
    """
    Seek backwards until `delimiter` is found, then read and return the rest
    of the stream.

    :param stream: stream to read from
    :param delimiter: delimiter marking when to stop reading
    :param buf_size: number of characters to read/store in buffer while
        progressing backwards. Ensure this is greater than or equal to the
        intended length of `delimiter` so that the entire delimiter can be
        detected
    :param stop_after: return the result after detecting this many delimiters
    :param trim_start: If not 0, this many characters will be skipped from the
        beginning of the output (to return only what comes after delimiter, for
        instance)
    :returns: the rest of the stream
    """
    if not isinstance(stream, TextIOBase):
        raise TypeError("stream must be of type TextIO")
    if not isinstance(delimiter, (str, Pattern)):
        raise TypeError("delimiter must be of type str or Pattern")

    stop_after -= 1
    original_pos = stream.tell()
    cursor = stream.seek(0, SEEK_END)
    buf = ' ' * (buf_size*2)

    while cursor >= 0:
        if cursor >= buf_size:
            cursor -= buf_size
        else:
            cursor = 0
        stream.seek(cursor)
        # Combine the previous two buffers in case delimiter runs
        # across two buffers
        buf = stream.read(buf_size) + buf[:buf_size]

        if isinstance(delimiter, str):
            delim_pos = buf.rfind(delimiter)
        else:
            matches = list(delimiter.finditer(buf))
            if matches:
                delim_pos = matches[-1].start()
            else:
                delim_pos = -1

        if delim_pos == -1 or delim_pos >= buf_size:
            # Skip if no delimiter found or if it's in the second half of
            # the buffer (it will turn up twice as it moves to the end of
            # the buffer)
            pass
        elif stop_after > 0:
            # Decrement since we found delimiter
            stop_after -= 1
        else:
            # Move to the start of the final line
            stream.seek(max(cursor, 1) + delim_pos + trim_start - 1)
            last_line = stream.read()
            stream.seek(original_pos)
            return last_line
    # No match
    return None


def read_last_line(stream: TextIO):
    return read_backward_until(stream, os.linesep, stop_after=2,
                               trim_start=len(os.linesep))


def iter_logs(path: Union[str, Path]) -> Generator[Tuple[TextIO, Path, dt.date]]:
    if isinstance(path, str):
        path = Path(path)
    elif not isinstance(path, Path):
        raise TypeError("path must be of type str or Path.")
    open_methods = {'.log': open, '.gz': gzip.open}

    for file in path.iterdir():
        name_match = log_name_pattern.fullmatch(file.name)
        if not name_match:
            continue
        date = dt.date.fromisoformat(name_match.group('date'))
        stream = open_methods[file.suffix](file, 'rt', errors='ignore')
        yield stream, file, date


def get_log_timedelta(log: TextIO) -> Optional[dt.timedelta]:
    try:
        start_time = time_pattern.search(log.readline())
        if start_time is None:
            logger.warning(
                f"Unable to find start time; skipping (file={log.name})"
            )
            return
        end_time = time_pattern.search(read_backward_until(log, time_pattern))
        if end_time is None:
            logger.warning(
                f"Unable to find end time; skipping (file={log.name})"
            )
            return
    except EOFError:
        logger.warning(
            f"Log file may be corrupted; skipping (file={log.name})"
        )
        return
    except OSError:
        logger.warning(
            f"Log file may be corrupted or is unable to be opened; "
            f"skipping (file={log.name})",
            exc_info=True
        )
        return
    except:
        logger.warning(
            f"Unexpected error while reading log file; skipping "
            f"(file={log.name})",
            exc_info=True
        )
        return

    start_time = dt.timedelta(
        hours=int(start_time['hour']),
        minutes=int(start_time['min']),
        seconds=int(start_time['sec'])
    )
    end_time = dt.timedelta(
        hours=int(end_time['hour']),
        minutes=int(end_time['min']),
        seconds=int(end_time['sec'])
    )

    if end_time < start_time:
        end_time += dt.timedelta(days=1)
    return end_time - start_time
