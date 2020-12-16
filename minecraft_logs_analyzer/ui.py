from __future__ import annotations
from _thread import start_new_thread
from csv import writer as csv_writer
from datetime import timedelta
from enum import IntEnum
from glob import iglob
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


class ScanMode(IntEnum):
    AUTOMATIC = 0
    MANUAL = 1
    GLOB = 2


class MinecraftLogsAnalyzerUI:

    background_color = '#23272A'
    outline_color = '#2C2F33'
    foreground_color = 'white'
    graph_color = '#18aaff'
    log_text_color = '#2C2F33'
    font = 'Helvetica 10'

    log: ScrolledText

    def __init__(self):
        self.root = Tk()
        self.csv_data = {}

        self.graph_data_collection = {}
        self.total_play_time = None

        self.scan_mode = IntVar(None, ScanMode.AUTOMATIC)
        self.path = StringVar()
        self._pack()
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
        self.log = ScrolledText(
            frame, bg=self.log_text_color, fg="white", font="Helvetica 11"
        )
        self.log.config(width=120)
        self.log.pack()

        # exit button
        stop_button = Button(
            frame, text="Stop scanning", command=exit,
            width=20, bg=bg, fg=fg, font=font
        )
        stop_button.pack()

    def change_mode(self):
        scan_mode = self.scan_mode.get()
        if scan_mode == ScanMode.MANUAL:
            self.path_input.config(state='disabled', cursor="arrow")
        else:
            self.path_input.config(state='normal', cursor="hand2")
        self.insert(f"Changed mode to {ScanMode(scan_mode)._name_.lowercase()}")
        # probably put path detect here

    def insert(self, string_input: Any, newline=True, error=False, scroll=True):  # to get text to output field
        string_input = str(string_input)
        log = self.log

        if error:
            log.insert(END, "** ")
            log.insert(END, string_input.upper())
            log.insert(END, " **")
        else:
            log.insert(END, string_input)
        if newline:
            log.insert(END, "\n")
        if scroll:
            log.see(END)

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
        self.insert(f"\nTotal Time: {total_time}")
        self.total_play_time = total_time

    def run(self):
        self.csv_data = {}
        self.graph_data_collection = {}
        self.insert("Starting log scanning...")

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
                self.insert("ERROR: Could not automatically locate your .minecraft/logs folder")

        elif self.scan_mode == ScanMode.MANUAL:
            paths_list = self.path_input.get().split("|")
            for path in paths_list:
                path = Path(path)
                if path.exists() is False:
                    self.insert("ERROR: One of your specified paths does not exit:")
                    self.insert(path, error=True)
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
                    self.insert("ERROR: One of your specified paths does not exit:")
                    self.insert(str(path), error=True)
                    return

            start_new_thread(
                self.count_playtimes_thread, (),
                {"paths": glob_list, "mode": self.scan_mode}
            )

    def exit(self):
        self.insert("Stopping scan...")
        return

    def create_graph(self):
        try:
            if self.graph_data_collection == {}:
                self.insert("Not enough data to create a graph, one full month is needed")
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
            self.insert("An error ocured while creating the graph: ", error=True)
            self.insert("Try closing and opening the program\n"
                        "Make sure that you have matplotlib installed!")

    def get_color(self):
        color = askcolor()
        self.graph_color = color[1]
        self.color_button.config(bg=self.graph_color)
        self.insert(f"Color changed to {self.graph_color}")

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
            self.insert("Not enough data to create a csv file, make sure to start a scan first")
