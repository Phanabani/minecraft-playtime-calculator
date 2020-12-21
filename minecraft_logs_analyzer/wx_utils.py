import logging
from typing import *

import wx
import wx.lib.newevent

__all__ = [
    'create_panel_with_margin',
    'get_font', 'get_system_fonts', 'try_get_font',
    'WxLogEvent', 'EVT_WX_LOG_EVENT', 'WxLogHandler'
]


def create_panel_with_margin(parent: wx.Window, margin: int):
    margin_panel = wx.Panel(parent)
    margin_sizer = wx.BoxSizer()
    margin_panel.SetSizer(margin_sizer)

    panel = wx.Panel(margin_panel)
    margin_sizer.Add(panel, 1, wx.ALL | wx.EXPAND, margin)
    return panel


def get_font(face_name: str = '', font_size: int = 10):
    return wx.Font(
        font_size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_NORMAL, faceName=face_name
    )


def get_system_fonts(monospace=False):
    fonts = wx.FontEnumerator()
    fonts.EnumerateFacenames(wx.FONTENCODING_SYSTEM, fixedWidthOnly=monospace)
    return fonts.GetFacenames(wx.FONTENCODING_SYSTEM, fixedWidthOnly=monospace)


def try_get_font(
        face_names: Union[str, List[str]], font_size: int,
        monospace: bool = False
):
    if isinstance(face_names, str):
        face_names = [face_names]
    fonts = get_system_fonts(monospace)

    for face_name in face_names:
        if face_name in fonts:
            # This font exists! Yay!
            return get_font(face_name, font_size)

    if len(fonts) > 0:
        # Fallback to first font in the list
        return get_font(fonts[0], font_size)

    # Mega fallback, just get whatever font we can
    return get_font('', font_size)


WxLogEvent, EVT_WX_LOG_EVENT = wx.lib.newevent.NewEvent()


class WxLogHandler(logging.Handler):

    def __init__(self, destination: wx.Window, level: int = logging.NOTSET):
        super().__init__(level=level)
        self.destination = destination

    def flush(self):
        pass

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            evt = WxLogEvent(message=msg, levelname=record.levelname)
            wx.PostEvent(self.destination, evt)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)
