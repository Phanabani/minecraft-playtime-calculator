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

from matplotlib import pyplot as plt
import wx
import wx.lib.newevent
from wx.lib.platebtn import PB_STYLE_SQUARE

from .minecraft_logs import *
from .plate_button import PlateButton

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


WxLogEvent, EVT_WX_LOG_EVENT = wx.lib.newevent.NewEvent()


class WxLogHandler(logging.Handler):

    def __init__(self, destination: wx.Window, level: int = logging.NOTSET):
        super().__init__(level=level)
        self.destination = destination

    def flush(self):
        pass

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            evt = WxLogEvent(message=msg, levelname=record.levelname)
            wx.PostEvent(self.destination, evt)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


T_TimePerDay = List[Tuple[dt.date, dt.timedelta]]
ScanCompleteEvent, EVT_WX_SCAN_COMPLETE = wx.lib.newevent.NewEvent()


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


def create_panel_with_margin(parent: wx.Window, margin: int):
    margin_panel = wx.Panel(parent)
    margin_sizer = wx.BoxSizer()
    margin_panel.SetSizer(margin_sizer)

    panel = wx.Panel(margin_panel)
    margin_sizer.Add(panel, 1, wx.ALL | wx.EXPAND, margin)
    return panel


class MinecraftLogsAnalyzerFrame(wx.Frame):

    title = "Minecraft playtime calculator - by Quinten Cabo and Hawkpath"

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

        self.__DoLayout()
        self._init_logging()

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(EVT_WX_SCAN_COMPLETE, self.OnScanComplete)
        self.panel_controls.Bind(wx.EVT_RADIOBUTTON, self.OnChangeScanMode)
        self.scan_button.Bind(wx.EVT_BUTTON, self.OnScanButton)

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
        font = self._get_main_font()
        log_font = self._get_monospace_font()

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
            panel_controls, label="Enter directories", name='manual'
        )
        scan_glob = wx.RadioButton(
            panel_controls, label="Enter glob", name='glob'
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
            label="Enter directories / globs\n(separate multiple with | )"
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

        # button = wx.Button(controls_panel, label="Calculate play time")
        self.scan_button = button = PlateButton(
            panel_controls, label=self.text_begin_scan,
            style=PB_STYLE_SQUARE, size=(-1, 60)
        )
        button.SetBackgroundColour(element_color)
        sizer_controls.AddStretchSpacer(1)
        sizer_controls.Add(button, 0, wx.EXPAND)

        # Add log output

        sizer_main.AddSpacer(self.margin_main)

        self.log_window = log = wx.TextCtrl(
            panel_main, style=wx.TE_MULTILINE | wx.TE_READONLY
        )
        log.SetBackgroundColour(element_color)
        log.SetForegroundColour(fg)
        log.SetFont(log_font)
        sizer_main.Add(log, 1, wx.EXPAND | wx.ALL)

    def _get_font(self, face_name: str = ''):
        return wx.Font(
            self.font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL, faceName=face_name
        )

    def _get_system_fonts(self, monospace=False):
        fonts = wx.FontEnumerator()
        fonts.EnumerateFacenames(wx.FONTENCODING_SYSTEM, fixedWidthOnly=monospace)
        return fonts.GetFacenames(wx.FONTENCODING_SYSTEM, fixedWidthOnly=monospace)

    def _get_main_font(self):
        fonts = self._get_system_fonts()
        if 'Arial' in fonts:
            return self._get_font('Arial')
        return self._get_font()

    def _get_monospace_font(self):
        fonts = self._get_system_fonts(monospace=True)
        if 'Consolas' in fonts:
            return self._get_font('Consolas')
        if fonts:
            return self._get_font(fonts[0])
        return self._get_font()

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
                    "Unexpected error while getting paths! Scan aborted.",
                    exc_info=True
                )
                return
            if paths is None:
                logger.error("No logs path is specified!")
                return
            logger.info("Starting log scan")
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

        paths_or_globs = self.path_input.GetValue().split('|')

        if scan_mode == ScanMode.MANUAL:
            paths = []
            for path in paths_or_globs:
                path = Path(path)
                if not path.exists():
                    logger.error(f"The specified path does not exist: {path}")
                    return
                paths.append(path)
            return paths

        if scan_mode == ScanMode.GLOB:
            paths = []
            for glob in paths_or_globs:
                for path in iglob(glob, recursive=True):
                    path = Path(path)
                    paths.append(path)
            if not paths:
                logger.error(f"No paths were found")
                return
            return paths

    def create_graph(self):
        try:
            if not self.playtime_days:
                logger.warning(
                    "Not enough data to create a graph; one full month is "
                    "needed"
                )
                return
            data_list_dates = list(self.graph_data_collection.keys())
            data_list_hour = list(self.graph_data_collection.values())
            plt.bar(data_list_dates, data_list_hour, color=self.graph_color)

            plt.xticks(rotation='vertical')

            plt.xlabel("Months")
            plt.ylabel("Hours")
            plt.title(f"Total playtime:\n{self.playtime_total}")
            plt.draw()
            plt.show()
        except Exception:
            logger.error(
                "An unexpected error occurred while creating the graph. "
                "Make sure that you have matplotlib installed!",
                exc_info=True
            )

    def get_color(self):
        color = askcolor()
        self.graph_color = color[1]
        self.color_button.config(bg=self.graph_color)
        logger.info(f"Color changed to {self.graph_color}")

    def create_csv(self):
        if len(self.csv_data) != 0:
            filename = filedialog.asksaveasfilename(
                initialdir="/desktop", title="Save file:",
                initialfile="minecraft_playtime.csv",
                filetypes=(("csv files", "*.csv"), ("all files", "*.*"))
            )
            with open(filename, newline='', mode="w+") as csvfile:
                writer = csv_writer(csvfile, delimiter=',')
                writer.writerow(["Day", "Hours"])
                writer.writerows(self.csv_data.items())
        else:
            logger.warning(
                "Not enough data to create a CSV file. Make sure to start a "
                "scan first."
            )
