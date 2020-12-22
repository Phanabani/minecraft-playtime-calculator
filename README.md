# Minecraft Playtime Calculator

A cross-platform tool to calculate your play time in Minecraft.

![Application interface](assets/img/application_gui.png)

## Table of Contents

- [Running the program](#running-the-program)
    - [Windows](#windows)
    - [Mac / Linux](#mac--linux)
- [Usage](#usage)
- [Developers](#developers)
- [License](#license)

## Running the program

### Windows

Windows users may simply download and run the .exe file.

### Mac / Linux

Mac and Linux users can install and run this software using
[Python 3.7+](https://www.python.org/downloads/).

#### Installation

Download and extract the source code zip file either from the green download
button at the top of this page or from the releases page on the right.

Navigate to the source code you downloaded and run the file `setup.sh`. This
will set up a Python virtual environment, which is a self-contained Python
version with special packages needed to run this program. 

#### Running

After following the installation instructions above, run the file `run.sh` to
start the program.

## Usage

You must first run a scan to gather your play times. After the scan is complete,
you may either view a graph of your play time per month, or output the data
to a CSV file (for use in Microsoft Excel, for example).

Controls are located on the left, and program output is displayed on the right.

### Scanning modes

This program works by scanning Minecraft log files to determine when you
started and stopped playing the game. There are three modes for finding these
log files:

#### Automatic
Attempts to find logs at the default `.minecraft/logs` folder on your system.

#### Specify directories

You can manually specify (one or more) folders containing log files to scan.
This is useful if you play with modpacks and your game data is stored somewhere
else. You can specify multiple folders by separating them with a vertical bar `|`.

Example:

```
C:\Users\MyUsername\AppData\Roaming\.minecraft\logs | C:\Users\MyUsername\Twitch\Minecraft\Instances\Hexxit Updated\logs
```

#### Specify files / globs

You can manually specify individual log files to scan, by supplying either
absolute file paths or globs, with each separated by a vertical bar `|`.

Globs are special patterns for targeting multiple files. For example, `*.log`
will select any file ending with `.log` in a folder. Log files may also end with
`.log.gz` (compressed logs), so to select both types, you can use `*.log*`.
Globs may also search folders recursively with `**` (checks all folders inside
other folders inside other folders...).

A practical example using glob rules would be to find all log files across
multiple modpacks in the Twitch launcher:

```
C:\Users\MyUsername\Twitch\Minecraft\Instances\**\*.log*
```

This will search all folders (recursively) in the Twitch launcher data folder
for files that end with `.log` or `.log.gz`.

You could also add the main Minecraft folder to the search:

```
C:\Users\MyUsername\AppData\Roaming\.minecraft\logs\*.log* | C:\Users\MyUsername\Twitch\Minecraft\Instances\**\*.log*
```

## Developers

### Building

Pyinstaller can be used to build a binary of this app. Only tested on Windows,
but should hopefully work on other platforms.

```shell script
# Unix
source venv/bin/activate
# Windows
venv\Scripts\activate.bat

python -m pip install pyinstaller
pyinstaller --clean -p venv\Lib\site-packages -p minecraft_playtime_calculator --windowed --onefile -n minecraft_playtime_calculator --icon assets/img/icon.ico -y main.py
```

Binary will be output in `./dist`.

## License

[MIT © Quinten Cabo & Hawkpath.](LICENSE)
