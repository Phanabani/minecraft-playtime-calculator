import wx

from .ui import MinecraftLogsAnalyzerFrame

if __name__ == '__main__':
    app = wx.App(redirect=False, useBestVisual=True)
    frame = MinecraftLogsAnalyzerFrame()
    app.MainLoop()
