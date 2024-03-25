import time
import logging
import threading
import ctypes

import hid
from PIL import Image, ImageDraw, ImageFont
import wx
from wx.adv import TaskBarIcon

ctypes.windll.shcore.SetProcessDpiAwareness(2)

MODEL = "Ninjutso Sora V2"
VID = 0x1915
PID_WIRELESS = 0xAE1C
PID_WIRED = 0xAE11
USAGE_PAGE = 0xFFA0

# Colors
RED = (255, 0, 0)
GREEN = (71, 255, 12)
BLUE = (91, 184, 255)
YELLOW = (255, 255, 0)

# Settings
poll_rate = 60
foreground_color = BLUE
background_color = (0, 0, 0, 0)
font = "consola.ttf"

logging.basicConfig(level=logging.INFO)


def get_path(device_list, usage_page):
    for device in device_list:
        if device['usage_page'] == usage_page:
            return device['path']


def get_device_list():
    device_list = hid.enumerate(VID, PID_WIRELESS)
    if not device_list:
        device_list = hid.enumerate(VID, PID_WIRED)
        if not device_list:
            raise RuntimeError(f"The specified device ({VID:X}:{PID_WIRELESS:X} or {VID:X}:{PID_WIRED:X}) cannot be found.")
    return device_list


def get_battery():
    device_list = get_device_list()
    path = get_path(device_list, USAGE_PAGE)
    logging.info(f"Device path: {path}")
    device = hid.device()
    device.open_path(path)
    report = [0] * 32
    report[0] = 5  # Report ID
    report[1] = 21
    report[4] = 1
    logging.info(f"Sending report:  {report}")
    device.send_feature_report(report)
    time.sleep(0.09)
    res = device.get_feature_report(5, 32)
    logging.info(f"Recieved report: {res}")
    device.close()
    battery = res[9]
    charging = res[10]
    full_charge = res[11]
    online = res[12]
    return battery, charging, full_charge, online


def create_icon(text: str, color, font):

    # Convert PIL Image to wxPython Bitmap
    def PIL2wx(image):
        width, height = image.size
        return wx.Bitmap.FromBufferRGBA(width, height, image.tobytes())

    def get_text_pos_size(text):
        if len(text) == 3:
            return (0, 28), 80
        elif len(text) == 2:
            return (4, 16), 110
        elif len(text) == 1:
            return (34, 16), 110

    image = Image.new(mode="RGBA", size=(128, 128), color=background_color)
    # Call draw Method to add 2D graphics in an image
    I1 = ImageDraw.Draw(image)
    # Custom font style and font size
    text_pos, size = get_text_pos_size(text)
    myFont = ImageFont.truetype(font, size)
    # Add Text to an image
    I1.text(text_pos, text, font=myFont, fill=color)
    return PIL2wx(image)


class MyTaskBarIcon(TaskBarIcon):

    def __init__(self, frame):
        super().__init__()
        self.frame = frame
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.OnClick)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        item_settings = wx.MenuItem(menu, wx.ID_ANY, "Settings")
        self.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=item_settings.GetId())
        item_exit = wx.MenuItem(menu, wx.ID_ANY, "Exit")
        self.Bind(wx.EVT_MENU, self.OnTaskBarExit, id=item_exit.GetId())
        # menu.Append(item_settings)
        menu.Append(item_exit)
        return menu

    def OnTaskBarActivate(self, event):
        if not self.frame.IsShown():
            self.frame.Show()

    def OnTaskBarExit(self, event):
        self.Destroy()
        self.frame.Destroy()

    def OnClick(self, event):
        if self.frame.battery_str == "Zzz":
            self.frame.show_battery()


class MyFrame(wx.Frame):

    def __init__(self, parent, title):
        super().__init__(parent, title=title, pos=(-1, -1), size=(290, 280))
        self.SetSize((350, 250))
        self.tray_icon = MyTaskBarIcon(self)
        self.show_battery()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Centre()

        self.thread = threading.Thread(target=self.thread_worker, daemon=True)
        self.thread.start()

    def OnClose(self, event):
        if self.IsShown():
            self.Hide()

    def show_battery(self):
        try:
            battery, charge, full_charge, online = get_battery()
            if not online:
                self.battery_str = "Zzz"
            else:
                self.battery_str = str(battery)
        except RuntimeError as e:
            logging.error(e)
            self.battery_str = "-"

        logging.info(f"Battery level obtained: {self.battery_str}")
        self.tray_icon.SetIcon(create_icon(self.battery_str, foreground_color, font),
                               "No Mouse Detected" if self.battery_str == "-" else MODEL)

    def thread_worker(self):
        while True:
            time.sleep(poll_rate)
            self.show_battery()


class MyApp(wx.App):

    def OnInit(self):
        frame = MyFrame(None, title='Sora Tray settings')
        frame.Show(False)
        self.SetTopWindow(frame)
        return True


def main():
    app = MyApp()
    app.MainLoop()


if __name__ == "__main__":
    main()
