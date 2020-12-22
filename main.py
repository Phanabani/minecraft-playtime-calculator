import wx

from minecraft_playtime_calculator import MinecraftPlaytimeCalculatorFrame

app = wx.App(redirect=False, useBestVisual=True)
frame = MinecraftPlaytimeCalculatorFrame(None)
app.MainLoop()
