from __future__ import annotations
from csv import writer as csv_writer
import datetime as dt
from enum import Enum
from glob import iglob
import logging
from pathlib import Path
import queue
from typing import *

from matplotlib import pyplot as plt
import wx
from wx.lib.platebtn import PB_STYLE_SQUARE

from .minecraft_logs import *
from .plate_button import PlateButton

parent_logger = logging.getLogger('minecraft_logs_analyzer')
parent_logger.setLevel(logging.INFO)
logger = logging.getLogger('minecraft_logs_analyzer.ui')

LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'


class ScanMode(Enum):
    AUTOMATIC = 'automatic'
    MANUAL = 'manual'
    GLOB = 'glob'


class TkinterScrolledTextLogHandler(logging.Handler):

    def __init__(self, scrolled_text: ScrolledText,
                 level: int = logging.NOTSET, *, scroll=True):
        super().__init__(level=level)
        self._scrolled_text = scrolled_text
        self.scroll = scroll

    def emit(self, record: logging.LogRecord):
        if not isinstance(self._scrolled_text, ScrolledText):
            return
        formatted = self.format(record)
        self._scrolled_text.insert(END, formatted)
        if self.scroll:
            self._scrolled_text.see(END)


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
    width_paths_input = 200

    font_size = 11
    background_color = '#23272A'
    outline_color = '#2C2F33'
    foreground_color = 'white'
    element_color = '#353C40'
    graph_color = '#18aaff'
    log_text_color = '#2C2F33'

    _scan_thread: PlaytimeCounterThread = None
    _scan_queue: queue.Queue[T_ScanResult] = None
    log_widget: ScrolledText

    def __init__(self, parent=None):
        super().__init__(parent, title=self.title, size=(1280, 720))
        self.playtime_total: Optional[dt.timedelta] = None
        self.playtime_days: Optional[T_PlaytimePerDay] = None

        self.scan_mode = ScanMode.AUTOMATIC
        self.path_or_glob = None

        self._init_logging()
        self._pack()
        self._init_logging()
        self.Show(True)

    def _init_logging(self):
        self._log_handler = TkinterScrolledTextLogHandler(
            self.log_widget, logging.INFO
        )
        self._log_handler.formatter = logging.Formatter()
        self._log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        parent_logger.addHandler(self._log_handler)

    def _pack(self):
        bg = self.background_color
        fg = self.foreground_color
        element_color = self.element_color
        font = wx.Font(
            self.font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
            wx.FONTWEIGHT_NORMAL, faceName=''
        )

        self.SetBackgroundColour(bg)
        self.SetForegroundColour(fg)
        self.SetFont(font)

        panel_main = create_panel_with_margin(self, self.margin_main)
        sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        panel_main.SetSizer(sizer_main)

        # Add controls

        self.controls_panel = panel_controls = wx.Panel(panel_main)
        self.controls_panel_sizer = sizer_controls = wx.BoxSizer(wx.VERTICAL)
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
            panel_controls, label="Enter path(s)", name='manual'
        )
        scan_glob = wx.RadioButton(
            panel_controls, label="Enter glob", name='glob'
        )
        sizer_controls.Add(label)
        sizer_controls.AddSpacer(self.margin_control_label)
        sizer_controls.Add(scan_auto)
        sizer_controls.Add(scan_manual)
        sizer_controls.Add(scan_glob)
        panel_controls.Bind(wx.EVT_RADIOBUTTON, self.change_scan_mode)

        # Path/glob input
        self.path_or_glob_panel = panel_path = wx.Panel(panel_controls)
        sizer_path = wx.BoxSizer(wx.VERTICAL)
        panel_path.SetSizer(sizer_path)
        panel_path.SetForegroundColour(fg)
        panel_path.Hide()  # Initially hidden bc automatic is selected

        label = wx.StaticText(
            panel_path, label="Enter path(s) / glob (separate with | )"
        )
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
        self.b = button = PlateButton(
            panel_controls, label="hi",
            style=PB_STYLE_SQUARE, size=(200, 40)
        )
        button.SetBackgroundColour(element_color)
        sizer_controls.AddStretchSpacer(1)
        sizer_controls.Add(button)

        # Add log output

        sizer_main.AddSpacer(self.margin_main)

        log = wx.TextCtrl(panel_main, value="HEY THERE", style=wx.TC_MULTILINE)
        sizer_main.Add(log, 1, wx.EXPAND | wx.ALL)

    @property
    def log_handler(self):
        return self._log_handler

    def change_scan_mode(self, e):
        self.scan_mode = ScanMode(e.EventObject.Name)
        if self.scan_mode is ScanMode.AUTOMATIC:
            self.path_or_glob_panel.Hide()
        else:
            self.path_or_glob_panel.Show()
        self.controls_panel_sizer.Layout()
        logger.info(f"Changed mode to {self.scan_mode._name_}")

    def start_scan(self):
        if self._scan_thread is None:
            logger.info("Starting log scan")
            self._scan_queue = queue.Queue()
            paths = self.get_paths()
            if paths is None:
                return
            self._scan_thread = PlaytimeCounterThread(self._scan_queue, paths)
            self._scan_thread.start()
            self.root.after(100, self.process_queue)

    def stop_scan(self):
        if self._scan_thread is not None and not self._scan_thread.stopped():
            logger.info("Cancelling log scan")
            self._scan_thread.stop()

    def process_queue(self):
        try:
            self.playtime_total, self.playtime_days = self._scan_queue.get()
        except queue.Empty:
            self.root.after(100, self.process_queue)

    def get_paths(self) -> Optional[List[Path]]:
        scan_mode = self.scan_mode.get()
        if scan_mode == ScanMode.AUTOMATIC:
            default_logs_path = get_default_logs_path()
            if not default_logs_path.exists():
                logger.error(
                    "Could not automatically locate your .minecraft/logs folder"
                )
                return
            return [default_logs_path]

        if scan_mode == ScanMode.MANUAL:
            paths = []
            for path in self.path.get().split("|"):
                path = Path(path)
                if not path.exists():
                    logger.error(
                        f"The specified path does not exist: {path}"
                    )
                    return
                paths.append(path)
            return paths

        if scan_mode == ScanMode.GLOB:
            globs = self.path.get().split("|")
            paths = []
            for glob in globs:
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
