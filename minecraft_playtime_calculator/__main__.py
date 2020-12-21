import wx

from .ui import MinecraftPlaytimeCalculatorFrame

if __name__ == '__main__':
    app = wx.App(redirect=False, useBestVisual=True)
    frame = MinecraftPlaytimeCalculatorFrame()
    app.MainLoop()
