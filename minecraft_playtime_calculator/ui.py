from __future__ import annotations

from collections import defaultdict
from csv import writer as csv_writer
import datetime as dt
from enum import Enum
from glob import iglob
import logging
from pathlib import Path
import threading
from typing import *

try:
    from matplotlib import pyplot as plt
except ImportError:
    plt = None
import wx
import wx.lib.newevent
from wx.lib.platebtn import PB_STYLE_SQUARE

from .minecraft_logs import *
from .plate_button import PlateButton
from .wx_utils import *

parent_logger = logging.getLogger('minecraft_logs_analyzer')
parent_logger.setLevel(logging.INFO)
logger = logging.getLogger('minecraft_logs_analyzer.ui')

LOG_FORMAT = '[%(levelname)s] %(message)s'


class ScanMode(Enum):
    AUTOMATIC = 'automatic'
    MANUAL = 'manual'
    GLOB = 'glob'


class ScanningState(Enum):
    IDLE = 0
    RUNNING = 1
    CANCELLING = 2


T_TimePerDay = List[Tuple[dt.date, dt.timedelta]]
ScanCompleteEvent, EVT_WX_SCAN_COMPLETE = wx.lib.newevent.NewEvent()


# noinspection PyBroadException
class PlaytimeCounterThread(threading.Thread):

    def __init__(self, parent: wx.Window, paths: List[Path], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self._parent = parent
        self._paths = paths

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def run(self) -> NoReturn:
        total_time = dt.timedelta()
        # Logs for a given date may be split to reduce filesize, so multiple
        # timedeltas for a date will be summed
        playtimes: Dict[dt.date, dt.timedelta] = defaultdict(dt.timedelta)
        cancelled = False

        try:
            for path in self._paths:
                for file, date in iter_logs(path):
                    if self.stopped():
                        cancelled = True
                        break
                    delta = get_log_timedelta(file)
                    if delta is None:
                        continue
                    logger.info(f"{file.name} {delta}")
                    playtimes[date] += delta
                    total_time += delta
        except:
            logger.error(
                "Unexpected error while scanning! Aborting.", exc_info=True
            )
            event = ScanCompleteEvent(success=False)
            wx.PostEvent(self._parent, event)
            return

        playtimes_sorted = list(sorted(playtimes.items()))
        event = ScanCompleteEvent(
            success=True, cancelled=cancelled,
            total_time=total_time, time_per_day=playtimes_sorted
        )
        wx.PostEvent(self._parent, event)


# noinspection PyPep8Naming,PyUnusedLocal,PyBroadException
class MinecraftPlaytimeCalculatorFrame(wx.Frame):

    title = "Minecraft Playtime Calculator - by Quinten Cabo and Hawkpath"

    margin_main = 20
    margin_control = 20
    margin_control_label = 4
    width_paths_input = 400

    text_begin_scan = "Calculate playtime"

    font_size = 11
    background_color = '#23272A'
    outline_color = '#2C2F33'
    foreground_color = '#BAC2D2'
    element_color = '#353C40'
    graph_color = '#18AAFF'

    def __init__(self, parent=None):
        super().__init__(parent, title=self.title, size=(1280, 720))
        self.SetMinSize((800, 400))

        self._scan_thread: Optional[PlaytimeCounterThread] = None
        self.playtime_total: Optional[dt.timedelta] = None
        self.playtime_days: Optional[T_TimePerDay] = None
        self.scan_mode = ScanMode.AUTOMATIC
        self.scanning_state = ScanningState.IDLE
        self.graph_months = None
        self.graph_times = None

        self.__DoLayout()
        self._init_logging()

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_WX_SCAN_COMPLETE, self.OnScanComplete)
        self.panel_controls.Bind(wx.EVT_RADIOBUTTON, self.OnChangeScanMode)
        self.scan_button.Bind(wx.EVT_BUTTON, self.OnScanButton)
        self.graph_button.Bind(wx.EVT_BUTTON, self.OnGraphButton)
        self.csv_button.Bind(wx.EVT_BUTTON, self.OnCSVButton)

        self.Show(True)

    def _init_logging(self):
        self._log_handler = WxLogHandler(self, logging.INFO)
        # self._log_handler = logging.StreamHandler(sys.stdout)
        self._log_handler.formatter = logging.Formatter()
        self._log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        parent_logger.addHandler(self._log_handler)
        self.Bind(EVT_WX_LOG_EVENT, self.OnLogEvent)

    def __DoLayout(self):
        bg = self.background_color
        fg = self.foreground_color
        element_color = self.element_color
        font = try_get_font(['Helvetica 10', 'Arial'], self.font_size)
        log_font = try_get_font(
            ['Consolas', 'Courier', 'Monospace'], self.font_size,
            monospace=True
        )

        self.SetBackgroundColour(bg)
        self.SetForegroundColour(fg)
        self.SetFont(font)

        panel_main = create_panel_with_margin(self, self.margin_main)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        panel_main.SetSizer(sizer_main)

        # Add controls

        self.panel_controls = panel_controls = wx.Panel(panel_main)
        self.sizer_controls = sizer_controls = wx.BoxSizer(wx.VERTICAL)
        panel_controls.SetSizer(sizer_controls)
        panel_controls.SetBackgroundColour(bg)
        panel_controls.SetForegroundColour(fg)
        panel_controls.SetMinSize((self.width_paths_input, -1))
        sizer_main.Add(panel_controls, 0, wx.EXPAND)

        # Scan mode
        label = wx.StaticText(panel_controls, label="Scan mode")
        scan_auto = wx.RadioButton(
            panel_controls, label="Automatic", name='automatic',
            style=wx.RB_GROUP
        )
        scan_manual = wx.RadioButton(
            panel_controls, label="Specify directories", name='manual'
        )
        scan_glob = wx.RadioButton(
            panel_controls, label="Specify files/globs", name='glob'
        )
        sizer_controls.Add(label)
        sizer_controls.AddSpacer(self.margin_control_label)
        sizer_controls.Add(scan_auto)
        sizer_controls.Add(scan_manual)
        sizer_controls.Add(scan_glob)

        # Path/glob input
        self.panel_path = panel_path = wx.Panel(panel_controls)
        sizer_path = wx.BoxSizer(wx.VERTICAL)
        panel_path.SetSizer(sizer_path)
        panel_path.SetForegroundColour(fg)
        panel_path.Hide()  # Initially hidden bc automatic is selected

        label = wx.StaticText(
            panel_path,
            label="Enter directories / files / globs to scan\n"
                  "(separate multiple with | )"
        )
        label.Wrap(panel_controls.Size[0])
        self.path_input = path_input = wx.TextCtrl(
            panel_path, size=(self.width_paths_input, -1)
        )
        path_input.SetBackgroundColour(bg)
        path_input.SetForegroundColour(fg)

        sizer_path.AddSpacer(self.margin_control)
        sizer_path.Add(label)
        sizer_path.AddSpacer(self.margin_control_label)
        sizer_path.Add(path_input)

        sizer_controls.Add(panel_path)

        # Buttons

        sizer_controls.AddStretchSpacer(1)

        self.scan_button = scan_button = PlateButton(
            panel_controls, label=self.text_begin_scan,
            style=PB_STYLE_SQUARE, size=(-1, 60)
        )
        scan_button.SetBackgroundColour(element_color)

        self.graph_button = graph_button = PlateButton(
            panel_controls, label="Show graph",
            style=PB_STYLE_SQUARE, size=(-1, 60)
        )
        graph_button.SetBackgroundColour(element_color)
        graph_button.Disable()

        self.csv_button = csv_button = PlateButton(
            panel_controls, label="Save CSV file",
            style=PB_STYLE_SQUARE, size=(-1, 60)
        )
        csv_button.SetBackgroundColour(element_color)
        csv_button.Disable()

        sizer_controls.Add(scan_button, 0, wx.EXPAND)
        sizer_controls.AddSpacer(self.margin_main // 2)
        sizer_controls.Add(graph_button, 0, wx.EXPAND)
        sizer_controls.AddSpacer(self.margin_main // 2)
        sizer_controls.Add(csv_button, 0, wx.EXPAND)

        # Add log output

        sizer_main.AddSpacer(self.margin_main)

        self.log_window = log = wx.TextCtrl(
            panel_main, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        log.SetBackgroundColour(element_color)
        log.SetForegroundColour(fg)
        log.SetFont(log_font)
        sizer_main.Add(log, 1, wx.EXPAND | wx.ALL)

    def OnClose(self, e: wx.Event):
        """
        Clean up scanning thread!
        """
        if self._scan_thread is not None:
            self._scan_thread.stop()
            self._scan_thread.join()
        self.Destroy()

    def OnLogEvent(self, e: WxLogEvent):
        msg = e.message + '\n'
        self.log_window.AppendText(msg)
        e.Skip()

    def OnChangeScanMode(self, e: wx.CommandEvent):
        self.scan_mode = ScanMode(e.EventObject.Name)
        if self.scan_mode is ScanMode.AUTOMATIC:
            self.panel_path.Hide()
        else:
            self.panel_path.Show()
        self.sizer_controls.Layout()

    def OnScanButton(self, e: wx.CommandEvent):
        if self.scanning_state is ScanningState.IDLE:
            self.start_scan()
        elif self.scanning_state is ScanningState.RUNNING:
            self.stop_scan()

    def OnScanComplete(self, e: ScanCompleteEvent):
        self._scan_thread = None
        self.update_scanning_state(ScanningState.IDLE)
        if not e.success:
            return

        self.scan_button.Enable()
        self.graph_button.Enable()
        self.csv_button.Enable()

        cancelled = e.cancelled
        self.playtime_total = e.total_time
        self.playtime_days = e.time_per_day
        hours = self.playtime_total.total_seconds() / 3600
        days = hours / 24

        if cancelled:
            logger.info("Scan cancelled!")
        else:
            logger.info("Scan complete!")
        logger.info(f"Total time: {hours:.2f} hours ({days:.2f} days)")

    def OnGraphButton(self, e: wx.CommandEvent):
        self.create_graph()

    def OnCSVButton(self, e: wx.CommandEvent):
        self.create_csv()

    def update_scanning_state(self, new_state: ScanningState):
        self.scanning_state = new_state
        button = self.scan_button
        if new_state is ScanningState.IDLE:
            button.SetLabel(self.text_begin_scan)
            button.Enable()
        if new_state is ScanningState.RUNNING:
            button.SetLabel("Cancel")
        if new_state is ScanningState.CANCELLING:
            button.SetLabel("Cancelling...")
            button.Disable()

    def start_scan(self):
        if self._scan_thread is None:
            try:
                paths = self.get_paths()
            except:
                logger.error(
                    "Unexpected error while getting paths! Scan aborted",
                    exc_info=True
                )
                return
            if paths is None:
                logger.error("No files to scan. Scan aborted")
                return
            logger.info("Starting log scan")

            self.playtime_total = None
            self.playtime_days = None
            self.graph_months = None
            self.graph_times = None

            self._scan_thread = PlaytimeCounterThread(self, paths)
            self._scan_thread.start()
            self.update_scanning_state(ScanningState.RUNNING)

    def stop_scan(self):
        if self._scan_thread is not None and not self._scan_thread.stopped():
            logger.info("Cancelling log scan")
            self.update_scanning_state(ScanningState.CANCELLING)
            self._scan_thread.stop()

    def get_paths(self) -> Optional[List[Path]]:
        scan_mode = self.scan_mode
        if scan_mode == ScanMode.AUTOMATIC:
            default_logs_path = get_default_logs_path()
            if not default_logs_path.exists():
                logger.error(
                    "Could not automatically locate your .minecraft/logs folder"
                )
                return
            return [default_logs_path]

        paths_or_globs = self.path_input.GetValue()
        if not paths_or_globs:
            return
        paths_or_globs = paths_or_globs.split('|')

        if scan_mode == ScanMode.MANUAL:
            paths = []
            for path in paths_or_globs:
                path = Path(path.strip(' '))
                if not path.exists():
                    logger.error(
                        f"The specified directory does not exist: {path}"
                    )
                    return
                paths.append(path)
            return paths

        if scan_mode == ScanMode.GLOB:
            paths = []
            for glob in paths_or_globs:
                for path in iglob(glob.strip(' '), recursive=True):
                    path = Path(path)
                    paths.append(path)
            if not paths:
                logger.error(f"The specified file(s) could not be found")
                return
            return paths

    def prepare_graph_data(self) -> NoReturn:

        if self.graph_months is not None and self.graph_times is not None:
            return

        def month_to_int(date: dt.date) -> int:
            """
            Get the sequential month number starting at year 0
            (0000-01-01 -> 0)
            """
            return date.year * 12 + (date.month - 1)

        def int_to_month(month_int: int) -> dt.date:
            """
            Get the date for this month number starting at year 0
            (0 -> 0000-01-01)
            """
            return dt.date(year=month_int // 12, month=(month_int % 12) + 1,
                           day=1)

        def add_month(new_month: Union[dt.date, int]):
            if isinstance(new_month, int):
                new_month = int_to_month(new_month)
            months.append(new_month.strftime('%Y-%m'))

        months: List[str] = []
        times: List[dt.timedelta] = []
        last_month: int = 0
        for day, time in self.playtime_days:
            # We can safely assume dates are sorted
            month = month_to_int(day)
            if month > last_month:
                # Start a new month entry
                if last_month != 0:
                    for i in range(last_month+1, month):
                        # Add in missing months
                        add_month(i)
                        times.append(dt.timedelta())
                add_month(month)
                times.append(dt.timedelta())
            # Sum up time for this month
            times[-1] += time
            last_month = month
        self.graph_months = months
        self.graph_times = [t.total_seconds() / 3600 for t in times]

    def create_graph(self):
        if plt is None:
            logger.warning(
                "matplotlib is not installed, so graphing is unavailable"
            )
            return
        if not self.playtime_days:
            logger.warning(
                "Not enough data to create a graph; one full month is "
                "needed"
            )
            return

        try:

            self.prepare_graph_data()

            fig, ax = plt.subplots(figsize=(16, 9))

            ax.bar(self.graph_months, self.graph_times, color=self.graph_color)

            plt.setp(ax.xaxis.get_majorticklabels(), rotation=70)

            ax.set_xlabel("Months")
            ax.set_ylabel("Hours")

            hours = self.playtime_total.total_seconds() / 3600
            days = hours / 24
            ax.set_title(f"Total playtime:\n{hours:.2f} hours ({days:.2f} days)")

            plt.show()

        except Exception:
            logger.error(
                "An unexpected error occurred while creating the graph. "
                "Make sure that you have matplotlib installed!",
                exc_info=True
            )

    def create_csv(self):
        if self.playtime_days is None:
            logger.error(
                "No time data has been collected yet. Run a scan first."
            )
            return

        with wx.FileDialog(
                self, "Save CSV file", defaultFile='minecraft_playtime.csv',
                wildcard='CSV files (*.csv)|*.csv|All files|*.*',
                style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as file_dialog:
            if file_dialog.ShowModal() == wx.ID_CANCEL:
                return
            path = file_dialog.GetPath()

        try:
            with open(path, 'w', newline='') as csv_file:
                writer = csv_writer(csv_file, delimiter=',')
                writer.writerow(["date", "seconds"])
                for day, time in self.playtime_days:
                    writer.writerow([str(day), int(time.total_seconds())])
        except PermissionError:
            logger.error(
                f"Failed to save file at {path}. This is probably because you "
                f"already have the file open in Excel (or another program). "
                f"Close any other program with this file open to overwrite it."
            )
        except IOError:
            logger.error(f"Failed to save file at {path}", exc_info=True)
        else:
            logger.info(f"Saved CSV file at {path}")
