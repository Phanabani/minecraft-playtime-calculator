from __future__ import annotations

import datetime as dt
from io import SEEK_END
import gzip
import logging
import os
import re
from pathlib import Path
import sys
from typing import *
from typing import Match, Pattern

__all__ = [
    'iter_logs', 'get_log_timedelta', 'get_default_logs_path'
]

logger = logging.getLogger('minecraft_logs_analyzer.minecraft_logs')

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


def find_backwards(
        stream: TextIO, pattern: Pattern, buffer_size: int = 128
) -> Optional[Match]:
    pos_init = stream.tell()
    pos = stream.seek(0, SEEK_END)
    buffer_last = ''
    match = None

    while pos > 0:
        pos = max(pos - buffer_size, 0)
        stream.seek(pos)
        buffer = stream.read(buffer_size)
        matches = list(pattern.finditer(buffer + buffer_last))
        if matches:
            match = matches[-1]
            break
        buffer_last = buffer

    stream.seek(pos_init)
    return match


def parse_log_name(file: Path) -> Optional[dt.date]:
    name_match = log_name_pattern.fullmatch(file.name)
    if not name_match:
        return None
    return dt.date.fromisoformat(name_match.group('date'))


def iter_logs(dir_or_file: Union[str, Path]) -> Generator[Tuple[Path, dt.date]]:
    if isinstance(dir_or_file, str):
        dir_or_file = Path(dir_or_file)
    elif not isinstance(dir_or_file, Path):
        raise TypeError("path must be of type str or Path.")

    if dir_or_file.is_file():
        date = parse_log_name(dir_or_file)
        if date is not None:
            yield dir_or_file, date
        return

    for file in dir_or_file.iterdir():
        date = parse_log_name(file)
        if date is None:
            continue
        yield file, date


def open_log(file: Path) -> TextIO:
    if file.suffix == '.gz':
        return gzip.open(file, 'rt', errors='ignore')
    if file.suffix == '.log':
        # noinspection PyTypeChecker
        return open(file, 'rt', errors='ignore')


def get_log_timedelta(log: Path) -> Optional[dt.timedelta]:
    try:
        log = open_log(log)
        start_time = time_pattern.search(log.readline())
        if start_time is None:
            logger.warning(
                f"Unable to find start time; skipping (file={log.name})"
            )
            return
        end_time = find_backwards(log, time_pattern)
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
    finally:
        log.close()

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
