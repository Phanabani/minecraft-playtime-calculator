# Minecraft Playtime Calculator

A cross-platform tool to calculate your play time in Minecraft.

## Table of Contents

- [Running the program](#running-the-program)
    - [Windows](#windows)
    - [Mac / Linux](#mac--linux)
- [Usage](#usage)
- [License](#license)

## Running the program

### Windows

Windows users may simply download and run the .exe file.

You can also follow the cross-platform instructions [below](#mac--linux) to run
using Python. The only difference is you need to run `venv\Scripts\activate.bat`
instead of `source venv/bin/activate` to activate the virtual environment.

### Mac / Linux

Mac and Linux users can install and run this software using
[Python 3.7+](https://www.python.org/downloads/).

#### Installation

Download and extract the source code zip file either from the green download
button at the top of this page or from the releases page on the right.

Open the Terminal and navigate to the folder with the extracted source code
you downloaded:

```shell script
cd path/to/minecraft-playtime-calculator
```

We will now create a virtual environment, which is basically a self-contained
version of Python, and install important Python packages for running the
program.

```shell script
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

This should have created a new folder called `venv` and installed the packages
we need!

#### Running

After following the installation instructions above, you should be able to run
the program now!

To do so, open the Terminal and run the following commands:

```shell script
cd path/to/minecraft-playtime-calculator
source venv/bin/activate
python main.py
```

This navigates to the source code folder, activates the virtual environment with
the packages we need to run the program, and uses the Python version in the
virtual environment to run `main.py`, the file which starts the program.

## Usage

## License

There are 3 modes:

[1] Automatic (default)
[2] Enter path(s)
[3] Enter glob

1: Automatic trys to detect your logs in the normal minecraft folder 
C:/Users/USER/AppData/Roaming/.minecraft/logs

2: With this mode you can enter your own file paths
Separate multiple paths with pipes (vertical bar: | ).

3: With glob you can enter a glob to select multiple folders in a directory,
glob will basically select your path but also all the paths of any subdirectories that might exist in your spicified path and that match the glob
Separate multiple globs with pipes (vertical bar: | ). Make sure files don't overlap

Folders that start with period must be explicitly specified
(AppData/Roaming/.*/logs)

Glob-Example: To find all logs folders in all folders that start with . in AppData,
C:/Users/USER/AppData/Roaming/.*/**
This would select all the logs in .minecraft but also in .technic for instance

Globs can take a bit to load if your selection is large

You can read more about globs here: https://pymotw.com/3/glob/

This is how it all looks: https://imgur.com/a/ZuV0CCW

Results
--------------
You can export the results into 2 ways
- A graph with hours per month
- A csv file with hours per session

This next part is only for those who use the .pyw version
-----------------------------------------------------------------------------------------------
Atleast python 3.6 is required for this program to work it might work on python 3.5 but I have not tested that

(I now added python 3.7 and 3.8 support)

This program uses matplotlib pyplot to create graphs. If you do not have matplotlib installed please install it by entering the flowing command into the cmd:
pip install matplotlib

If that does not work try to reinstall python and make sure to click the install pip option

The program will also detect if you do not have matplotlib installed and it will ask you if you want to auto install
This will basicly run os.system("pip install matplotlib") this is about the same as running "pip install matplotlib" in the cmd
