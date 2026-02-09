import json, time, os
import win32api, win32con
from ctypes import Structure, c_ulong, POINTER, windll
import mss, cv2, keyboard
import numpy as np

# ================= CLICK =================
PUL = POINTER(c_ulong)

class MOUSEINPUT(Structure):
    _fields_=[("dx",c_ulong),("dy",c_ulong),("mouseData",c_ulong),
              ("dwFlags",c_ulong),("time",c_ulong),("dwExtraInfo",PUL)]
class INPUT(Structure):
    _fields_=[("type",c_ulong),("mi",MOUSEINPUT)]

def click_fast():
    windll.user32.SendInput(1, INPUT(0,MOUSEINPUT(0,0,0,2,0,None)), 40)
    windll.user32.SendInput(1, INPUT(0,MOUSEINPUT(0,0,0,4,0,None)), 40)

def press_space():
    windll.user32.keybd_event(0x20,0,0,0)
    windll.user32.keybd_event(0x20,0,2,0)

# ================= FSM =================
class FSM:
    def __init__(self): self.s=0
    def reset(self): self.s=0
    def step(self,h):
        if self.s==0 and h[0]: self.s=1
        elif self.s==1 and h[1]: self.s=2
        elif self.s==2 and h[2]: self.reset(); return True
        elif self.s>0 and not h[self.s-1]: self.reset()
        return False

# ================= MAIN =================
def main():
    cfg=json.load(open("config.json"))
    fsm=FSM()
    test=False
    mode="CONFIG"

    sw,sh=win32api.GetSystemMetrics(0),win32api.GetSystemMetrics(1)

    with mss.mss() as sct:
        cv2.namedWindow("overlay", cv2.WND_PROP_FULLSCREEN)
        cv2.setWindowProperty("overlay", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

        while True:
            ar=cfg["active_rect"]
            ax=int(ar["x"]*sw); ay=int(ar["y"]*sh)
            aw=int(ar["w"]*sw); ah=int(ar["h"]*sh)

            base=min(aw,ah)
            tor=cfg["tor"]
            cx=ax+int(aw*tor["center_px"]["x"])
            cy=ay+int(ah*tor["center_px"]["y"])

            overlay=np.zeros((sh,sw,3),np.uint8)

            # active rect
            cv2.rectangle(overlay,(ax,ay),(ax+aw,ay+ah),(0,255,255),1)

            # rings
            for r,c in [
                (tor["outer_r"],(255,255,255)),
                (tor["blue_end_r"],(255,200,0)),
                (tor["trigger_end_r"],(0,255,0)),
                (tor["inner_hole_r"],(0,0,255))
            ]:
                cv2.circle(overlay,(cx,cy),int(base*r),c,1)

            # groups
            for gi,off in enumerate(cfg["groups"]["radial_offsets"]):
                rr=int(base*(tor["blue_end_r"]-off))
                for i in range(cfg["groups"]["pixels_per_group"]):
                    cv2.circle(overlay,(cx,cy+rr+i),2,(0,255-gi*60,255),-1)

            cv2.putText(overlay,f"MODE: {mode}",(30,40),
                        cv2.FONT_HERSHEY_SIMPLEX,1,(255,255,255),2)

            cv2.imshow("overlay",overlay)
            cv2.waitKey(1)

            # controls
            if keyboard.is_pressed("left"):  ar["x"]-=0.001
            if keyboard.is_pressed("right"): ar["x"]+=0.001
            if keyboard.is_pressed("up"):    ar["y"]-=0.001
            if keyboard.is_pressed("down"):  ar["y"]+=0.001
            if keyboard.is_pressed("+"): ar["w"]+=0.001; ar["h"]+=0.001
            if keyboard.is_pressed("-"): ar["w"]-=0.001; ar["h"]-=0.001

            if keyboard.is_pressed("enter"):
                mode="MONITOR" if mode=="CONFIG" else "CONFIG"
                time.sleep(0.3)

            if keyboard.is_pressed("1"):
                test=not test; time.sleep(0.3)

            if keyboard.is_pressed("pause"):
                break

            time.sleep(0.01)

    cv2.destroyAllWindows()
    json.dump(cfg,open("config.json","w"),indent=2)

if __name__=="__main__":
    main()
