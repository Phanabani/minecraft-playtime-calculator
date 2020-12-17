from __future__ import annotations
from _thread import start_new_thread
from csv import writer as csv_writer
from datetime import timedelta
from enum import IntEnum
from glob import iglob
import logging
import os
from pathlib import Path
from tkinter import *
from tkinter import filedialog
from tkinter.colorchooser import *
from tkinter.scrolledtext import ScrolledText
import tkinter.ttk as ttk
from typing import *

from matplotlib import pyplot as plt

from . import minecraft_logs as mc_logs

logger = logging.getLogger('minecraft_logs_analyzer.ui')


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

    log_widget: ScrolledText

    def __init__(self):
        self.root = Tk()
        self.csv_data = {}

        self.graph_data_collection = {}
        self.total_play_time = None

        self.scan_mode = IntVar(None, ScanMode.AUTOMATIC)
        self.path = StringVar()
        self._pack()
        self._log_handler = TkinterScrolledTextLogHandler(self.log_widget)
        self.root.mainloop()

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
            value=ScanMode.AUTOMATIC, command=self.change_mode,
            cursor="hand2", style='Wild.TRadiobutton'
        )
        mode2 = ttk.Radiobutton(
            frame, text="Enter path(s)", variable=self.scan_mode,
            value=ScanMode.MANUAL, command=self.change_mode,
            cursor="hand2", style='Wild.TRadiobutton'
        )
        mode3 = ttk.Radiobutton(
            frame, text="Enter glob    ", variable=self.scan_mode,
            value=ScanMode.GLOB, command=self.change_mode,
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
            frame, text="Run", command=self.run,
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
            frame, text="Stop scanning", command=exit,
            width=20, bg=bg, fg=fg, font=font
        )
        stop_button.pack()

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
        # probably put path detect here

    def count_playtimes_thread(self, paths, mode):
        total_time = timedelta()
        if mode == 1:
            paths = Path(paths)
            total_time += mc_logs.count_playtime(paths, print_files='file')
        if mode == 2:
            for path in paths:
                total_time += mc_logs.count_playtime(path, print_files='full' if len(paths) > 1 else 'file')
        if mode == 3:
            for path in paths:
                if path.is_dir():
                    total_time += mc_logs.count_playtime(path, print_files='full')
        logger.info(f"Total Time: {total_time}")
        self.total_play_time = total_time

    def run(self):
        self.csv_data = {}
        self.graph_data_collection = {}
        logger.info("Starting log scanning...")

        if self.scan_mode == ScanMode.AUTOMATIC:
            default_logs_path = Path(
                'C:/Users', os.getlogin(), 'AppData/Roaming/.minecraft', 'logs'
            )

            if default_logs_path.exists():
                start_new_thread(
                    self.count_playtimes_thread, (),
                    {"paths": default_logs_path, "mode": self.scan_mode}
                )
                return
            # say that it did not exist
            else:
                logger.error(
                    "Could not automatically locate your .minecraft/logs folder"
                )

        elif self.scan_mode == ScanMode.MANUAL:
            paths_list = self.path_input.get().split("|")
            for path in paths_list:
                path = Path(path)
                if path.exists() is False:
                    logger.error(
                        f"The specified path does not exist: {path}"
                    )
                    return
            paths_list_ready = [Path(path) for path in paths_list]
            start_new_thread(
                self.count_playtimes_thread, (),
                {"paths": paths_list_ready, "mode": self.scan_mode}
            )

        elif self.scan_mode == ScanMode.GLOB:
            globs = self.path_input.get().split("|")
            glob_list = []
            for _glob in globs:
                for paths in iglob(_glob+"", recursive=True):
                    glob_list.append(Path(paths))
            for path in glob_list:
                if not path.exists():
                    logger.error(f"The specified paths does not exist: {path}")
                    return

            start_new_thread(
                self.count_playtimes_thread, (),
                {"paths": glob_list, "mode": self.scan_mode}
            )

    def exit(self):
        logger.info("Stopping scan...")
        return

    def create_graph(self):
        try:
            if self.graph_data_collection == {}:
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
            plt.title(f"Total playtime:\n{self.total_play_time}")
            plt.draw()
            plt.show()
        except Exception:
            logger.error(
                "An unexpected error occurred while creating the graph. "
                "Make sure that you have matplotlib installed!",
                error=True
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
