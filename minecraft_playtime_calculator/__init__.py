import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(True)
except:
    pass

from .minecraft_logs import *
from .ui import MinecraftPlaytimeCalculatorFrame
