from __future__ import annotations
from datetime import timedelta
from io import TextIOBase, SEEK_END
import gzip
import os
import re
from pathlib import Path
from typing import *


def read_backward_until(stream, delimiter, buf_size=32, stop_after=1,
                        trim_start=0):
    """
    `stream` (TextIOBase): Stream to read from
    `delimiter` (str|re._pattern_type): Delimeter marking when to stop reading
    `buf_size` (int): Number of characters to read/store in buffer while
                      progressing backwards. Ensure this is greater than or
                      equal to the intended length of `delimiter` so that the
                      entire delimiter can be detected
    `stop_after` (int): Return the result after detecting this many delimiters
    `trim_start` (int): If not 0, this many characters will be skipped
                        from the beginning of the output (to return only
                        what comes after delimiter, for instance)
    """
    if not isinstance(stream, TextIOBase):
        raise TypeError('Expected type of `stream` to be TextIOBase, got %s'
                        % type(stream))
    if not (isinstance(delimiter, str)
            or isinstance(delimiter, Pattern)):
        raise TypeError('Expected type of `delimiter` to be str or '
                        'regex pattern, got %s' % type(delimiter))

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
            delim_pos = buf.find('\n')
        else:
            delim_pos = delimiter.search(buf)
            delim_pos = delim_pos.start() if delim_pos else -1

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
            stream.seek(cursor + delim_pos + trim_start - 1)
            last_line = stream.read()
            stream.seek(original_pos)
            return last_line
    # No match
    return None


def read_last_line(stream):
    return read_backward_until(stream, os.linesep, stop_after=2, trim_start=2)


def iter_logs(path: Union[str, Path]) -> Generator[TextIO]:
    if isinstance(path, str):
        path = Path(path)
    elif not isinstance(path, Path):
        raise TypeError('Expected type of `path` to be str or Path, got %s'
                        % type(path))
    open_methods = {'.log': open, '.gz': gzip.open}

    for file in path.iterdir():
        if file.suffix not in open_methods:
            continue
        elif not file.name.startswith('20'):
            continue
        yield open_methods[file.suffix](
            file, 'rt', encoding='ansi', errors='replace', newline=''
        )


def count_playtime(path, count=-1, print_files='file'):
    global graph_data_collection,stop_scan,total_data_time,data_total_play_time,csv_data
    current_month = ""
    total_data_time = 0
    time_pattern = re.compile(
        r'\[(?P<hour>\d{2}):(?P<min>\d{2}):(?P<sec>\d{2})\]', re.I
    )
    time_pattern_simple = re.compile(r'\d{2}:\d{2}:\d{2}')
    total_time = timedelta()

    for log in iter_logs(path):
        try:
            if stop_scan:
                stop_scan = False
                insert("\nTotal Time:" + " " + str(total_time))
                data_total_play_time = total_time
                return
            if count == 0:
                return
            count -= 1

            try:
                start_time = time_pattern.match(log.readline()).groupdict()
                end_time = time_pattern.match(
                    read_backward_until(log, time_pattern_simple)).groupdict()
            except AttributeError as e:
                # Not a recognized chat log
                insert("ERROR: {} generated this error: {}".format(Path(log.name).name,e))
                continue
            except EOFError:
                insert('ERROR: {} may be corrupted -- skipping'.format(Path(log.name).name))
                continue
            except OSError:
                insert('ERROR: {} may be corrupted or is not gzipped -- skipping'.format(Path(log.name).name))
                continue
            except:
                insert('ERROR: An error occured while scanning file {} -- skiping')
            start_time = timedelta(
                hours=int(start_time['hour']),
                minutes=int(start_time['min']),
                seconds=int(start_time['sec'])
            )
            end_time = timedelta(
                hours=int(end_time['hour']),
                minutes=int(end_time['min']),
                seconds=int(end_time['sec'])
            )
            if end_time < start_time:
                end_time += timedelta(days=1)
            delta = end_time - start_time
            total_time += delta
            if print_files == 'full':
                insert(str(log.name)+" "+str(delta))
            elif print_files == 'file':
                insert(str(Path(log.name).name)+" "+str(delta))
            # collect data for csv
            csv_data[str(Path(log.name).name)[:12]] = str(delta)

            # collect data for graph
            month = str(Path(log.name).name)[:7]
            if current_month != month:  # Check if we are still on the same month if not save the current month and move on
                if current_month != '':
                    if current_month not in graph_data_collection:
                        graph_data_collection[current_month] = 0
                    graph_data_collection[current_month] += int(total_data_time/3600) # make seconds an hour this will mean that if you played less then an hour it will end up as 0
                # add first month and next
                current_month = month
                total_data_time = delta.total_seconds()
            else:
                total_data_time += delta.total_seconds()
                data_total_play_time = total_time

        finally:
            log.close()

    return total_time
