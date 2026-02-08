import json, time, os
from ctypes import Structure, c_ulong, c_ushort, POINTER, windll
import win32api, win32con
import mss
import numpy as np
import cv2
import keyboard

# ===================== WinAPI CLICK =====================
PUL = POINTER(c_ulong)

class MOUSEINPUT(Structure):
    _fields_ = [
        ("dx", c_ulong), ("dy", c_ulong),
        ("mouseData", c_ulong),
        ("dwFlags", c_ulong),
        ("time", c_ulong),
        ("dwExtraInfo", PUL)
    ]

class INPUT(Structure):
    _fields_ = [("type", c_ulong), ("mi", MOUSEINPUT)]

def click_fast():
    down = INPUT(0, MOUSEINPUT(0,0,0,win32con.MOUSEEVENTF_LEFTDOWN,0,None))
    up   = INPUT(0, MOUSEINPUT(0,0,0,win32con.MOUSEEVENTF_LEFTUP,0,None))
    windll.user32.SendInput(1, down, 40)
    windll.user32.SendInput(1, up, 40)

def press_space():
    windll.user32.keybd_event(0x20, 0, 0, 0)
    windll.user32.keybd_event(0x20, 0, win32con.KEYEVENTF_KEYUP, 0)

# ===================== FSM =====================
class FSM:
    def __init__(self):
        self.state = 0

    def reset(self):
        self.state = 0

    def update(self, hits):
        if self.state == 0 and hits[0]:
            self.state = 1
        elif self.state == 1 and hits[1]:
            self.state = 2
        elif self.state == 2 and hits[2]:
            self.reset()
            return True
        elif self.state > 0 and not hits[self.state-1]:
            self.reset()
        return False

# ===================== GEOMETRY =====================
class Geometry:
    def __init__(self, cfg):
        self.cfg = cfg
        self.update()

    def update(self):
        sw, sh = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        ar = self.cfg["active_rect"]

        self.ax = int(ar["x"] * sw)
        self.ay = int(ar["y"] * sh)
        self.aw = int(ar["w"] * sw)
        self.ah = int(ar["h"] * sh)

        t = self.cfg["tor"]
        self.cx = int(self.aw * t["center_px"]["x"])
        self.cy = int(self.ah * t["center_px"]["y"])

        base = min(self.aw, self.ah)
        self.outer_r = int(base * t["outer_r"])
        self.blue_end_r = int(base * t["blue_end_r"])
        self.trigger_end_r = int(base * t["trigger_end_r"])
        self.inner_r = int(base * t["inner_hole_r"])

        # build LOCAL pixel groups
        self.groups = []
        for off in self.cfg["groups"]["radial_offsets"]:
            r = int(self.blue_end_r - off * base)
            pts = []
            for i in range(self.cfg["groups"]["pixels_per_group"]):
                x = self.cx
                y = self.cy + r + i
                if 0 <= x < self.aw and 0 <= y < self.ah:
                    pts.append((x,y))
            self.groups.append(pts)

# ===================== COLOR =====================
def pixel_hit(bgr, cfg):
    v = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0][2]
    return v > cfg["colors"]["dark_threshold_v"]

# ===================== MAIN =====================
def main():
    cfg = json.load(open("config.json"))
    geom = Geometry(cfg)
    fsm = FSM()
    test_mode = False

    with mss.mss() as sct:
        while True:
            mon = {
                "left": geom.ax,
                "top": geom.ay,
                "width": geom.aw,
                "height": geom.ah
            }
            img = np.array(sct.grab(mon))[:,:,:3]

            # overlay
            vis = img.copy()
            for g in geom.groups:
                for x,y in g:
                    cv2.circle(vis,(x,y),2,(0,255,255),-1)

            cv2.imshow("overlay", vis)
            cv2.waitKey(1)

            hits = []
            for grp in geom.groups:
                hit = False
                for x,y in grp:
                    if pixel_hit(img[y,x], cfg):
                        hit = True
                        break
                hits.append(hit)

            if fsm.update(hits):
                press_space() if test_mode else click_fast()

            if keyboard.is_pressed("1"):
                test_mode = not test_mode
                time.sleep(0.3)

            if keyboard.is_pressed("pause"):
                break

            time.sleep(0.001)

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
