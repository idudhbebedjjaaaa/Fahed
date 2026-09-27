# -*- coding: utf-8 -*-
"""Laundry cabinet design generator.
All dimensions are in centimetres and come from the single model below.
Every derived number is checked with assertions before any drawing is produced.
"""
import base64, os, html, re, math

HERE = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------ model
T = 1.8            # board thickness (Egger H309 ST12, 18 mm)
HDF = 0.8          # back panel / drawer bottom (HDF 8 mm)
GAP = 0.3          # gap between doors / door reveal

RECESS_W, RECESS_H, RECESS_D = 113.0, 264.0, 60.0
CAB_W = 112.0                        # cabinet size given by the owner: 0.5 cm to each wall
CAB_H = 263.0                        # 1 cm to the ceiling, enough to stand the side panels up
PANEL_D = 59.2                       # side panels depth
CAB_D = PANEL_D + HDF                # 60.0 carcass incl. back
DOOR_PROUD = CAB_D + T               # 61.8 from wall to door face

LEFT_IN = 44.6                       # left column clear width
NICHE_IN = 62.0                      # machine niche clear width: 1 cm each side of a 60 cm machine
PLINTH = 10.0
PLINTH_SETBACK = 5.0

# x positions (from left outer face)
X_LS = 0.0
X_LC0, X_LC1 = T, T + LEFT_IN                     # 1.8 .. 46.4
X_DIV0, X_DIV1 = X_LC1, X_LC1 + T                 # 46.4 .. 48.2
X_N0, X_N1 = X_DIV1, X_DIV1 + NICHE_IN            # 48.2 .. 110.2
X_RS0, X_RS1 = X_N1, X_N1 + T                     # 110.2 .. 112.0

# heights (bottom face of each board, from floor)
H_BOTTOM = PLINTH                    # left bottom panel 10 .. 11.8
H_FIX1 = 81.8                        # fixed shelf above drawers
H_FIX2 = 180.0                       # fixed shelf / upper cabinet bottom
H_TOP = CAB_H - T                    # 261.2 top panel
NICHE_H = H_FIX2                     # 180 clear height for machines

# adjustable shelves: equal spacing
zoneB0, zoneB1 = H_FIX1 + T, H_FIX2                    # 83.6 .. 180
spB = (zoneB1 - zoneB0 - 2 * T) / 3
ADJ_B = [zoneB0 + spB, zoneB0 + 2 * spB + T]
zoneC0, zoneC1 = H_FIX2 + T, H_TOP                     # 181.8 .. 260.2
spC = (zoneC1 - zoneC0 - T) / 2
ADJ_C = zoneC0 + spC

# doors
DOOR_BOT_L = PLINTH
DOOR_TOP = CAB_H - GAP                                  # 262.7: 3 mm under the top of the cabinet
DOOR_L_W = 47.0
DOOR_R_W = 32.1
DOOR_L_H = DOOR_TOP - DOOR_BOT_L                        # 252.7
DOOR_R_H = DOOR_TOP - H_FIX2                            # 82.7
XD_L0 = 0.1; XD_L1 = XD_L0 + DOOR_L_W                   # 0.1 .. 47.1
XD_R10 = XD_L1 + GAP; XD_R11 = XD_R10 + DOOR_R_W        # 47.4 .. 79.5
XD_R20 = XD_R11 + GAP; XD_R21 = XD_R20 + DOOR_R_W       # 79.8 .. 111.9

# drawers
SPACER = T + HDF                                        # 2.6
DR_CLEAR = LEFT_IN - SPACER                             # 42.0
SLIDE = 1.3
BOX_W = round(DR_CLEAR - 2 * SLIDE, 1)                  # 39.4
BOX_D = 50.0
BOX_H = 30.0
FRONT_W = round(DR_CLEAR - 0.4, 1)                      # 41.6
FRONT_H = 34.5
FRONT_SETBACK = 2.5
F1 = (H_BOTTOM + T + GAP, H_BOTTOM + T + GAP + FRONT_H)  # 12.1 .. 46.6
F2 = (F1[1] + 0.4, F1[1] + 0.4 + FRONT_H)               # 47.0 .. 81.5
BOX1 = (F1[0] + 1.4, F1[0] + 1.4 + BOX_H)               # 13.5 .. 43.5
BOX2 = (F2[0] + 1.4, F2[0] + 1.4 + BOX_H)               # 48.4 .. 78.4
SLIDE_C = [28.5, 55.0]                                  # slide centre lines from floor

# hinges (distance from door bottom edge)
HINGE_L = [10.0, 58.0, 96.0, 150.0, 195.0, round(DOOR_L_H - 10, 1)]
HINGE_R = [10.0, round(DOOR_R_H - 10, 1)]

# machines (standard European front loaders)
M_W, M_H, M_D = 60.0, 85.0, 60.0
KIT = 2.0
SIDE_CLR = (NICHE_IN - M_W) / 2                         # 1.0 cm each side
MX = X_N0 + SIDE_CLR                                    # machine left edge, centred in the niche

# ------------------------------------------------------------ assertions
def eq(a, b, msg):
    assert abs(a - b) < 0.051, f"{msg}: {a} != {b}"

eq(X_RS1, CAB_W, "widths add up to cabinet width")
eq(RECESS_W - CAB_W, 1.0, "0.5 cm to each wall")
eq(DOOR_TOP, CAB_H - 0.3, "doors stop 3 mm under the cabinet top")
assert math.hypot(CAB_H, T) <= RECESS_H - 0.9, "a side panel can be tipped upright under the ceiling"
eq(CAB_D, RECESS_D, "carcass depth fills recess")
eq(H_TOP, 261.2, "top panel height")
eq(DOOR_L_H, 252.7, "left door height")
eq(DOOR_R_H, 82.7, "right door height")
eq(XD_R21, CAB_W - 0.1, "door row ends 1 mm inside cabinet")
assert XD_L1 > X_DIV0 and XD_L1 < (X_DIV0 + X_DIV1) / 2, "left door overlaps half of divider"
assert XD_R10 > (X_DIV0 + X_DIV1) / 2 and XD_R10 < X_DIV1, "right door overlaps half of divider"
eq(ADJ_B[1] + T + spB, zoneB1, "zone B spacing closes")
eq(ADJ_C + T + spC, zoneC1, "zone C spacing closes")
assert F2[1] + GAP <= H_FIX1 + 0.001, "upper drawer front under fixed shelf"
assert BOX2[1] < H_FIX1 - 3, "upper box has lift clearance"
assert FRONT_SETBACK + T + BOX_D < PANEL_D, "drawer fits in depth"
assert SIDE_CLR >= 1.0, "at least 1 cm each side of the machines"
assert 2 * M_H + KIT + 5 <= NICHE_H, "5 cm above stacked machines"
for hh in HINGE_L:  # no hinge plate (±3 cm) on a fixed board
    a = DOOR_BOT_L + hh
    for b in (H_BOTTOM, H_FIX1, H_FIX2, ADJ_B[0], ADJ_B[1], ADJ_C, H_TOP):
        assert not (b - 3 < a < b + T + 3), f"hinge {a} hits board {b}"
    for sc in SLIDE_C:
        assert abs(a - sc) > 5, f"hinge {a} vs slide {sc}"
assert DOOR_L_H < 280 and CAB_H < 280, "longest parts fit a 280 cm board"

def f1(v):
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s

# --------------------------------------------------------------- svg kit
WOOD = base64.b64encode(open(os.path.join(HERE, "wood.jpg"), "rb").read()).decode()

class S:
    def __init__(self, x0, y0, w, h, ground):
        self.x0, self.y0, self.w, self.h, self.g = x0, y0, w, h, ground
        self.p = []
        self.k = 1.0
    def Y(self, v):
        return self.g - v
    def add(self, s):
        self.p.append(s)
    def rect(self, x, y, w, h, cls, extra=""):
        self.add(f'<rect x="{x:.2f}" y="{self.Y(y + h):.2f}" width="{w:.2f}" height="{h:.2f}" class="{cls}" {extra}/>')
    def line(self, x1, y1, x2, y2, cls):
        self.add(f'<line x1="{x1:.2f}" y1="{self.Y(y1):.2f}" x2="{x2:.2f}" y2="{self.Y(y2):.2f}" class="{cls}"/>')
    def text(self, x, y, s, cls="t", anchor="middle", rot=0, size=None):
        base = {"dt": 3, "lv": 2.9, "lbl": 3, "lbl small": 2.5, "lbl onwood": 3, "doortxt": 3.4, "mt": 3}
        fs = size if size else (base.get(cls.replace(" num", ""), 3) if self.k != 1 else None)
        st = f' style="font-size:{fs * self.k:.2f}px"' if fs else ""
        tr = f' transform="rotate({rot} {x:.2f} {self.Y(y):.2f})"' if rot else ""
        anchor = {"left": "end", "right": "start"}.get(anchor, anchor)  # svg text runs rtl
        self.add(f'<text x="{x:.2f}" y="{self.Y(y):.2f}" class="{cls}" text-anchor="{anchor}"{tr}{st}>{html.escape(str(s))}</text>')
    def wood(self, x, y, w, h):
        self.add(f'<image href="data:image/jpeg;base64,{WOOD}" x="{x:.2f}" y="{self.Y(y + h):.2f}" width="{w:.2f}" height="{h:.2f}" preserveAspectRatio="none"/>')
    def hdim(self, x1, x2, y, label=None, ext_from=None, cls="dim"):
        """horizontal dimension at height y; ext_from = height the extension lines start at"""
        if ext_from is not None:
            for x in (x1, x2):
                self.line(x, ext_from, x, y + (1.2 if y > ext_from else -1.2), "ext")
        self.line(x1, y, x2, y, cls)
        for x in (x1, x2):
            self.add(f'<line x1="{x - 0.9:.2f}" y1="{self.Y(y) + 0.9:.2f}" x2="{x + 0.9:.2f}" y2="{self.Y(y) - 0.9:.2f}" class="{cls} tick"/>')
        self.text((x1 + x2) / 2, y + 1.0, label if label is not None else f1(abs(x2 - x1)), "dt")
    def vdim(self, x, y1, y2, label=None, ext_from=None, cls="dim", side=-1):
        if ext_from is not None:
            for y in (y1, y2):
                self.line(ext_from, y, x + (1.2 if x > ext_from else -1.2), y, "ext")
        self.line(x, y1, x, y2, cls)
        for y in (y1, y2):
            self.add(f'<line x1="{x - 0.9:.2f}" y1="{self.Y(y) + 0.9:.2f}" x2="{x + 0.9:.2f}" y2="{self.Y(y) - 0.9:.2f}" class="{cls} tick"/>')
        tx = x + (1.0 if side > 0 else -1.0)
        self.text(tx, (y1 + y2) / 2, label if label is not None else f1(abs(y2 - y1)), "dt", rot=-90)
    def svg(self, title, minw=560):
        return (f'<svg viewBox="{self.x0} {self.y0} {self.w} {self.h}" role="img" aria-label="{html.escape(title)}" '
                f'style="min-width:{minw}px" xmlns="http://www.w3.org/2000/svg">' + "".join(self.p) + "</svg>")

def carcass(s, show_adj=True):
    # side panels, divider, top
    s.rect(X_LS, 0, T, CAB_H, "board")
    s.rect(X_DIV0, 0, T, H_TOP, "board")
    s.rect(X_RS0, 0, T, CAB_H, "board")
    s.rect(T, H_TOP, CAB_W - 2 * T, T, "board")
    # left column
    s.rect(X_LC0 + 0.0, 0, LEFT_IN, PLINTH, "plinth")
    s.rect(X_LC0, H_BOTTOM, LEFT_IN, T, "board")
    s.rect(X_LC0, H_FIX1, LEFT_IN, T, "board")
    s.rect(X_LC0, H_FIX2, LEFT_IN, T, "board")
    if show_adj:
        for h in ADJ_B + [ADJ_C]:
            s.rect(X_LC0, h, LEFT_IN, T, "adj")
        s.rect(X_N0, ADJ_C, NICHE_IN, T, "adj")
    # upper right
    s.rect(X_N0, H_FIX2, NICHE_IN, T, "board")

def machines(s, x0, alpha=False):
    cls = "mach"
    s.rect(x0, 0, M_W, M_H, cls)
    s.rect(x0, M_H, M_W, KIT, "kit")
    s.rect(x0, M_H + KIT, M_W, M_H, cls)
    for base, name in ((0, "غسالة"), (M_H + KIT, "نشافة")):
        s.rect(x0, base + M_H - 12, M_W, 12, "machpanel")
        cx, cy = x0 + M_W / 2, base + 36
        s.add(f'<circle cx="{cx:.2f}" cy="{s.Y(cy):.2f}" r="17" class="machdoor"/>')
        s.add(f'<circle cx="{cx:.2f}" cy="{s.Y(cy):.2f}" r="12.5" class="machglass"/>')
        s.text(cx, base + M_H - 7.8, name, "mt")

# ---------------------------------------------------------------- sheet 1
def sheet_front_closed():
    s = S(-42, -4, 196, 300, 272)
    # recess walls hatch
    s.rect(-8, 0, 8, RECESS_H + 6, "wall")
    s.rect(RECESS_W, 0, 8, RECESS_H + 6, "wall")
    s.rect(-8, RECESS_H, RECESS_W + 16, 6, "wall")
    s.rect(0, 0, RECESS_W, RECESS_H, "void")
    s.line(-12, 0, RECESS_W + 12, 0, "floor")
    ox = (RECESS_W - CAB_W) / 2  # 0.5 cm to each wall
    def X(v):
        return v + ox
    # carcass silhouette and interior of niche
    s.rect(X(0), 0, CAB_W, CAB_H, "carc")
    s.rect(X(X_N0), 0, NICHE_IN, NICHE_H, "niche")
    machines(s, X(MX))
    s.rect(X(X_DIV0), 0, T, NICHE_H, "edge")
    s.rect(X(X_RS0), 0, T, NICHE_H, "edge")
    s.rect(X(X_LC0), 0, LEFT_IN, PLINTH, "plinthshadow")
    s.rect(X(X_LS), 0, T, DOOR_BOT_L, "edge")
    # doors
    for (x0, x1, b, h) in ((XD_L0, XD_L1, DOOR_BOT_L, DOOR_L_H), (XD_R10, XD_R11, H_FIX2, DOOR_R_H), (XD_R20, XD_R21, H_FIX2, DOOR_R_H)):
        s.wood(X(x0), b, x1 - x0, h)
        s.rect(X(x0), b, x1 - x0, h, "door")
    # hinge side marks (dashed triangle: apex at hinge side)
    def swing(x0, x1, b, h, hinge_left):
        hx = x0 if hinge_left else x1
        fx = x1 if hinge_left else x0
        s.add(f'<polyline points="{X(fx):.2f},{s.Y(b + h):.2f} {X(hx):.2f},{s.Y(b + h / 2):.2f} {X(fx):.2f},{s.Y(b):.2f}" class="swing"/>')
    swing(XD_L0, XD_L1, DOOR_BOT_L, DOOR_L_H, True)
    swing(XD_R10, XD_R11, H_FIX2, DOOR_R_H, True)
    swing(XD_R20, XD_R21, H_FIX2, DOOR_R_H, False)
    # handles
    s.rect(X(XD_L1 - 4.3), 115 - 22.4, 1.2, 44.8, "handle")
    s.rect(X(XD_R11 - 4.3), H_FIX2 + 4, 1.2, 16, "handle")
    s.rect(X(XD_R20 + 3.1), H_FIX2 + 4, 1.2, 16, "handle")
    # hinge dots
    for hh in HINGE_L:
        s.add(f'<circle cx="{X(XD_L0 + 2.2):.2f}" cy="{s.Y(DOOR_BOT_L + hh):.2f}" r="1.1" class="hinge"/>')
    for hh in HINGE_R:
        s.add(f'<circle cx="{X(XD_R10 + 2.2):.2f}" cy="{s.Y(H_FIX2 + hh):.2f}" r="1.1" class="hinge"/>')
        s.add(f'<circle cx="{X(XD_R21 - 2.2):.2f}" cy="{s.Y(H_FIX2 + hh):.2f}" r="1.1" class="hinge"/>')
    # labels on doors
    s.text(X((XD_L0 + XD_L1) / 2), 150, f"باب طويل واحد", "doortxt")
    s.text(X((XD_L0 + XD_L1) / 2), 144, f"عرض {f1(DOOR_L_W)}", "doortxt num")
    s.text(X((XD_L0 + XD_L1) / 2), 138, f"ارتفاع {f1(DOOR_L_H)}", "doortxt num")
    s.text(X((XD_R10 + XD_R21) / 2), 225, "بابان", "doortxt")
    s.text(X((XD_R10 + XD_R21) / 2), 219, f"كل باب عرض {f1(DOOR_R_W)} وارتفاع {f1(DOOR_R_H)}", "doortxt num")
    # dimensions
    s.hdim(X(0), X(CAB_W), -9, f"عرض الخزانة {f1(CAB_W)}", ext_from=0)
    s.hdim(0, RECESS_W, -17, f"الحيط {f1(RECESS_W)}", ext_from=-1)
    s.vdim(-15, 0, DOOR_BOT_L, f"{f1(DOOR_BOT_L)}", ext_from=-8.5)
    s.vdim(-15, DOOR_BOT_L, DOOR_TOP, f"الباب الطويل {f1(DOOR_L_H)}", ext_from=-8.5)
    s.vdim(-25, 0, CAB_H, f"ارتفاع الخزانة {f1(CAB_H)}", ext_from=-8.5)
    s.vdim(-35, 0, RECESS_H, f"الحيط {f1(RECESS_H)}", ext_from=-8.5)
    xr = RECESS_W + 11
    s.vdim(xr, 0, NICHE_H, f"فتحة الغسالة والنشافة {f1(NICHE_H)}", side=1, ext_from=RECESS_W + 8.5)
    s.vdim(xr, NICHE_H, DOOR_TOP, f"الباب العلوي {f1(DOOR_R_H)}", side=1, ext_from=RECESS_W + 8.5)
    s.text(xr + 2, RECESS_H + 0.6, f"{f1(RECESS_H - CAB_H)} سم للسقف", "dt", anchor="left", size=2.6)
    s.hdim(X(X_N0), X(X_N1), 176.5, f"{f1(NICHE_IN)} صافي")
    return s.svg("الواجهة والأبواب مغلقة", 540)

# ---------------------------------------------------------------- sheet 2
def sheet_front_open():
    s = S(-40, -6, 200, 306, 272)
    s.line(-12, 0, CAB_W + 12, 0, "floor")
    s.rect(0, 0, CAB_W, CAB_H, "inside")
    s.rect(X_N0, 0, NICHE_IN, NICHE_H, "niche")
    machines(s, MX)
    carcass(s)
    s.rect(X_LC0, 0, LEFT_IN, PLINTH, "plinth")
    # spacer & drawers
    s.rect(X_LC0, H_BOTTOM + T, SPACER, H_FIX1 - H_BOTTOM - T, "spacer")
    for (a, b), n in ((F1, "درج عميق ١"), (F2, "درج عميق ٢")):
        s.rect(X_LC0 + SPACER + 0.2, a, FRONT_W, b - a, "front")
        s.rect(X_LC0 + SPACER + 0.2 + FRONT_W / 2 - 6, b - 5, 12, 1.2, "handle")
        s.text(X_LC0 + SPACER + 0.2 + FRONT_W / 2, (a + b) / 2 + 1.5, n, "lbl onwood")
        s.text(X_LC0 + SPACER + 0.2 + FRONT_W / 2, (a + b) / 2 - 4.5, f"عرض {f1(FRONT_W)}  ارتفاع {f1(FRONT_H)}", "lbl onwood num", size=2.6)
    # labels of compartments
    for a, b in ((zoneB0, ADJ_B[0]), (ADJ_B[0] + T, ADJ_B[1]), (ADJ_B[1] + T, zoneB1), (zoneC0, ADJ_C), (ADJ_C + T, zoneC1)):
        s.text((X_LC0 + X_LC1) / 2, (a + b) / 2 - 1, "رف", "lbl")
    s.text((X_N0 + X_N1) / 2, (zoneC0 + ADJ_C) / 2 - 1, "رف", "lbl")
    s.text((X_N0 + X_N1) / 2, (ADJ_C + T + zoneC1) / 2 - 1, "رف", "lbl")
    s.text((X_LC0 + X_LC1) / 2, PLINTH / 2 - 1.2, "قاعدة", "lbl small")
    # left chain (clear openings)
    xL = -8
    chain = [(0, PLINTH), (H_BOTTOM, H_BOTTOM + T), (H_BOTTOM + T, H_FIX1), (H_FIX1, H_FIX1 + T),
             (zoneB0, ADJ_B[0]), (ADJ_B[0], ADJ_B[0] + T), (ADJ_B[0] + T, ADJ_B[1]), (ADJ_B[1], ADJ_B[1] + T),
             (ADJ_B[1] + T, zoneB1), (H_FIX2, H_FIX2 + T), (zoneC0, ADJ_C), (ADJ_C, ADJ_C + T), (ADJ_C + T, zoneC1),
             (H_TOP, CAB_H)]
    for a, b in chain:
        big = (b - a) > 3
        s.line(xL, a, xL, b, "dim")
        s.add(f'<line x1="{xL - 0.9:.2f}" y1="{s.Y(a) + 0.9:.2f}" x2="{xL + 0.9:.2f}" y2="{s.Y(a) - 0.9:.2f}" class="dim tick"/>')
        if big:
            s.text(xL - 1.0, (a + b) / 2, f1(b - a), "dt", rot=-90)
    s.add(f'<line x1="{xL - 0.9:.2f}" y1="{s.Y(CAB_H) + 0.9:.2f}" x2="{xL + 0.9:.2f}" y2="{s.Y(CAB_H) - 0.9:.2f}" class="dim tick"/>')
    for a, b in chain:
        s.line(0, a, xL - 1.2, a, "ext")
    s.line(0, CAB_H, xL - 1.2, CAB_H, "ext")
    # level marks (height of the underside of each board) on far left
    xl2 = -22
    for v, nm in ((H_BOTTOM, "أرضية العمود"), (H_FIX1, "رف ثابت"), (ADJ_B[0], "رف متحرك"), (ADJ_B[1], "رف متحرك"),
                  (H_FIX2, "رف ثابت"), (ADJ_C, "رف متحرك"), (H_TOP, "السقف العلوي")):
        s.add(f'<polygon points="{xl2 - 1.2:.2f},{s.Y(v) - 1.8:.2f} {xl2 + 1.2:.2f},{s.Y(v) - 1.8:.2f} {xl2:.2f},{s.Y(v):.2f}" class="lvl"/>')
        s.line(xl2 - 3, v, xl2 + 3, v, "lvlline")
        s.text(xl2 - 3.5, v + 0.6, f"{f1(v)}", "lv", anchor="right")
    s.text(xl2 + 3, CAB_H + 6, "ارتفاع أسفل اللوح عن الأرض", "lv", anchor="right", size=2.6)
    # right chain
    xR = CAB_W + 8
    for a, b, lab in ((0, NICHE_H, f"{f1(NICHE_H)} صافي"), (H_FIX2, H_FIX2 + T, ""), (zoneC0, ADJ_C, None), (ADJ_C, ADJ_C + T, ""),
                      (ADJ_C + T, zoneC1, None), (H_TOP, CAB_H, "")):
        s.vdim(xR, a, b, lab, side=1)
    for v in (0, NICHE_H, H_FIX2 + T, ADJ_C, ADJ_C + T, H_TOP, CAB_H):
        s.line(CAB_W, v, xR + 1.2, v, "ext")
    s.vdim(xR, CAB_H, RECESS_H, "", side=1)
    s.line(CAB_W, RECESS_H, xR + 1.2, RECESS_H, "ext")
    s.vdim(xR + 10, 0, CAB_H, f"جسم الخزانة {f1(CAB_H)}", side=1)
    s.text(xR + 13, CAB_H - 0.6, f"{f1(RECESS_H - CAB_H)} سم للسقف", "dt", anchor="left", size=2.4)
    s.rect(-2, RECESS_H, CAB_W + 4, 3, "wall")
    s.text(CAB_W / 2, RECESS_H + 0.7, "السقف", "lbl small")
    # stacked machine heights inside niche
    # bottom chain
    yb = -8
    xs = [0, X_LC0, X_LC1, X_DIV1, X_N1, CAB_W]
    for a, b in zip(xs, xs[1:]):
        s.hdim(a, b, yb, "" if (b - a) < 3 else None, ext_from=0)
    s.text((X_LS + X_LC0) / 2 - 1.5, yb - 4.2, "1.8", "dt", size=2.6)
    s.text((X_DIV0 + X_DIV1) / 2, yb - 4.2, "1.8", "dt", size=2.6)
    s.text((X_RS0 + X_RS1) / 2 + 1.5, yb - 4.2, "1.8", "dt", size=2.6)
    s.hdim(0, CAB_W, -20, f"العرض الكلي {f1(CAB_W)}", ext_from=yb - 1.3)
    return s.svg("الخزانة من الداخل بدون أبواب", 560)

# ---------------------------------------------------------------- sheet 3
def sheet_section():
    """side section through the left column: wall on the left, room on the right"""
    s = S(-26, -6, 128, 300, 272)
    s.rect(-8, 0, 8, RECESS_H + 6, "wall")
    s.rect(-8, RECESS_H, 90, 6, "wall")
    s.line(-12, 0, 90, 0, "floor")
    s.line(RECESS_D, RECESS_H, RECESS_D, RECESS_H + 6, "ext")
    B = HDF  # back panel thickness at x 0..0.8
    s.rect(0, PLINTH, B, CAB_H - PLINTH, "back")
    # boards (horizontal)
    for h in (H_BOTTOM, H_FIX1, H_FIX2):
        s.rect(B, h, PANEL_D, T, "board")
    s.rect(B, H_TOP, PANEL_D, T, "board")
    for h in ADJ_B + [ADJ_C]:
        s.rect(B + 0.2, h, 57.0, T, "adj")
    # side panel outline (seen)
    s.rect(B, 0, PANEL_D, CAB_H, "seen")
    # plinth
    px = CAB_D - PLINTH_SETBACK - T
    s.rect(px, 0, T, PLINTH, "board")
    # drawers
    fx = CAB_D - FRONT_SETBACK - T
    for (a, b), (ba, bb) in ((F1, BOX1), (F2, BOX2)):
        s.rect(fx, a, T, b - a, "front")
        s.rect(fx - BOX_D, ba, BOX_D, bb - ba, "box")
        s.rect(fx - BOX_D, (ba + bb) / 2 - 2.2, BOX_D, 4.4, "slide")
    # door
    s.wood(CAB_D, DOOR_BOT_L, T, DOOR_L_H)
    s.rect(CAB_D, DOOR_BOT_L, T, DOOR_L_H, "door")
    # dimensions (depth)
    s.hdim(0, B, -7, "", ext_from=0)
    s.hdim(B, CAB_D, -7, f"{f1(PANEL_D)} عمق الجوانب", ext_from=0)
    s.hdim(CAB_D, DOOR_PROUD, -7, "", ext_from=0)
    s.text(DOOR_PROUD + 3.5, -8.2, "1.8", "dt", size=2.6)
    s.text(-2.5, -8.2, "0.8", "dt", size=2.6)
    s.hdim(0, RECESS_D, -16, f"عمق الحائط {f1(RECESS_D)}", ext_from=-8)
    s.hdim(fx - BOX_D, fx, 44.6 + 3.5, f"{f1(BOX_D)} الدرج")
    s.hdim(fx, CAB_D, 88 + 0.5, "", ext_from=F2[1])
    s.text(CAB_D - 1.2, 93.5, f"{f1(FRONT_SETBACK)}", "dt", size=2.6)
    s.hdim(B + 0.2, B + 57.2, ADJ_C + 5, "57 عمق الرف المتحرك")
    s.hdim(px + T, CAB_D, 13.5, "", ext_from=PLINTH)
    s.text(px + T + 2.5, 15.4, "5", "dt", size=2.6)
    s.vdim(DOOR_PROUD + 6, 0, PLINTH, f"{f1(PLINTH)}", side=1)
    s.vdim(DOOR_PROUD + 6, PLINTH, DOOR_TOP, f"الباب {f1(DOOR_L_H)}", side=1)
    s.text(8, RECESS_H + 2, "الحائط الخلفي والسقف", "lbl small", anchor="left")
    s.text(-4, 130, "الحائط", "lbl small", rot=-90)
    return s.svg("مقطع جانبي في العمود الأيسر", 360)

# ---------------------------------------------------------------- sheet 4 plan
def sheet_plan():
    """plan (top view): wall at top, room at bottom. y axis = depth from the back wall"""
    s = S(-22, -16, 158, 152, 0)
    # here we use Y(v) = -v, i.e. depth grows downward from the wall
    s.g = 0
    def R(x, d, w, h, cls):  # d = depth from wall (downwards)
        s.add(f'<rect x="{x:.2f}" y="{d:.2f}" width="{w:.2f}" height="{h:.2f}" class="{cls}"/>')
    # walls
    wl, wr = -(RECESS_W - CAB_W) / 2, CAB_W + (RECESS_W - CAB_W) / 2   # wall faces, 0.5 cm away
    s.add(f'<rect x="{wl - 8:.2f}" y="-8" width="{RECESS_W + 16}" height="8" class="wall"/>')
    s.add(f'<rect x="{wl - 8:.2f}" y="0" width="8" height="{RECESS_D}" class="wall"/>')
    s.add(f'<rect x="{wr:.2f}" y="0" width="8" height="{RECESS_D}" class="wall"/>')
    s.add(f'<line x1="-18" y1="{RECESS_D}" x2="{wl:.2f}" y2="{RECESS_D}" class="wallface"/>')
    s.add(f'<line x1="{wr:.2f}" y1="{RECESS_D}" x2="{RECESS_W + 18}" y2="{RECESS_D}" class="wallface"/>')
    # carcass
    R(0, 0, CAB_W, HDF, "back")
    R(X_LS, 0, T, CAB_D, "board")
    R(X_DIV0, 0, T, CAB_D, "board")
    R(X_RS0, 0, T, CAB_D, "board")
    R(X_LC0, HDF, LEFT_IN, PANEL_D, "insideplan")
    # machine footprint
    R(MX, 6, M_W, M_D, "machplan")
    s.add(f'<text x="{MX + M_W / 2:.2f}" y="{6 + M_D / 2 + 1:.2f}" class="lbl" text-anchor="middle">غسالة / نشافة</text>')
    s.add(f'<text x="{MX + M_W / 2:.2f}" y="{6 + M_D / 2 + 6:.2f}" class="lbl small" text-anchor="middle">60 × 60 تقريباً</text>')
    s.add(f'<text x="{MX + M_W / 2:.2f}" y="4.4" class="lbl small" text-anchor="middle">مسافة الخراطيم</text>')
    # doors (closed) + swing arcs
    def door(x0, x1, hinge_left, dashed=False):
        R(x0, CAB_D, x1 - x0, T, "doorplan")
        w = x1 - x0
        hx = (x0 if hinge_left else x1)
        ex = hx + (w if hinge_left else -w)
        sweep = 1 if hinge_left else 0
        cls = "arc dash" if dashed else "arc"
        s.add(f'<path d="M {ex:.2f} {DOOR_PROUD:.2f} A {w:.2f} {w:.2f} 0 0 {sweep} {hx:.2f} {DOOR_PROUD + w:.2f} L {hx:.2f} {DOOR_PROUD:.2f}" class="{cls}"/>')
    door(XD_L0, XD_L1, True)
    door(XD_R10, XD_R11, True, True)
    door(XD_R20, XD_R21, False, True)
    # dims
    s.add(f'<line x1="-14" y1="0" x2="-14" y2="{DOOR_PROUD}" class="dim"/>')
    for d in (0, CAB_D, DOOR_PROUD):
        s.add(f'<line x1="-15" y1="{d + 0.9:.2f}" x2="-13" y2="{d - 0.9:.2f}" class="dim tick"/>')
    s.add(f'<text x="-15.2" y="{CAB_D / 2:.2f}" class="dt" text-anchor="middle" transform="rotate(-90 -15.2 {CAB_D / 2:.2f})">60</text>')
    s.add(f'<text x="-17" y="{DOOR_PROUD + 1.2:.2f}" class="dt" text-anchor="start" style="font-size:2.6px">1.8</text>')
    xs = [0, X_LC0, X_LC1, X_DIV1, X_N1, CAB_W]
    yb = DOOR_PROUD + 50
    for a, b in zip(xs, xs[1:]):
        s.add(f'<line x1="{a:.2f}" y1="{yb}" x2="{b:.2f}" y2="{yb}" class="dim"/>')
        if b - a > 3:
            s.add(f'<text x="{(a + b) / 2:.2f}" y="{yb - 1:.2f}" class="dt" text-anchor="middle">{f1(b - a)}</text>')
    for a in xs:
        s.add(f'<line x1="{a - 0.9:.2f}" y1="{yb + 0.9:.2f}" x2="{a + 0.9:.2f}" y2="{yb - 0.9:.2f}" class="dim tick"/>')
    yb2 = yb + 8
    s.add(f'<line x1="0" y1="{yb2}" x2="{CAB_W}" y2="{yb2}" class="dim"/>')
    for a in (0, CAB_W):
        s.add(f'<line x1="{a - 0.9:.2f}" y1="{yb2 + 0.9:.2f}" x2="{a + 0.9:.2f}" y2="{yb2 - 0.9:.2f}" class="dim tick"/>')
        s.add(f'<line x1="{a:.2f}" y1="{RECESS_D:.2f}" x2="{a:.2f}" y2="{yb2 + 1.2:.2f}" class="ext"/>')
    s.add(f'<text x="{CAB_W / 2:.2f}" y="{yb2 - 1:.2f}" class="dt" text-anchor="middle">عرض الخزانة {f1(CAB_W)}، والحيط {f1(RECESS_W)}</text>')
    s.add(f'<text x="{CAB_W / 2:.2f}" y="-10.5" class="lbl small" text-anchor="middle">الحائط الخلفي</text>')
    s.add(f'<text x="{CAB_W / 2:.2f}" y="{yb2 + 8:.2f}" class="lbl small" text-anchor="middle">جهة الغرفة</text>')
    s.add(f'<text x="{XD_L0 + 22.5:.2f}" y="{DOOR_PROUD + 30:.2f}" class="lbl small" text-anchor="middle">فتح الباب الطويل</text>')
    return s.svg("المسقط من فوق", 520)

# ---------------------------------------------------------------- sheet 5 drawer
def sheet_drawer():
    """front section of the lower drawer, enlarged"""
    s = S(-12, -2, 70, 57, 44)
    s.k = 0.62
    s.rect(-T, 0, T, 44, "board")                 # left side panel
    s.rect(LEFT_IN, 0, T, 44, "board")            # divider
    s.rect(0, 0, SPACER, 44, "spacer")            # spacer
    bx = SPACER + SLIDE
    s.rect(bx, 5, BOX_W, BOX_H, "box")
    s.rect(bx, 5, T, BOX_H, "board")
    s.rect(bx + BOX_W - T, 5, T, BOX_H, "board")
    s.rect(bx, 5 - HDF, BOX_W, HDF, "back")
    s.rect(SPACER, 5 + BOX_H / 2 - 2.2, SLIDE, 4.4, "slide")
    s.rect(bx + BOX_W, 5 + BOX_H / 2 - 2.2, SLIDE, 4.4, "slide")
    s.hdim(0, SPACER, 40.5, "", ext_from=35)
    s.text(SPACER / 2 - 1.2, 42.2, "2.6", "dt", size=2.4)
    s.hdim(SPACER, SPACER + DR_CLEAR, 40.5, f"{f1(DR_CLEAR)} الفتحة", ext_from=35)
    s.hdim(bx, bx + BOX_W, 0.6, f"{f1(BOX_W)} عرض الصندوق الخارجي")
    s.hdim(0, LEFT_IN, -7, f"{f1(LEFT_IN)} صافي العمود", ext_from=0)
    s.vdim(LEFT_IN + T + 3.5, 5, 5 + BOX_H, f"{f1(BOX_H)}", side=1)
    s.text(bx + BOX_W / 2, 22, "صندوق الدرج", "lbl")
    s.text(bx + BOX_W / 2, 17.5, "سكة 1.3 من كل جهة", "lbl small")
    s.text(SPACER / 2, 25, "حشوة", "lbl small", rot=-90)
    s.text(-T / 2 - 3, 22, "جنب الخزانة", "lbl small", rot=-90)
    return s.svg("تفصيل الدرج", 420)

# ------------------------------------------------------------- cut list
PARTS = [
    # name, L (grain), W, qty, edge note
    ("جنب يسار", CAB_H, PANEL_D, 1, "كنار 2 مم على الحرف الأمامي"),
    ("جنب يمين", CAB_H, PANEL_D, 1, "كنار 2 مم على الحرف الأمامي"),
    ("قاطع وسط", H_TOP, PANEL_D, 1, "كنار 2 مم على الحرف الأمامي"),
    ("سقف علوي كامل", CAB_W - 2 * T, PANEL_D, 1, "كنار أمامي"),
    ("أرضية العمود الأيسر", LEFT_IN, PANEL_D, 1, "كنار أمامي"),
    ("رف ثابت (العمود الأيسر)", LEFT_IN, PANEL_D, 2, "كنار أمامي"),
    ("أرضية الخزانة فوق النشافة", NICHE_IN, PANEL_D, 1, "كنار أمامي + كنار سفلي ظاهر"),
    ("رف متحرك (العمود الأيسر)", LEFT_IN - 0.2, 57.0, 3, "كنار أمامي"),
    ("رف متحرك (فوق النشافة)", NICHE_IN - 0.2, 57.0, 1, "كنار أمامي"),
    ("وزرة القاعدة", LEFT_IN, PLINTH, 1, "كنار على الحرف الظاهر"),
    ("حشوة المفصلات (خشب 18)", H_FIX1 - H_BOTTOM - T, PANEL_D, 1, "+ طبقة HDF 8 مم بنفس المقاس"),
    ("الباب الطويل", DOOR_L_H, DOOR_L_W, 1, "كنار 2 مم من الأربع جهات"),
    ("باب علوي", DOOR_R_H, DOOR_R_W, 2, "كنار 2 مم من الأربع جهات"),
    ("واجهة درج داخلية", FRONT_H, FRONT_W, 2, "كنار من الأربع جهات"),
    ("جانب صندوق الدرج", BOX_D, BOX_H, 4, "كنار علوي"),
    ("أمام وخلف صندوق الدرج", BOX_W - 2 * T, BOX_H, 4, "كنار علوي"),
]
HDF_PARTS = [
    ("ظهر العمود الأيسر (سفلي)", H_FIX1 + T / 2 - PLINTH, X_DIV1, 1),
    ("ظهر العمود الأيسر (وسط)", H_FIX2 + T / 2 - (H_FIX1 + T / 2), X_DIV1, 1),
    ("ظهر العمود الأيسر (علوي)", CAB_H - (H_FIX2 + T / 2), X_DIV1, 1),
    ("ظهر الخزانة فوق النشافة", CAB_H - H_FIX2, CAB_W - X_DIV1, 1),
    ("قاع درج", BOX_D, BOX_W, 2),
    ("طبقة الحشوة", H_FIX1 - H_BOTTOM - T, PANEL_D, 1),
]
eq(sum(p[1] for p in HDF_PARTS[:3]) + PLINTH, CAB_H, "left back pieces cover full height")

area18 = sum(p[1] * p[2] * p[3] for p in PARTS) / 1e4
SHEETS = 3

def cut_rows():
    out = []
    for i, (n, L, W, q, e) in enumerate(PARTS, 1):
        out.append(f"<tr><td class='c'>{i}</td><td>{n}</td><td class='n'>{f1(L)}</td><td class='n'>{f1(W)}</td><td class='n'>{q}</td><td class='note'>{e}</td></tr>")
    return "".join(out)

def hdf_rows():
    out = []
    for i, (n, L, W, q) in enumerate(HDF_PARTS, len(PARTS) + 1):
        out.append(f"<tr><td class='c'>{i}</td><td>{n}</td><td class='n'>{f1(L)}</td><td class='n'>{f1(W)}</td><td class='n'>{q}</td></tr>")
    return "".join(out)

hinge_l_abs = "، ".join(f1(h) for h in HINGE_L)

# ---------------------------------------------------------------- page
CSS = open(os.path.join(HERE, "style.css"), encoding="utf-8").read()

def page():
    return f"""<title>خزانة الغسيل</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500;600;700&family=Reem+Kufi:wght@600;700&family=IBM+Plex+Mono:wght@500&display=swap">
<style>{CSS}</style>
<main dir="rtl" lang="ar">

<header class="titleblock">
  <div class="tb-name">
    <p class="eyebrow">مخطط تنفيذ للنجار</p>
    <h1>خزانة الغسيل</h1>
    <p class="lede">عمود طويل بباب واحد فيه درجين عميقين ورفوف، وبجانبه فتحة للغسالة والنشافة فوق بعض، وفوقهما خزانة ببابين ورف. الخزانة عرضها {f1(CAB_W)} وارتفاعها {f1(CAB_H)} بفتحة حيط {f1(RECESS_W)} × {f1(RECESS_H)}.</p>
  </div>
  <dl class="tb-cells">
    <div><dt>فتحة الحائط</dt><dd class="num">عرض {f1(RECESS_W)}، ارتفاع {f1(RECESS_H)}، عمق {f1(RECESS_D)}</dd></div>
    <div><dt>مقاس الخزانة</dt><dd class="num">عرض {f1(CAB_W)}، ارتفاع {f1(CAB_H)}، عمق {f1(CAB_D)}<br><span class="sub">نص سانتي لكل حيط، وسانتي للسقف</span></dd></div>
    <div><dt>الخشب</dt><dd><bdi dir="ltr">Egger H309 ST12</bdi><br><span class="sub"><bdi dir="ltr">Brown Tonsberg Oak</bdi>، سماكة 18 مم</span></dd></div>
    <div><dt>الوحدة</dt><dd>كل المقاسات بالسنتيمتر</dd></div>
  </dl>
</header>

<section class="keynums" aria-label="أهم المقاسات">
  <div><span class="k">فتحة الغسالة والنشافة</span><span class="v num">{f1(NICHE_H)}</span><span class="s">ارتفاع صافي، والعرض الصافي {f1(NICHE_IN)}، بدون باب وبدون ظهر</span></div>
  <div><span class="k">العمود الأيسر من الداخل</span><span class="v num">{f1(LEFT_IN)}</span><span class="s">عرض صافي، باب واحد من القاعدة للسقف</span></div>
  <div><span class="k">الدرجين العميقين</span><span class="v num">{f1(H_FIX1 - H_BOTTOM - T)}</span><span class="s">ارتفاع منطقة الدرجين معاً، كل درج {f1(FRONT_H)}</span></div>
  <div><span class="k">الغسالة فوقها النشافة</span><span class="v num">172</span><span class="s">ارتفاعهم مع قطعة التركيب تقريباً، كل جهاز عرض 60 وارتفاع 85</span></div>
</section>

<section class="sheet check">
  <div class="sheet-head"><span class="sheet-no">قبل التنفيذ</span><h2>أشياء لازم تتأكد منها</h2></div>
  <ul>
    <li><b>قيس الفتحة بثلاث أماكن</b> للعرض (تحت، نص، فوق) وللارتفاع (يمين، نص، يسار)، واعتمد أصغر رقم. المخطط مبني على حيط عرضه {f1(RECESS_W)} وارتفاعه {f1(RECESS_H)} وعمقه {f1(RECESS_D)}، وخزانة {f1(CAB_W)} × {f1(CAB_H)}. إذا طلع الحيط أضيق بأي نقطة، الفرق بيتعدّل على عرض العمود اليسار بس، وفتحة الغسالة بتضل {f1(NICHE_IN)}.</li>
    <li><b>مقاس الغسالة والنشافة الحقيقي.</b> المخطط مبني على المقاس القياسي عرض 60 وارتفاع 85. إذا واحد منهم أعرض من 60 أو أطول من 87، لازم نعدّل الفتحة. وشوف كتالوج تركيب الغسالة: إذا طالب مسافة من الجوانب أكتر من {f1(SIDE_CLR)} سم، لازم نلتزم فيها.</li>
    <li><b>النشافة</b> الأفضل تكون نوع مكثف أو مضخة حرارية لأنها ما بتحتاج فتحة تهوية للخارج. إذا كانت نوع تهوية، لازم فتحة بالحائط قطر 10 سم.</li>
    <li><b>الكهربا والمي.</b> خلي الفيش وحنفية المي والصرف على الحائط الخلفي بمكان ما يكون ورا جسم الغسالة مباشرة، وتأكد مع الكهربجي والسمكري قبل ما يبدأ النجار.</li>
  </ul>
</section>

<section class="sheet brk">
  <div class="sheet-head"><span class="sheet-no">لوحة 1</span><h2>الواجهة والأبواب مسكّرة</h2></div>
  <div class="figwrap">{sheet_front_closed()}</div>
  <p class="cap">الخزانة عرضها {f1(CAB_W)} وارتفاعها {f1(CAB_H)}، ومنها للحيط نص سانتي من كل جهة وسانتي للسقف. المثلث المنقّط على كل باب رأسه عند جهة المفصلات. النقاط الصغيرة أماكن المفصلات. الباب الطويل يفتح لجهة الحائط اليسار، والبابان العلويان يفتحان من النص للطرفين.</p>
</section>

<section class="sheet">
  <div class="sheet-head"><span class="sheet-no">لوحة 2</span><h2>من الداخل بدون أبواب</h2></div>
  <div class="figwrap">{sheet_front_open()}</div>
  <p class="cap">الأرقام على الخط اليسار هي الفتحات الصافية بين الألواح، وكل لوح سماكته 1.8. الأرقام بجانب المثلثات هي ارتفاع أسفل كل لوح عن الأرض. الرفوف الرمادية الفاتحة متحركة على ثقوب تعليق، والمقاس المرسوم هو توزيع متساوٍ مقترح.</p>
</section>

<div class="pair">
<section class="sheet">
  <div class="sheet-head"><span class="sheet-no">لوحة 3</span><h2>مقطع جانبي في العمود الأيسر</h2></div>
  <div class="figwrap">{sheet_section()}</div>
  <p class="cap">الخزانة تملأ عمق الحائط 60 سم ولازقة بالحيط الخلفي. الأبواب تطلع 1.8 سم لقدّام عن وجه الحائط حتى تنفتح بدون ما تحتك بالحيطان الجانبية.</p>
</section>
<section class="sheet">
  <div class="sheet-head"><span class="sheet-no">لوحة 4</span><h2>المسقط من فوق</h2></div>
  <div class="figwrap">{sheet_plan()}</div>
  <p class="cap">فتحة الغسالة بدون ظهر حتى تمر الخراطيم والفيش. الغسالة العادية بعمق 55 إلى 65 سم مع الخراطيم، فطبيعي تطلع من 3 إلى 8 سم عن وجه الخزانة.</p>
</section>
</div>

<section class="sheet">
  <div class="sheet-head"><span class="sheet-no">لوحة 5</span><h2>تفصيل الدرج العميق</h2></div>
  <div class="drawer-grid">
    <div class="figwrap">{sheet_drawer()}</div>
    <dl class="spec">
      <div><dt>عدد الأدراج</dt><dd>2 داخل الباب الطويل</dd></div>
      <div><dt>الصندوق الخارجي</dt><dd class="num">عرض {f1(BOX_W)}، ارتفاع {f1(BOX_H)}، عمق {f1(BOX_D)}</dd></div>
      <div><dt>الواجهة الداخلية</dt><dd class="num">عرض {f1(FRONT_W)}، ارتفاع {f1(FRONT_H)}</dd></div>
      <div><dt>ترجع الواجهة عن حرف الخزانة</dt><dd class="num">{f1(FRONT_SETBACK)}</dd></div>
      <div><dt>الدرج السفلي</dt><dd>واجهته من {f1(F1[0])} إلى {f1(F1[1])} عن الأرض، ومنتصف السكة على {f1(SLIDE_C[0])}</dd></div>
      <div><dt>الدرج العلوي</dt><dd>واجهته من {f1(F2[0])} إلى {f1(F2[1])} عن الأرض، ومنتصف السكة على {f1(SLIDE_C[1])}</dd></div>
      <div><dt>السكك</dt><dd>بلي 3 طيات فتح كامل، طول 50 سم، حمولة 45 كغ، يفضّل مع إغلاق هادئ</dd></div>
      <div><dt>الحشوة</dt><dd>لوح 18 مم مع HDF 8 مم ملصوقين (2.6 سم) على جنب المفصلات، ومفرّغة مكان قاعدة كل مفصلة، حتى ما يضرب الدرج بالمفصلات لما ينفتح.</dd></div>
    </dl>
  </div>
</section>

<section class="sheet">
  <div class="sheet-head"><span class="sheet-no">جدول 1</span><h2>جدول التقطيع</h2></div>
  <p class="cap">خشب Egger H309 ST12 سماكة 18 مم. الطول دائماً باتجاه عروق الخشب، والعروق عمودية على الأبواب والجوانب مثل العينة. المساحة تقريباً {area18:.1f} م² يعني {SHEETS} ألواح 280 × 207 مع الهدر.</p>
  <div class="tablewrap">
  <table>
    <thead><tr><th>#</th><th>القطعة</th><th>الطول (مع العرق)</th><th>العرض</th><th>العدد</th><th>الكنار</th></tr></thead>
    <tbody>{cut_rows()}</tbody>
  </table>
  </div>
  <h3>ألواح HDF سماكة 8 مم (أبيض)</h3>
  <p class="cap">الظهر يُركّب بالبراغي على الحرف الخلفي للجوانب، وكل قطعة تنتهي على نص رف ثابت. الكل يطلع من لوحين HDF مقاس 122 × 244.</p>
  <div class="tablewrap">
  <table>
    <thead><tr><th>#</th><th>القطعة</th><th>الطول</th><th>العرض</th><th>العدد</th></tr></thead>
    <tbody>{hdf_rows()}</tbody>
  </table>
  </div>
</section>

<section class="sheet">
  <div class="sheet-head"><span class="sheet-no">جدول 2</span><h2>الإكسسوارات</h2></div>
  <div class="tablewrap">
  <table>
    <thead><tr><th>الصنف</th><th>العدد</th><th>التفاصيل</th></tr></thead>
    <tbody>
      <tr><td>مفصلة 110° إغلاق هادئ، كاملة التغطية</td><td class="n">8</td><td>6 للباب الطويل على الجنب اليسار، و2 للباب العلوي اليمين</td></tr>
      <tr><td>مفصلة 110° إغلاق هادئ، نصف تغطية</td><td class="n">2</td><td>للباب العلوي اليسار لأنه يركب على القاطع الوسط</td></tr>
      <tr><td>سكة بلي فتح كامل 50 سم</td><td class="n">2 زوج</td><td>حمولة 45 كغ للأدراج العميقة</td></tr>
      <tr><td>مسامير رفوف (تعليق)</td><td class="n">16</td><td>4 لكل رف متحرك، وثقوب على مسافات 3.2 سم</td></tr>
      <tr><td>مسكة الباب الطويل</td><td class="n">1</td><td>طول تقريباً 45 سم عمودية، منتصفها على ارتفاع 115 سم</td></tr>
      <tr><td>مسكة الأبواب العلوية</td><td class="n">2</td><td>طول 16 سم عمودية، أسفل الباب من جهة النص</td></tr>
      <tr><td>مسكة الأدراج الداخلية</td><td class="n">2</td><td>صغيرة أو فتحة يد، لأنها داخل الباب</td></tr>
      <tr><td>زاوية تثبيت بالحائط</td><td class="n">6</td><td>3 للعمود من فوق، و3 للجنب اليمين على الحائط لأنه واقف لحاله جنب الغسالة</td></tr>
      <tr><td>قطعة تركيب النشافة فوق الغسالة</td><td class="n">1</td><td>من نفس ماركة الأجهزة، ما بتنعمل من الخشب</td></tr>
      <tr><td>مقوّم باب (اختياري)</td><td class="n">1</td><td>ينصح فيه للباب الطويل حتى ما يتقوّس مع الوقت</td></tr>
    </tbody>
  </table>
  </div>
  <h3>أماكن المفصلات</h3>
  <p class="cap">المسافة من أسفل الباب لمنتصف كأس المفصلة.</p>
  <ul class="hinges">
    <li><b>الباب الطويل:</b> <span class="num">{hinge_l_abs}</span>. هذه الأماكن مختارة حتى لا تطلع مفصلة على أي رف ولا على سكك الأدراج.</li>
    <li><b>البابان العلويان:</b> <span class="num">{f1(HINGE_R[0])} و {f1(HINGE_R[1])}</span>.</li>
  </ul>
</section>

<section class="sheet notes">
  <div class="sheet-head"><span class="sheet-no">ملاحظات</span><h2>ملاحظات للنجار</h2></div>
  <ul>
    <li><b>التجميع بالمكان قطعة قطعة.</b> صندوق كامل ارتفاعه {f1(CAB_H)} وعمقه 60 ما بيوقف تحت سقف {f1(RECESS_H)}. الجنبين بيوقفوا لحالهم، وبعدين بيتركب القاطع والألواح الأفقية بينهم.</li>
    <li><b>الفراغ مع الحيطان.</b> نص سانتي من كل جهة وسانتي من فوق. بيتسكّر بسيليكون بلون الخشب أو بشريط رفيع من نفس الخشب.</li>
    <li><b>الأبواب لقدّام عن الحائط.</b> وجه الجسم على نفس خط وجه الحيط، والأبواب بتطلع 1.8 سم لقدّام. هيك الباب بينفتح بدون ما يحتك بالحيط اللي جنبه. إذا دخلت الأبواب جوّا الفتحة، بتحتك بالحيط وما بتنفتح.</li>
    <li><b>فتحة الأجهزة بدون أرضية وبدون ظهر.</b> الغسالة توقف على البلاط مباشرة، والجنب اليمين والقاطع يتثبتوا منيح لأنه ما في شي يربطهم من تحت.</li>
    <li><b>مسافة {f1(SIDE_CLR)} سم من كل جهة للغسالة والنشافة.</b> هاي أقل مسافة آمنة، فلازم تكون الفتحة {f1(NICHE_IN)} بالضبط من تحت ومن النص ومن فوق، والقاطع موازي للجنب اليمين. والغسالة لازم تنزبط بالميزان منيح حتى ما تدق بالخشب وقت العصر.</li>
    <li><b>الرطوبة.</b> يفضّل طلب اللوح بنسخة مقاومة للرطوبة (MR) إذا متوفرة بنفس اللون، وكنار ABS 2 مم على كل الحروف الظاهرة، وسيليكون شفاف تحت الجوانب عند البلاط.</li>
    <li><b>عروق الخشب</b> عمودية على كل الأبواب والجوانب والواجهات حتى يطلع الشكل متناسق مثل العينة.</li>
  </ul>
</section>



</main>"""

if __name__ == "__main__":
    body = page()
    open(os.path.join(HERE, "design.html"), "w", encoding="utf-8").write(body)
    pbody = body
    font_css = os.environ.get("FONT_CSS")  # offline copy of the Google Fonts faces, used only for the PDF
    if font_css and os.path.exists(font_css):
        pbody = re.sub(r'<link rel="stylesheet" href="https://fonts.googleapis.com[^>]*>', "<style>" + open(font_css).read() + "</style>", pbody)
    full = "<!doctype html><html lang='ar' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'></head><body>" + pbody + "</body></html>"
    open(os.path.join(HERE, "print.html"), "w", encoding="utf-8").write(full)
    print("ok; area18 m2 =", round(area18, 2))
    print("ADJ_B", [round(x, 2) for x in ADJ_B], "ADJ_C", round(ADJ_C, 2), "spB", round(spB, 2), "spC", round(spC, 2))
