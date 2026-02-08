import json, time, threading, sys
from ctypes import Structure, c_ulong, c_ushort, c_short, POINTER, windll
import win32api, win32con
import mss
import numpy as np
import cv2
import keyboard

# ===================== WinAPI SendInput =====================
PUL = POINTER(c_ulong)
class KEYBDINPUT(Structure):
    _fields_ = [("wVk", c_ushort), ("wScan", c_ushort),
                ("dwFlags", c_ulong), ("time", c_ulong), ("dwExtraInfo", PUL)]
class MOUSEINPUT(Structure):
    _fields_ = [("dx", c_long := c_long if 'c_long' in globals() else c_short),
                ("dy", c_long), ("mouseData", c_ulong),
                ("dwFlags", c_ulong), ("time", c_ulong), ("dwExtraInfo", PUL)]
class INPUT(Structure):
    class _I(Structure):
        _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]
    _anonymous_ = ("i",)
    _fields_ = [("type", c_ulong), ("i", _I)]

def click_fast():
    mi = MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTDOWN, 0, None)
    windll.user32.SendInput(1, INPUT(type=0, mi=mi), 40)
    mi = MOUSEINPUT(0, 0, 0, win32con.MOUSEEVENTF_LEFTUP, 0, None)
    windll.user32.SendInput(1, INPUT(type=0, mi=mi), 40)

def press_space():
    windll.user32.keybd_event(0x20, 0, 0, 0)
    windll.user32.keybd_event(0x20, 0, win32con.KEYEVENTF_KEYUP, 0)

# ===================== Overlay (OpenCV) =====================
class Overlay:
    def __init__(self):
        self.mode = "CONFIG"
        self.msg = ""
    def draw(self, canvas, geom):
        # Active rect
        x,y,w,h = geom.active_rect_px
        cv2.rectangle(canvas,(x,y),(x+w,y+h),(0,255,255),1)

        # Validation rings
        cx,cy = geom.center
        for r,col in [
            (geom.outer_r_px,(255,255,255)),
            (geom.blue_end_r_px,(255,200,0)),
            (geom.trigger_end_r_px,(0,255,0)),
            (geom.inner_hole_r_px,(0,0,255))
        ]:
            cv2.circle(canvas,(cx,cy),int(r),col,1)

        # Groups
        for gi,pts in enumerate(geom.group_points):
            for (px,py) in pts:
                cv2.circle(canvas,(px,py),2,(0,255-gi*60,255),-1)

        cv2.putText(canvas,f"MODE: {self.mode}",(10,20),
                    cv2.FONT_HERSHEY_SIMPLEX,0.6,(255,255,255),1)
        if self.msg:
            cv2.putText(canvas,self.msg,(10,45),
                        cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,255,255),1)

# ===================== Geometry =====================
class Geometry:
    def __init__(self, cfg):
        self.cfg = cfg
        self.update_from_screen()

    def update_from_screen(self):
        sw, sh = win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1)
        ar = self.cfg["active_rect"]
        self.active_rect_px = (
            int(ar["x"]*sw), int(ar["y"]*sh),
            int(ar["w"]*sw), int(ar["h"]*sh)
        )

        t = self.cfg["tor"]
        self.center = (
            int(self.active_rect_px[0] + self.active_rect_px[2]*t["center_px"]["x"]),
            int(self.active_rect_px[1] + self.active_rect_px[3]*t["center_px"]["y"])
        )

        base = min(self.active_rect_px[2], self.active_rect_px[3])
        self.outer_r_px = base * t["outer_r"]
        self.blue_end_r_px = base * t["blue_end_r"]
        self.trigger_end_r_px = base * t["trigger_end_r"]
        self.inner_hole_r_px = base * t["inner_hole_r"]

        # build groups (radial line downward)
        self.group_points = []
        offsets = self.cfg["groups"]["radial_offsets"]
        n = self.cfg["groups"]["pixels_per_group"]
        for off in offsets:
            r = base * (t["blue_end_r"] - off)
            pts=[]
            for i in range(n):
                pts.append((int(self.center[0]), int(self.center[1] + r + i)))
            self.group_points.append(pts)

# ===================== FSM =====================
class FSM:
    def __init__(self):
        self.state = 0
    def reset(self):
        self.state = 0
    def update(self, hits):
        # hits: [g1,g2,g3] booleans
        if self.state == 0 and hits[0]:
            self.state = 1
        elif self.state == 1 and hits[1]:
            self.state = 2
        elif self.state == 2 and hits[2]:
            self.state = 3
            return True
        elif (self.state == 1 and not hits[0]) or (self.state == 2 and not hits[1]):
            self.reset()
        return False

# ===================== Color check =====================
def pixel_hit(bgr, cfg):
    hsv = cv2.cvtColor(np.array([[bgr]],dtype=np.uint8), cv2.COLOR_BGR2HSV)[0][0]
    v = hsv[2]
    # any non-dark
    return v > cfg["colors"]["dark_threshold_v"]

# ===================== Main =====================
def main():
    cfg_path="config.json"
    cfg = json.load(open(cfg_path)) if os.path.exists(cfg_path) else None

    overlay = Overlay()
    fsm = FSM()
    test_mode = False
    running = True

    with mss.mss() as sct:
        while running:
            geom = Geometry(cfg)
            mon = {"left":geom.active_rect_px[0],
                   "top":geom.active_rect_px[1],
                   "width":geom.active_rect_px[2],
                   "height":geom.active_rect_px[3]}
            img = np.array(sct.grab(mon))[:,:,:3]

            # Overlay canvas
            canvas = img.copy()
            overlay.draw(canvas, geom)
            cv2.imshow("overlay", canvas)
            cv2.waitKey(1)

            # Read pixels
            hits=[]
            for grp in geom.group_points:
                h=False
                for (px,py) in grp:
                    bgr = img[py-mon["top"], px-mon["left"]]
                    if pixel_hit(bgr, cfg):
                        h=True; break
                hits.append(h)

            if fsm.update(hits):
                if test_mode: press_space()
                else: click_fast()
                fsm.reset()

            # Hotkeys
            if keyboard.is_pressed("pause"):
                running=False
            if keyboard.is_pressed("1"):
                test_mode = not test_mode
                time.sleep(0.3)

            time.sleep(0.001)

    cv2.destroyAllWindows()

if __name__=="__main__":
    main()
