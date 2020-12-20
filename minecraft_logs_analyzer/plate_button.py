import wx
from wx.lib.platebtn import *
import wx.lib.newevent
from wx.lib.colourutils import *

PlateButtonBase = PlateButton


class PlateButton(PlateButtonBase):

    def __DrawBitmap(self, gc):
        """Draw the bitmap if one has been set

        :param wx.GCDC `gc`: :class:`wx.GCDC` to draw with
        :return: x cordinate to draw text at

        """
        if self.IsEnabled():
            bmp = self._bmp['enable']
        else:
            bmp = self._bmp['disable']

        if bmp is not None and bmp.IsOk():
            bw, bh = bmp.GetSize()
            ypos = (self.GetSize()[1] - bh) // 2
            gc.DrawBitmap(bmp, 6, ypos, bmp.GetMask() is not None)
            return bw + 6
        else:
            return 0

    def __DrawButton(self):
        """Draw the button"""
        # TODO using a buffered paintdc on windows with the nobg style
        #      causes lots of weird drawing. So currently the use of a
        #      buffered dc is dissabled for this style.
        if PB_STYLE_NOBG & self._style:
            dc = wx.PaintDC(self)
        else:
            dc = wx.AutoBufferedPaintDCFactory(self)

        gc = wx.GCDC(dc)

        # Setup
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetBrush(wx.TRANSPARENT_BRUSH)
        gc.SetFont(self.Font)
        dc.SetFont(self.Font)
        gc.SetBackgroundMode(wx.TRANSPARENT)

        # The background needs some help to look transparent on
        # on Gtk and Windows
        if wx.Platform in ['__WXGTK__', '__WXMSW__']:
            gc.SetBackground(self.GetBackgroundBrush(gc))
            gc.Clear()

        # Calc Object Positions
        width, height = self.GetSize()
        if wx.Platform == '__WXGTK__':
            tw, th = dc.GetTextExtent(self.Label)
        else:
            tw, th = gc.GetTextExtent(self.Label)
        txt_y = max((height - th) // 2, 1)

        if self._state['cur'] == PLATE_HIGHLIGHT:
            gc.SetTextForeground(self._color['htxt'])
            gc.SetPen(wx.TRANSPARENT_PEN)
            self.__DrawHighlight(gc, width, height)

        elif self._state['cur'] == PLATE_PRESSED:
            gc.SetTextForeground(self._color['htxt'])
            if wx.Platform == '__WXMAC__':
                pen = wx.Pen(GetHighlightColour(), 1, wx.PENSTYLE_SOLID)
            else:
                pen = wx.Pen(AdjustColour(self._color['press'], -80, 220), 1)
            gc.SetPen(pen)

            self.__DrawHighlight(gc, width, height)
            bmp_right = self.__DrawBitmap(gc)
            txt_x = bmp_right + ((width - bmp_right) // 2) - (tw // 2)
            if wx.Platform == '__WXGTK__':
                dc.DrawText(self.Label, txt_x, txt_y)
            else:
                gc.DrawText(self.Label, txt_x, txt_y)
            self.__DrawDropArrow(gc, width - 10, (height // 2) - 2)

        else:
            if self.IsEnabled():
                gc.SetTextForeground(self.GetForegroundColour())
            else:
                txt_c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
                gc.SetTextForeground(txt_c)

        # Draw bitmap and text
        if self._state['cur'] != PLATE_PRESSED:
            bmp_right = self.__DrawBitmap(gc)
            txt_x = bmp_right + ((width - bmp_right) // 2) - (tw // 2)
            if wx.Platform == '__WXGTK__':
                dc.DrawText(self.Label, txt_x, txt_y)
            else:
                gc.DrawText(self.Label, txt_x, txt_y)
            self.__DrawDropArrow(gc, width - 10, (height // 2) - 2)
