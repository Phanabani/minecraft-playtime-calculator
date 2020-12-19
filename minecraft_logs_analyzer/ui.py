from __future__ import annotations
from csv import writer as csv_writer
import datetime as dt
from enum import IntEnum
from glob import iglob
import logging
from pathlib import Path
import queue
from tkinter import *
from tkinter import filedialog
from tkinter.colorchooser import *
from tkinter.scrolledtext import ScrolledText
import tkinter.ttk as ttk
from typing import *

from matplotlib import pyplot as plt

from .minecraft_logs import *

parent_logger = logging.getLogger('minecraft_logs_analyzer')
parent_logger.setLevel(logging.INFO)
logger = logging.getLogger('minecraft_logs_analyzer.ui')

LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'


class ScanMode(IntEnum):
    AUTOMATIC = 0
    MANUAL = 1
    GLOB = 2


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


class MinecraftLogsAnalyzerUI:

    background_color = '#23272A'
    outline_color = '#2C2F33'
    foreground_color = 'white'
    graph_color = '#18aaff'
    log_text_color = '#2C2F33'
    font = 'Helvetica 10'

    _scan_thread: PlaytimeCounterThread = None
    _scan_queue: queue.Queue[T_ScanResult] = None
    log_widget: ScrolledText

    def __init__(self):
        self.root = Tk()
        self.playtime_total: Optional[dt.timedelta] = None
        self.playtime_days: Optional[T_PlaytimePerDay] = None

        self.scan_mode = IntVar(value=int(ScanMode.AUTOMATIC))
        self.path = StringVar()
        self._pack()
        self._init_logging()

    def _init_logging(self):
        self._log_handler = TkinterScrolledTextLogHandler(
            self.log_widget, logging.INFO
        )
        self._log_handler.formatter = logging.Formatter()
        self._log_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        parent_logger.addHandler(self._log_handler)

    def _pack(self):
        root = self.root
        bg = self.background_color
        fg = self.foreground_color
        font = self.font

        root.title("Playtime calculator - By Quinten Cabo")
        root.config(bg=bg)

        frame = Frame(root, bg=bg)
        frame.pack()

        # mode selection
        mode_text = Message(
            frame, text="Choose scan mode:", bg=bg, fg=fg,
            relief="groove", font=font
        )
        mode_text.config(width=120)
        mode_text.pack()

        s = ttk.Style()  # Creating style element
        s.configure(
            'Wild.TRadiobutton',  # First argument is the name of style. Needs to end with: .TRadiobutton
            background=bg,  # Setting background to our specified color above
            foreground=fg,
            font=font
        )

        mode1 = ttk.Radiobutton(
            frame, text="Automatic    ", variable=self.scan_mode,
            value=int(ScanMode.AUTOMATIC), command=self.change_mode,
            cursor="hand2", style='Wild.TRadiobutton'
        )
        mode2 = ttk.Radiobutton(
            frame, text="Enter path(s)", variable=self.scan_mode,
            value=int(ScanMode.MANUAL), command=self.change_mode,
            cursor="hand2", style='Wild.TRadiobutton'
        )
        mode3 = ttk.Radiobutton(
            frame, text="Enter glob    ", variable=self.scan_mode,
            value=int(ScanMode.GLOB), command=self.change_mode,
            cursor="hand2", style='Wild.TRadiobutton'
        )
        mode1.pack()
        mode2.pack()
        mode3.pack()

        Message(frame, text="", bg="#23272A").pack()

        # Path input
        path_text = Message(
            frame, text="(Separate input with '|')\nEnter path(s) / glob:",
            bg=bg, fg=fg, relief="groove", font=font
        )
        path_text.config(width=130, justify="center")
        path_text.pack()

        self.path_input = Entry(
            frame, exportselection=0, textvariable=self.path, state="disabled",
            cursor="arrow", bg="white", disabledbackground=bg, width=40,
            font=font
        )
        self.path_input.pack()

        Message(frame, text="", bg=bg).pack()

        # run button
        submit_button = Button(
            frame, text="Run", command=self.start_scan,
            cursor="hand2", bg=bg, fg=fg, font=font
        )
        submit_button.config(width=20)
        submit_button.pack()

        # graph button
        graph_button = Button(
            frame, text="Create graph", command=self.create_graph,
            cursor="hand2", bg=bg, fg=fg, font=font
        )
        graph_button.config(width=20)
        graph_button.pack()

        self.color_button = Button(
            frame, text='Select Color', command=self.get_color,
            bg=self.graph_color, font=font
        )
        self.color_button.config(width=20)
        self.color_button.pack()

        # csv button
        graph_button = Button(
            frame, text="Export as csv", command=self.create_csv,
            cursor="hand2", bg=bg, fg=fg, font=font)
        graph_button.config(width=20)
        graph_button.pack()

        # output
        self.log_widget = ScrolledText(
            frame, bg=self.log_text_color, fg="white", font="Helvetica 11"
        )
        self.log_widget.config(width=120)
        self.log_widget.pack()

        # exit button
        stop_button = Button(
            frame, text="Stop scanning", command=self.stop_scan,
            width=20, bg=bg, fg=fg, font=font
        )
        stop_button.pack()

    def start(self):
        self.root.mainloop()

    @property
    def log_handler(self):
        return self._log_handler

    def change_mode(self):
        scan_mode = self.scan_mode.get()
        if scan_mode == ScanMode.MANUAL:
            self.path_input.config(state='disabled', cursor="arrow")
        else:
            self.path_input.config(state='normal', cursor="hand2")
        logger.info(f"Changed mode to {ScanMode(scan_mode)._name_.lower()}")

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

    def process_queue(self):
        try:
            self.playtime_total, self.playtime_days = self._scan_queue.get()
        except queue.Empty:
            self.root.after(100, self.process_queue)

    def stop_scan(self):
        if self._scan_thread is not None and not self._scan_thread.stopped():
            logger.info("Cancelling log scan")
            self._scan_thread.stop()

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
