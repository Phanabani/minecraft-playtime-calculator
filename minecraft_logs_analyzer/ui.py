from __future__ import annotations
from _thread import start_new_thread
from csv import writer as csv_writher
from datetime import timedelta
from enum import IntEnum
from glob import iglob
import os
from pathlib import Path
from tkinter import *
from tkinter.colorchooser import *
from tkinter.scrolledtext import ScrolledText
import tkinter.ttk as ttk
# I import matplotlib in the module_not_found if it is not found otherwise in the matplotlib when building the gui we will see how that goes


class ScanMode(IntEnum):
    AUTOMATIC = 0
    MANUAL = 1
    GLOB = 2


class MinecraftLogsAnalyzerUI:

    background_color = '#23272A'
    outline_color= '#2C2F33'
    foreground_color = 'white'
    graph_color = '#18aaff'
    log_text_color = '#2C2F33'
    font = 'Helvetica 10'

    def __init__(self):
        self.root = Tk()
        self.csv_data = {}

        self.graph_data_collection = {}
        self.stop_scan = False
        try:
            from matplotlib import pyplot as plt
        except ImportError:
            plt = 0
            start_new_thread(module_not_found, ())

    def pack(self):
        root = self.root
        bg = self.background_color
        fg = self.foreground_color
        font = self.font

        root.title("Playtime calculator - By Quinten Cabo")
        root.config(bg=bg)

        frame = Frame(root, bg=bg)
        frame.pack()

        # mode selection
        modeText = Message(
            frame, text="Choose scan mode:", bg=bg, fg=fg,
            relief="groove", font=font
        )
        modeText.config(width=120)
        modeText.pack()

        s = ttk.Style()  # Creating style element
        s.configure(
            'Wild.TRadiobutton',  # First argument is the name of style. Needs to end with: .TRadiobutton
            background=bg,  # Setting background to our specified color above
            foreground=fg,
            font=font
        )  # You can define colors like this also

        self.scan_mode = IntVar(None, ScanMode.AUTOMATIC)
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
        pathText = Message(
            frame, text="(Separate input with '|')\nEnter path(s) / glob:",
            bg=bg, fg=fg, relief="groove", font=font
        )
        pathText.config(width=130, justify="center")
        pathText.pack()

        pathInput = StringVar()
        pathInput = Entry(
            frame, exportselection=0, textvariable=pathInput, state="disabled",
            cursor="arrow", bg="white", disabledbackground=bg, width=40,
            font=font
        )
        pathInput.pack()

        Message(frame, text="", bg=bg).pack()

        # run button
        submitButton = Button(
            frame, text="Run", command=self.run,
            cursor="hand2", bg=bg, fg=fg, font=font
        )
        submitButton.config(width=20)
        submitButton.pack()

        # graph button
        graphButton = Button(
            frame, text="Create graph", command=self.create_graph,
            cursor="hand2", bg=bg, fg=fg, font=font
        )
        graphButton.config(width=20)
        graphButton.pack()

        colorButton = Button(
            frame, text='Select Color', command=self.get_color,
            bg=self.graph_color, font=font
        )
        colorButton.config(width=20)
        colorButton.pack()

        # csv button
        graphButton = Button(
            frame, text="Export as csv", command=self.create_csv,
            cursor="hand2", bg=bg, fg=fg, font=font)
        graphButton.config(width=20)
        graphButton.pack()

        # output
        text = ScrolledText(
            frame, bg=self.log_text_color, fg="white", font="Helvetica 11"
        )
        text.config(width=120)
        text.pack()

        # exit button
        stopButton = Button(
            frame, text="Stop scanning", command=exit,
            width=20, bg=bg, fg=fg, font=font
        )
        stopButton.pack()

    def change_mode(self):
        global scan_mode
        scan_mode = mode.get()
        if scan_mode == 1:
            pathInput.config(state='disabled', cursor="arrow")
        else:
            pathInput.config(state='normal', cursor="hand2")
        insert("Changed mode to "+mode_dict[scan_mode])
        # probably put path detect here

    def insert(string_input, newline=True, error=False, scroll=True):  # to get text to output field
        string_input = str(string_input)
        if error == True:
            text.insert(END, "** ")
            text.insert(END, string_input.upper())
            text.insert(END, " **")
        if error == False:
            text.insert(END, string_input)
        if newline == True:
            text.insert(END, "\n")
        if scroll:
            text.see(END)
        return


    data_total_play_time = 0


    def count_playtimes_tread(paths,mode):
        global data_total_play_time
        total_time = timedelta()
        if mode == 1:
            paths = Path(paths)
            total_time += count_playtime(paths,print_files='file')
        if mode == 2:
            for path in paths:
                total_time += count_playtime(path,print_files='full' if len(paths) > 1 else 'file')
        if mode == 3:
            for path in paths:
                if path.is_dir():
                    total_time += count_playtime(path,print_files='full')
        insert("\nTotal Time:"+" "+str(total_time))
        data_total_play_time = total_time

    def run():
        global graph_data_collection,csv_data
        csv_data = {}
        graph_data_collection = {}
        insert("Starting log scanning...")
        if scan_mode == 0: # no input clicked yet
            insert("No mode selected, please select mode!")
            return
        elif scan_mode == 1:
            default_logs_path = Path('C:/Users', os.getlogin(),
                                     'AppData/Roaming/.minecraft', 'logs')

            if default_logs_path.exists():

                start_new_thread(count_playtimes_tread, tuple(), {"paths": default_logs_path, "mode": scan_mode})
                return
            # say that it did not exist
            else:
                insert("ERROR: Could not automatically locate your .minecraft/logs folder")

        elif scan_mode == 2: # files
            paths_list = pathInput.get().split("|")
            for path in paths_list:
                path = Path(path)
                if path.exists() == False:
                    insert("ERROR: One of your specified paths does not exit:")
                    insert(path, error=True)
                    return
            paths_list_ready = [Path(path) for path in paths_list]
            start_new_thread(count_playtimes_tread, tuple(), {"paths": paths_list_ready, "mode": scan_mode})

        elif scan_mode == 3: # glob
            globs = pathInput.get().split("|")
            glob_list = []
            for _glob in globs:
                for paths in iglob(_glob+"",recursive=True):
                    glob_list.append(Path(paths))
            for path in glob_list:
                if path.exists() == False:
                    insert("ERROR: One of your specified paths does not exit:")
                    insert(str(path), error=True)
                    return

            start_new_thread(count_playtimes_tread, tuple(), {"paths":glob_list,"mode":scan_mode})


    def exit():
        global stop_scan
        stop_scan = True
        insert("Stopping scan...")
        return


    def create_graph():
        global plt
        try:
            if graph_data_collection == {}:
                insert("Not enough data to create a graph, one full month is needed")
                return
            data_list_dates = [dates for dates in graph_data_collection]
            data_list_hour = [hours[1] for hours in graph_data_collection.items()]
            plt.bar(data_list_dates, data_list_hour,color=graph_color)

            plt.xticks(rotation='vertical')

            plt.xlabel("Months")
            plt.ylabel("Hours")
            plt.title("Total playtime:\n" + str(data_total_play_time))
            plt.draw()
            plt.show()
        except Exception as E:
            insert("An error ocured while creating the graph: "+str(E),error=True)
            insert("Try closing and opening the program\nMake sure that you have matplotlib installed!")


    def module_not_found():
        global plt
        if messagebox.askokcancel("Could not import Matplotlib module",'It looks like you do not have the matplotlib module installed\nWithout this module you can not make graphs\nInputing *pip install matplotlib* into the cmd will install it\n\nYou can also auto install by clicking ok'):
            insert("Attempting to install matplotlib...")
            os.system("pip install --user matplotlib")
        try:
            from matplotlib import pyplot as plt
            insert("Succesfully installed matplotlib!")

        except Exception as error:
            insert("Something may have gone wrong "+str(error))


    def get_color():
        global graph_color
        color = askcolor()
        graph_color = color[1]
        colorButton.config(bg=graph_color)
        insert("Color changed to "+graph_color)


    def create_csv():
        if len(csv_data) != 0:
            filename = filedialog.asksaveasfilename(initialdir="/desktop", title="Save file:",initialfile="minecraft_playtime.csv",
                                                    filetypes=(("csv files", "*.csv"), ("all files", "*.*")))
            with open(filename, newline='',mode="w+") as csvfile:
                writer = csv_writher(csvfile,delimiter=',')
                writer.writerow(["Day","Hours"])
                writer.writerows(csv_data.items())
        else:
            insert("Not enough data to create a csv file, make sure to start a scan first")

    root.mainloop()