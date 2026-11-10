"""
Простой Logisim на pygame с КОНЕЧНОЙ скоростью сигнала.

Как работает задержка:
  * У каждого выхода (компонента) хранится история переключений [(время, значение)].
  * Провод имеет длину L (в пикселях). Сигнал бежит по нему со скоростью SPEED (px/с).
  * Значение в точке провода на расстоянии d от источника = значение источника
    в момент (now - d / SPEED). Поэтому «волна» 0/1 реально едет по проводу.
  * Вход гейта видит значение источника с задержкой L / SPEED.
  * Сам гейт тоже имеет задержку переключения GATE_DELAY.

Управление:
  Палитра слева: клик по элементу -> клик на поле ставит его.
  ЛКМ по IN (без перетаскивания)  - переключить 0/1
  ЛКМ-перетаскивание компонента   - двигать
  ЛКМ от правого пина (выхода) к левому пину (входу) - провести провод
  ПКМ по компоненту / проводу     - удалить; ПКМ по пустому месту - отменить выбор
  Колесо над CLK                  - изменить период тактов
  SPACE - пауза   +/-  - скорость сигнала   [ ]  - задержка гейта
  S / L - сохранить / загрузить circuit.json      C - очистить
"""
import json
import math
import os
import sys
from bisect import bisect_right

import pygame

W, H = 1280, 760
PAL_W = 130
GRID = 10
SIM_STEP = 0.005  # шаг симуляции, сек
HISTORY_KEEP = 60.0  # сколько секунд истории хранить
SAVE_FILE = "circuit.json"

BG = (24, 26, 31)
PANEL = (34, 37, 44)
GRID_COL = (32, 35, 41)
BODY = (58, 64, 78)
BODY_BORDER = (150, 160, 180)
TEXT = (230, 233, 240)
WIRE_OFF = (70, 78, 92)
WIRE_ON = (70, 230, 110)
SELECT = (255, 200, 60)

PALETTE = ["IN", "OUT", "CLK", "NOT", "AND", "OR", "XOR", "NAND", "NOR"]

LOGIC = {
    "AND": lambda a, b: a & b,
    "OR": lambda a, b: a | b,
    "XOR": lambda a, b: a ^ b,
    "NAND": lambda a, b: 1 - (a & b),
    "NOR": lambda a, b: 1 - (a | b),
    "NOT": lambda a, b: 1 - a,
}


class Comp:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.x, self.y = x, y
        self.n_in = {"IN": 0, "CLK": 0, "OUT": 1, "NOT": 1}.get(kind, 2)
        self.has_out = kind != "OUT"
        self.w = 50 if kind in ("IN", "OUT", "CLK") else 70
        self.h = 40 if self.n_in <= 1 else 50
        self.state = 0            # для IN
        self.period = 2.0         # для CLK
        self.inputs = [None] * self.n_in  # провода, входящие в пины
        self.ts = [0.0]           # история выхода: времена...
        self.vs = [0]             # ...и значения

    # --- геометрия ---
    @property
    def rect(self):
        return pygame.Rect(self.x, self.y, self.w, self.h)

    def in_pos(self, i):
        return (self.x, self.y + self.h * (i + 1) / (self.n_in + 1))

    def out_pos(self):
        return (self.x + self.w, self.y + self.h / 2)

    # --- значение выхода в момент t (с учётом истории) ---
    def out_at(self, t):
        i = bisect_right(self.ts, t) - 1
        return self.vs[max(i, 0)]


class Wire:
    def __init__(self, src, dst, pin):
        self.src, self.dst, self.pin = src, dst, pin

    def points(self):
        a = self.src.out_pos()
        b = self.dst.in_pos(self.pin)
        if b[0] - a[0] >= 20:
            mx = (a[0] + b[0]) / 2
            return [a, (mx, a[1]), (mx, b[1]), b]
        ax, bx = a[0] + 15, b[0] - 15
        my = (a[1] + b[1]) / 2
        if abs(a[1] - b[1]) < 30:
            my += 45
        return [a, (ax, a[1]), (ax, my), (bx, my), (bx, b[1]), b]

    def length(self):
        p = self.points()
        return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


def dist_to_segment(p, a, b):
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.dist(p, a)
    t = max(0, min(1, ((p[0] - ax) * dx + (p[1] - ay) * dy) / (dx * dx + dy * dy)))
    return math.dist(p, (ax + t * dx, ay + t * dy))


class Sim:
    def __init__(self):
        self.comps = []
        self.wires = []
        self.t = 0.0
        self.speed = 200.0       # px/с — скорость сигнала по проводу
        self.gate_delay = 0.20   # с — задержка гейта
        self.paused = False

    # значение, которое реально ДОШЛО до входа pin компонента c
    def in_val(self, c, pin):
        w = c.inputs[pin]
        if w is None:
            return 0
        return w.src.out_at(self.t - w.length() / self.speed)

    def step(self):
        for c in self.comps:
            if c.kind == "OUT":
                continue
            if c.kind == "IN":
                tgt, delay = c.state, 0.0
            elif c.kind == "CLK":
                tgt, delay = int((self.t / (c.period / 2)) % 2), 0.0
            else:
                a = self.in_val(c, 0)
                b = self.in_val(c, 1) if c.n_in > 1 else 0
                tgt, delay = LOGIC[c.kind](a, b), self.gate_delay
            if tgt != c.vs[-1]:
                c.ts.append(max(self.t + delay, c.ts[-1]))
                c.vs.append(tgt)
            while len(c.ts) > 2 and c.ts[1] < self.t - HISTORY_KEEP:
                c.ts.pop(0)
                c.vs.pop(0)

    def advance(self, dt):
        if self.paused:
            return
        n = max(1, int(dt / SIM_STEP))
        h = dt / n
        for _ in range(n):
            self.t += h
            self.step()

    # --- редактирование ---
    def add(self, kind, x, y):
        c = Comp(kind, x, y)
        self.comps.append(c)
        return c

    def connect(self, src, dst, pin):
        self.remove_wire(dst.inputs[pin])
        w = Wire(src, dst, pin)
        dst.inputs[pin] = w
        self.wires.append(w)

    def remove_wire(self, w):
        if w is None or w not in self.wires:
            return
        self.wires.remove(w)
        w.dst.inputs[w.pin] = None

    def remove_comp(self, c):
        for w in list(self.wires):
            if w.src is c or w.dst is c:
                self.remove_wire(w)
        self.comps.remove(c)

    def clear(self):
        self.comps.clear()
        self.wires.clear()
        self.t = 0.0

    def save(self, path):
        idx = {id(c): i for i, c in enumerate(self.comps)}
        data = {
            "speed": self.speed,
            "gate_delay": self.gate_delay,
            "comps": [
                {"kind": c.kind, "x": c.x, "y": c.y, "state": c.state, "period": c.period}
                for c in self.comps
            ],
            "wires": [{"src": idx[id(w.src)], "dst": idx[id(w.dst)], "pin": w.pin} for w in self.wires],
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=1)

    def load(self, path):
        with open(path) as f:
            data = json.load(f)
        self.clear()
        self.speed = data.get("speed", self.speed)
        self.gate_delay = data.get("gate_delay", self.gate_delay)
        for d in data["comps"]:
            c = self.add(d["kind"], d["x"], d["y"])
            c.state, c.period = d.get("state", 0), d.get("period", 2.0)
            c.vs[0] = c.state if c.kind == "IN" else 0
        for w in data["wires"]:
            self.connect(self.comps[w["src"]], self.comps[w["dst"]], w["pin"])


# ---------------------------------------------------------------- рисование
def draw_wire(screen, sim, w):
    pts = w.points()
    d = 0.0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        seg = math.dist(a, b)
        if seg == 0:
            continue
        n = max(1, int(seg // 4))
        prev = a
        for k in range(1, n + 1):
            f = k / n
            cur = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            dd = d + seg * (k - 0.5) / n
            v = w.src.out_at(sim.t - dd / sim.speed)  # значение, которое «доехало» до этой точки
            pygame.draw.line(screen, WIRE_ON if v else WIRE_OFF, prev, cur, 4)
            prev = cur
        d += seg


def draw_comp(screen, sim, font, c, selected=False):
    r = c.rect
    col = BODY
    if c.kind == "IN":
        col = (40, 120, 60) if c.state else (70, 50, 50)
    elif c.kind == "CLK":
        col = (40, 120, 60) if c.out_at(sim.t) else (70, 50, 50)
    pygame.draw.rect(screen, col, r, border_radius=6)
    pygame.draw.rect(screen, SELECT if selected else BODY_BORDER, r, 2, border_radius=6)

    if c.kind == "OUT":
        v = sim.in_val(c, 0)
        pygame.draw.circle(screen, (255, 70, 70) if v else (60, 40, 40), r.center, 14)
        pygame.draw.circle(screen, BODY_BORDER, r.center, 14, 2)
    else:
        label = {"IN": str(c.state), "CLK": "CLK"}.get(c.kind, c.kind)
        img = font.render(label, True, TEXT)
        screen.blit(img, img.get_rect(center=r.center))

    for i in range(c.n_in):
        v = sim.in_val(c, i)
        pygame.draw.circle(screen, WIRE_ON if v else WIRE_OFF, c.in_pos(i), 5)
        pygame.draw.circle(screen, BODY_BORDER, c.in_pos(i), 5, 1)
    if c.has_out:
        v = c.out_at(sim.t)
        pygame.draw.circle(screen, WIRE_ON if v else WIRE_OFF, c.out_pos(), 5)
        pygame.draw.circle(screen, BODY_BORDER, c.out_pos(), 5, 1)


def palette_rect(i):
    return pygame.Rect(10, 10 + i * 44, PAL_W - 20, 36)


def snap(v):
    return int(round(v / GRID) * GRID)


# ---------------------------------------------------------------------- main
def main():
    pygame.init()
    screen = pygame.display.set_mode((W, H))
    pygame.display.set_caption("Mini Logisim (pygame)")
    font = pygame.font.SysFont("consolas,dejavusansmono,arial", 16)
    small = pygame.font.SysFont("consolas,dejavusansmono,arial", 14)
    clock = pygame.time.Clock()
    sim = Sim()

    tool = None
    drag = None         # (comp, dx, dy, moved)
    wiring = None       # источник нового провода
    selected = None

    def comp_at(p):
        for c in reversed(sim.comps):
            if c.rect.collidepoint(p):
                return c

    def out_pin_at(p):
        for c in reversed(sim.comps):
            if c.has_out and math.dist(p, c.out_pos()) <= 9:
                return c

    def in_pin_at(p):
        for c in reversed(sim.comps):
            for i in range(c.n_in):
                if math.dist(p, c.in_pos(i)) <= 9:
                    return c, i
        return None

    def wire_at(p):
        for w in sim.wires:
            pts = w.points()
            if any(dist_to_segment(p, pts[i], pts[i + 1]) < 6 for i in range(len(pts) - 1)):
                return w

    running = True
    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)
        mouse = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    tool = None
                elif e.key == pygame.K_SPACE:
                    sim.paused = not sim.paused
                elif e.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    sim.speed = min(3000, sim.speed * 1.25)
                elif e.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    sim.speed = max(20, sim.speed / 1.25)
                elif e.key == pygame.K_LEFTBRACKET:
                    sim.gate_delay = max(0.0, round(sim.gate_delay - 0.05, 2))
                elif e.key == pygame.K_RIGHTBRACKET:
                    sim.gate_delay = min(3.0, round(sim.gate_delay + 0.05, 2))
                elif e.key == pygame.K_s:
                    sim.save(SAVE_FILE)
                elif e.key == pygame.K_l and os.path.exists(SAVE_FILE):
                    sim.load(SAVE_FILE)
                elif e.key == pygame.K_c:
                    sim.clear()

            elif e.type == pygame.MOUSEWHEEL:
                c = comp_at(mouse)
                if c and c.kind == "CLK":
                    c.period = max(0.25, c.period + 0.25 * e.y)

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                p = e.pos
                if p[0] < PAL_W:
                    for i, k in enumerate(PALETTE):
                        if palette_rect(i).collidepoint(p):
                            tool = k
                elif tool:
                    c = sim.add(tool, snap(p[0] - 25), snap(p[1] - 20))
                    selected = c
                    tool = None
                else:
                    oc = out_pin_at(p)
                    if oc:
                        wiring = oc
                    else:
                        c = comp_at(p)
                        selected = c
                        if c:
                            drag = [c, p[0] - c.x, p[1] - c.y, False]

            elif e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                if wiring:
                    hit = in_pin_at(e.pos)
                    if hit:
                        sim.connect(wiring, hit[0], hit[1])
                    wiring = None
                if drag:
                    c = drag[0]
                    if not drag[3] and c.kind == "IN":
                        c.state ^= 1
                    drag = None

            elif e.type == pygame.MOUSEMOTION and drag:
                c = drag[0]
                nx, ny = snap(e.pos[0] - drag[1]), snap(e.pos[1] - drag[2])
                if (nx, ny) != (c.x, c.y):
                    drag[3] = True
                c.x, c.y = max(PAL_W + 5, nx), max(5, ny)

            elif e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
                tool = None
                c = comp_at(e.pos)
                if c:
                    sim.remove_comp(c)
                    if selected is c:
                        selected = None
                else:
                    sim.remove_wire(wire_at(e.pos))

        sim.advance(dt)

        # --- рендер ---
        screen.fill(BG)
        for x in range(PAL_W, W, GRID * 4):
            pygame.draw.line(screen, GRID_COL, (x, 0), (x, H))
        for y in range(0, H, GRID * 4):
            pygame.draw.line(screen, GRID_COL, (PAL_W, y), (W, y))

        for w in sim.wires:
            draw_wire(screen, sim, w)
        for c in sim.comps:
            draw_comp(screen, sim, font, c, c is selected)

        if wiring:
            a = wiring.out_pos()
            pygame.draw.line(screen, SELECT, a, mouse, 2)

        if tool:  # «призрак» ставимого элемента
            ghost = Comp(tool, snap(mouse[0] - 25), snap(mouse[1] - 20))
            pygame.draw.rect(screen, SELECT, ghost.rect, 2, border_radius=6)

        # палитра
        pygame.draw.rect(screen, PANEL, (0, 0, PAL_W, H))
        for i, k in enumerate(PALETTE):
            r = palette_rect(i)
            pygame.draw.rect(screen, (80, 90, 110) if k == tool else BODY, r, border_radius=6)
            pygame.draw.rect(screen, SELECT if k == tool else BODY_BORDER, r, 2, border_radius=6)
            img = font.render(k, True, TEXT)
            screen.blit(img, img.get_rect(center=r.center))

        info = (
            f"signal speed: {sim.speed:.0f} px/s  (+/-)    gate delay: {sim.gate_delay:.2f} s  ([ ])    "
            f"t = {sim.t:6.2f} s    {'PAUSED' if sim.paused else ''}"
        )
        screen.blit(small.render(info, True, TEXT), (PAL_W + 10, H - 44))
        hint = "LMB: place/drag/toggle IN | drag from right pin to left pin = wire | RMB: delete | SPACE pause | S/L save/load | C clear"
        screen.blit(small.render(hint, True, (140, 148, 165)), (PAL_W + 10, H - 24))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()