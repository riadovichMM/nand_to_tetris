#!/usr/bin/env python3
"""
Наглядная виртуальная машина nand2tetris (стековая VM) на tkinter.

Идея, которую надо "проглотить мозгом":
  1. Вся память — один массив RAM[0..32767].
  2. RAM[0..4] — регистры-указатели: SP, LCL, ARG, THIS, THAT.
  3. Стек — это просто область RAM, начиная с адреса 256. Он растёт ВВЕРХ (адреса растут).
     SP указывает на первую СВОБОДНУЮ ячейку (не на вершину!). Вершина = RAM[SP-1].
  4. "Сегменты" (local, argument, this, that) — не отдельная память, а окна в RAM:
     адрес = RAM[указатель] + индекс.
     temp = RAM[5..12], pointer = RAM[3..4], static = RAM[16..255], constant — виртуальный.
  5. call/function/return — это просто аккуратная работа с тем же стеком (кадр вызова).

Запуск:  python3 vm_visual.py        (F10 = шаг)
"""
import tkinter as tk
from tkinter import ttk

RAM_SIZE = 32768
SP, LCL, ARG, THIS, THAT = 0, 1, 2, 3, 4
REGS = (("SP", SP), ("LCL", LCL), ("ARG", ARG), ("THIS", THIS), ("THAT", THAT))
SEG_PTR = {
    "local": (LCL, "LCL"),
    "argument": (ARG, "ARG"),
    "this": (THIS, "THIS"),
    "that": (THAT, "THAT"),
}
SEGMENTS = ["constant", "local", "argument", "this", "that", "temp", "pointer", "static"]
ARITH_BIN = {"add", "sub", "eq", "gt", "lt", "and", "or"}
ARITH_UN = {"neg", "not"}
ARITH = ARITH_BIN | ARITH_UN
SYM = {"add": "+", "sub": "-", "and": "&", "or": "|", "eq": "==", "gt": ">", "lt": "<"}

MONO = ("Consolas", 11)
MONO_S = ("Consolas", 10)
BOLD = ("Consolas", 11, "bold")


def w16(x):
    """Обёртка в 16-битное знаковое число (как в Hack)."""
    x &= 0xFFFF
    return x - 0x10000 if x & 0x8000 else x


def check_simple(t):
    """Проверка push/pop/арифметики. Возвращает текст ошибки или None."""
    op = t[0]
    if op in ("push", "pop"):
        if len(t) != 3 or t[1] not in SEGMENTS or not t[2].isdigit():
            return "ожидается: push/pop <сегмент> <число>"
        i = int(t[2])
        if op == "pop" and t[1] == "constant":
            return "в constant нельзя писать (pop constant не существует)"
        if t[1] == "constant" and i > 32767:
            return "constant: 0..32767"
        if t[1] == "temp" and i > 7:
            return "temp: индекс 0..7"
        if t[1] == "pointer" and i > 1:
            return "pointer: индекс 0 или 1"
    elif op in ARITH and len(t) != 1:
        return "эта команда без аргументов"
    return None


# =====================================================================
#                           САМА ВИРТУАЛЬНАЯ МАШИНА
# =====================================================================
class VM:
    def __init__(self):
        self.prog, self.labels, self.funcs = [], {}, {}
        self.reset()

    # ---------- загрузка программы ----------
    def load(self, text):
        prog, labels, funcs, cur = [], {}, {}, ""
        for no, raw in enumerate(text.split("\n")):
            s = raw.split("//")[0].strip()
            if not s:
                continue
            t = s.split()
            op = t[0]

            def bad(msg):
                raise ValueError(f"строка {no + 1}: {msg}")

            if op in ("push", "pop") or op in ARITH:
                e = check_simple(t)
                if e:
                    bad(e)
            elif op == "return":
                if len(t) != 1:
                    bad("return без аргументов")
            elif op in ("label", "goto", "if-goto"):
                if len(t) != 2:
                    bad(f"ожидается: {op} <имя>")
                if op == "label":
                    labels[(cur, t[1])] = len(prog)
            elif op in ("function", "call"):
                if len(t) != 3 or not t[2].isdigit():
                    bad(f"ожидается: {op} <имя> <число>")
                if op == "function":
                    cur = t[1]
                    funcs[cur] = len(prog)
            else:
                bad(f"неизвестная команда '{op}'")
            prog.append({"t": t, "line": no, "fn": cur})
        for ins in prog:
            t = ins["t"]
            if t[0] in ("goto", "if-goto") and (ins["fn"], t[1]) not in labels:
                raise ValueError(f"строка {ins['line'] + 1}: нет метки '{t[1]}' в этой функции")
            if t[0] == "call" and t[1] not in funcs:
                raise ValueError(f"строка {ins['line'] + 1}: нет функции '{t[1]}'")
        self.prog, self.labels, self.funcs = prog, labels, funcs

    # ---------- состояние ----------
    def reset(self):
        self.ram = [0] * RAM_SIZE
        self.ram[SP] = 256
        self.pc, self.steps = 0, 0
        self.callstack = []
        self.changed = set()
        self.halted = not self.prog
        if "Sys.init" in self.funcs:
            self.do_call("Sys.init", 0, len(self.prog))
            self.note = ("Bootstrap: SP=256, затем call Sys.init 0 — так делает настоящий "
                         "транслятор VM→asm. Смотри: на стеке уже лежит кадр.")
        else:
            self.ram[LCL], self.ram[ARG], self.ram[THIS], self.ram[THAT] = 300, 400, 3000, 3010
            self.note = ("Нет Sys.init, поэтому как в тестах курса: SP=256, LCL=300, "
                         "ARG=400, THIS=3000, THAT=3010.")
        self.changed = set()

    # ---------- доступ к RAM ----------
    def getram(self, a):
        if not 0 <= a < RAM_SIZE:
            raise RuntimeError(f"адрес {a} вне RAM")
        return self.ram[a]

    def setram(self, a, v):
        if not 0 <= a < RAM_SIZE:
            raise RuntimeError(f"адрес {a} вне RAM")
        self.ram[a] = w16(v)
        self.changed.add(a)

    def push(self, v):
        sp = self.ram[SP]
        self.setram(sp, v)         # RAM[SP] = v
        self.setram(SP, sp + 1)    # SP++

    def pop(self):
        sp = self.ram[SP] - 1
        if sp < 256:
            raise RuntimeError("стек пуст (SP упал бы ниже 256)")
        self.setram(SP, sp)        # SP--
        return self.ram[sp]

    def target(self, seg, i):
        """Куда на самом деле указывает сегмент: (адрес RAM, описание)."""
        if seg in SEG_PTR:
            p, nm = SEG_PTR[seg]
            b = self.ram[p]
            return b + i, f"RAM[{nm}+{i}] = RAM[{b}+{i}] = RAM[{b + i}]"
        if seg == "temp":
            return 5 + i, f"RAM[5+{i}] = RAM[{5 + i}]"
        if seg == "pointer":
            return 3 + i, f"RAM[{3 + i}] ({'THIS' if i == 0 else 'THAT'})"
        return 16 + i, f"RAM[16+{i}] = RAM[{16 + i}] (static)"

    def do_call(self, name, n, ret):
        self.push(ret)                       # адрес возврата
        for r in (LCL, ARG, THIS, THAT):     # сохраняем кадр вызывающего
            self.push(self.ram[r])
        self.setram(ARG, self.ram[SP] - n - 5)
        self.setram(LCL, self.ram[SP])
        self.pc = self.funcs[name]
        self.callstack.append(name)

    def skip_labels(self, i):
        while i < len(self.prog) and self.prog[i]["t"][0] == "label":
            i += 1
        return i

    # ---------- выполнение ----------
    def step(self):
        if self.halted:
            return None
        old = self.pc
        ins = self.prog[old]
        self.changed = set()
        self.pc = old + 1
        try:
            txt = self.execute(ins, old + 1)
        except RuntimeError as e:
            self.halted = True
            return f"ОШИБКА в строке {ins['line'] + 1}: {e}"
        self.steps += 1
        if ins["t"][0] == "goto" and self.skip_labels(self.pc) == old:
            self.halted = True
            txt += "\n  (прыжок на самого себя — конец программы)"
        elif self.pc >= len(self.prog):
            self.halted = True
            txt += "\n— программа завершена"
        return txt

    def manual(self, t):
        e = check_simple(t)
        if e:
            raise ValueError(e)
        self.changed = set()
        return self.execute({"t": t, "fn": ""}, None, True)

    def execute(self, ins, nxt, manual=False):
        t = ins["t"]
        op = t[0]
        if manual and op not in ("push", "pop") and op not in ARITH:
            raise RuntimeError("вручную доступны push, pop и арифметика")

        if op == "push":
            seg, i = t[1], int(t[2])
            if seg == "constant":
                v, src = i, f"константа {i}"
            else:
                a, d = self.target(seg, i)
                v = self.getram(a)
                src = f"{d} = {v}"
            sp = self.ram[SP]
            self.push(v)
            return (f"push {seg} {i}\n  значение: {src}\n"
                    f"  RAM[SP={sp}] = {v}\n  SP++ → SP={self.ram[SP]}")

        if op == "pop":
            seg, i = t[1], int(t[2])
            a, d = self.target(seg, i)
            sp0 = self.ram[SP]
            v = self.pop()
            self.setram(a, v)
            return (f"pop {seg} {i}\n  SP-- → SP={sp0 - 1}\n"
                    f"  вершина стека RAM[{sp0 - 1}] = {v}\n  записываем в {d}")

        if op in ARITH_BIN:
            y = self.pop()
            x = self.pop()
            r = {"add": x + y, "sub": x - y, "and": x & y, "or": x | y,
                 "eq": -1 if x == y else 0, "gt": -1 if x > y else 0,
                 "lt": -1 if x < y else 0}[op]
            self.push(r)
            extra = "  (-1 = true, 0 = false)" if op in ("eq", "gt", "lt") else ""
            return (f"{op}\n  y = pop() = {y}\n  x = pop() = {x}\n"
                    f"  push(x {SYM[op]} y) = {w16(r)}{extra}")

        if op in ARITH_UN:
            y = self.pop()
            r = -y if op == "neg" else ~y
            self.push(r)
            return f"{op}\n  y = pop() = {y}\n  push({'-y' if op == 'neg' else '~y'}) = {w16(r)}"

        if op == "label":
            return f"label {t[1]}\n  просто метка, ничего не делает"

        if op == "goto":
            self.pc = self.labels[(ins["fn"], t[1])]
            return f"goto {t[1]}\n  безусловный прыжок, pc → {self.pc}"

        if op == "if-goto":
            v = self.pop()
            tgt = self.labels[(ins["fn"], t[1])]
            if v != 0:
                self.pc = tgt
                return f"if-goto {t[1]}\n  pop() = {v} ≠ 0 → прыгаем, pc → {tgt}"
            return f"if-goto {t[1]}\n  pop() = 0 → НЕ прыгаем, идём дальше"

        if op == "function":
            n = int(t[2])
            for _ in range(n):
                self.push(0)
            return (f"function {t[1]} {n}\n  начало функции: создаём {n} локальных "
                    f"переменных (push constant 0 × {n})\n  LCL={self.ram[LCL]}, SP={self.ram[SP]}")

        if op == "call":
            name, n = t[1], int(t[2])
            self.do_call(name, n, nxt)
            return (f"call {name} {n}\n  1) push адрес возврата ({nxt})\n"
                    f"  2) push LCL, ARG, THIS, THAT вызывающего (сохраняем кадр)\n"
                    f"  3) ARG = SP-{n}-5 = {self.ram[ARG]}  (аргументы уже лежат на стеке)\n"
                    f"  4) LCL = SP = {self.ram[LCL]}\n  5) goto {name}")

        if op == "return":
            if not self.callstack:
                raise RuntimeError("return вне функции")
            frame = self.ram[LCL]
            ret = self.getram(frame - 5)
            that = self.getram(frame - 1)
            this = self.getram(frame - 2)
            arg = self.getram(frame - 3)
            lcl = self.getram(frame - 4)
            v = self.pop()
            old_arg = self.ram[ARG]
            self.setram(old_arg, v)          # результат — на место первого аргумента
            self.setram(SP, old_arg + 1)
            self.setram(THAT, that)
            self.setram(THIS, this)
            self.setram(ARG, arg)
            self.setram(LCL, lcl)
            self.pc = ret
            name = self.callstack.pop()
            return (f"return (из {name})\n  frame = LCL = {frame}, ret = RAM[frame-5] = {ret}\n"
                    f"  RAM[ARG={old_arg}] = результат {v}\n  SP = ARG+1 = {old_arg + 1}\n"
                    f"  восстановили THAT, THIS, ARG, LCL из кадра\n  goto {ret}")
        raise RuntimeError(f"неизвестная команда {op}")


# =====================================================================
#                                  GUI
# =====================================================================
EXAMPLES = {
    "1. Арифметика": """// (7 + 8) - 3, потом сравнение
push constant 7
push constant 8
add
push constant 3
sub
push constant 12
eq
""",
    "2. Сегменты": """// сегменты — окна в RAM
push constant 10
pop local 0        // RAM[LCL+0] = 10
push constant 21
pop local 1
push local 0
push local 1
add
pop temp 2         // RAM[5+2]
push constant 3000
pop pointer 0      // THIS = 3000
push constant 42
pop this 0         // RAM[THIS+0] = 42
""",
    "3. Цикл (сумма 1..5)": """// local 0 = сумма, local 1 = счётчик
push constant 0
pop local 0
push constant 5
pop local 1
label LOOP
push local 0
push local 1
add
pop local 0
push local 1
push constant 1
sub
pop local 1
push local 1
if-goto LOOP
push local 0       // на вершине 15
""",
    "4. Вызов функции": """function Sys.init 0
push constant 7
push constant 3
call Main.add3 2
pop temp 0
label HALT
goto HALT

function Main.add3 1
push argument 0
push argument 1
add
pop local 0
push local 0
push constant 3
add
return
""",
    "5. Рекурсия sumto(3)": """function Sys.init 0
push constant 3
call Main.sumto 1
pop temp 0
label HALT
goto HALT

function Main.sumto 0
push argument 0
push constant 1
lt
if-goto BASE
push argument 0
push argument 0
push constant 1
sub
call Main.sumto 1
add
return
label BASE
push constant 0
return
""",
}

INTRO = ("""Как читать картинку:
 • Жёлтое — что изменилось на последнем шаге.
 • Синее — живой стек (адреса 256..SP-1). Серое выше SP — мусор, он просто не считается.
 • Красные стрелки ◀ — куда сейчас указывают SP/LCL/ARG/THIS/THAT.
 • «Сегменты» справа — это не память, а окна в RAM: адрес = указатель + индекс.
Нажимай «Шаг» (F10) и читай объяснение ниже. Кнопки справа выполняют команды вручную.""")


class App(tk.Tk):
    ROWS = 24
    CH = 26

    def __init__(self):
        super().__init__()
        self.title("Nand2Tetris VM — наглядная модель")
        self.geometry("1320x790")
        self.vm = VM()
        self.running = False
        self.lo = 256
        self.follow = tk.BooleanVar(value=True)
        self.status = tk.StringVar()
        self.build()
        self.bind("<F10>", lambda e: self.do_step())
        self.load_example()

    # ---------- построение интерфейса ----------
    def build(self):
        bar = ttk.Frame(self, padding=6)
        bar.pack(fill="x")
        ttk.Button(bar, text="⏭ Шаг (F10)", command=self.do_step).pack(side="left", padx=2)
        ttk.Button(bar, text="▶ Запуск", command=self.run).pack(side="left", padx=2)
        ttk.Button(bar, text="⏸ Пауза", command=self.pause).pack(side="left", padx=2)
        ttk.Button(bar, text="↺ Сброс (из кода)", command=self.reset).pack(side="left", padx=2)
        ttk.Label(bar, text="  задержка, мс:").pack(side="left")
        self.speed = tk.Scale(bar, from_=50, to=1500, orient="horizontal", length=140)
        self.speed.set(500)
        self.speed.pack(side="left")
        ttk.Label(bar, text="   пример:").pack(side="left")
        self.ex = ttk.Combobox(bar, values=list(EXAMPLES), state="readonly", width=22)
        self.ex.current(0)
        self.ex.pack(side="left", padx=2)
        ttk.Button(bar, text="Загрузить", command=self.load_example).pack(side="left", padx=2)
        ttk.Label(bar, textvariable=self.status, font=BOLD).pack(side="right", padx=8)

        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=6, pady=4)

        # --- левая колонка: код ---
        left = ttk.Frame(main)
        left.pack(side="left", fill="y")
        ttk.Label(left, text="Программа (VM-код, можно править → Сброс)", font=BOLD).pack(anchor="w")
        self.code = tk.Text(left, width=34, height=38, font=MONO, wrap="none", undo=True)
        self.code.pack(fill="y", expand=True)
        self.code.tag_configure("cur", background="#ffd54f")

        # --- средняя колонка: RAM ---
        mid = ttk.Frame(main)
        mid.pack(side="left", fill="y", padx=10)
        ttk.Label(mid, text="RAM (верх = большие адреса, стек растёт вверх)", font=BOLD).pack(anchor="w")
        nav = ttk.Frame(mid)
        nav.pack(fill="x", pady=2)
        ttk.Checkbutton(nav, text="следить за стеком", variable=self.follow,
                        command=self.refresh).pack(side="left")
        ttk.Button(nav, text="▲", width=3, command=lambda: self.scroll(8)).pack(side="left", padx=2)
        ttk.Button(nav, text="▼", width=3, command=lambda: self.scroll(-8)).pack(side="left")
        ttk.Label(nav, text=" адрес:").pack(side="left")
        self.addr_e = ttk.Entry(nav, width=6)
        self.addr_e.pack(side="left")
        self.addr_e.bind("<Return>", lambda e: self.jump_entry())
        ttk.Button(nav, text="Показать", command=self.jump_entry).pack(side="left", padx=2)
        nav2 = ttk.Frame(mid)
        nav2.pack(fill="x", pady=2)
        ttk.Button(nav2, text="0–15", width=6, command=lambda: self.jump(0)).pack(side="left")
        ttk.Button(nav2, text="static", width=6, command=lambda: self.jump(16)).pack(side="left")
        for nm, idx in REGS:
            ttk.Button(nav2, text="→" + nm, width=6,
                       command=lambda i=idx: self.jump_reg(i)).pack(side="left")
        self.canvas = tk.Canvas(mid, width=390, height=self.ROWS * self.CH + 12, bg="white",
                                highlightthickness=1, highlightbackground="#999")
        self.canvas.pack()

        # --- правая колонка ---
        right = ttk.Frame(main)
        right.pack(side="left", fill="both", expand=True)

        rf = ttk.Frame(right)
        rf.pack(fill="x")
        self.reg_lbl = {}
        for k, (nm, idx) in enumerate(REGS):
            lb = tk.Label(rf, text=nm, font=("Consolas", 13, "bold"), width=8, relief="ridge",
                          bg="#eceff1", pady=4)
            lb.grid(row=0, column=k, padx=2, sticky="ew")
            rf.columnconfigure(k, weight=1)
            self.reg_lbl[nm] = (lb, idx)

        ttk.Label(right, text="Сегменты = окна в RAM (адрес = указатель + индекс)",
                  font=BOLD).pack(anchor="w", pady=(8, 0))
        self.seg_lbl = tk.Label(right, text="", font=MONO_S, justify="left", anchor="w",
                                bg="#fafafa", relief="sunken", padx=4, pady=4)
        self.seg_lbl.pack(fill="x")
        self.cs_lbl = tk.Label(right, text="", font=MONO_S, justify="left", anchor="w", fg="#4a148c")
        self.cs_lbl.pack(fill="x", pady=2)

        man = ttk.LabelFrame(right, text="Вручную (не двигает программу)", padding=4)
        man.pack(fill="x", pady=4)
        r1 = ttk.Frame(man)
        r1.pack(fill="x")
        self.m_op = ttk.Combobox(r1, values=["push", "pop"], state="readonly", width=5)
        self.m_op.current(0)
        self.m_op.pack(side="left")
        self.m_seg = ttk.Combobox(r1, values=SEGMENTS, state="readonly", width=10)
        self.m_seg.current(0)
        self.m_seg.pack(side="left", padx=3)
        self.m_idx = ttk.Entry(r1, width=6)
        self.m_idx.insert(0, "5")
        self.m_idx.pack(side="left")
        self.m_idx.bind("<Return>", lambda e: self.manual_pp())
        ttk.Button(r1, text="Выполнить", command=self.manual_pp).pack(side="left", padx=4)
        r2 = ttk.Frame(man)
        r2.pack(fill="x", pady=(4, 0))
        for op in ("add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"):
            ttk.Button(r2, text=op, width=5, command=lambda o=op: self.manual([o])).pack(side="left", padx=1)

        ttk.Label(right, text="Что произошло (объяснение шагов)", font=BOLD).pack(anchor="w")
        lf = ttk.Frame(right)
        lf.pack(fill="both", expand=True)
        self.log_t = tk.Text(lf, height=12, font=MONO_S, wrap="word", bg="#fffde7")
        sb = ttk.Scrollbar(lf, command=self.log_t.yview)
        self.log_t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.log_t.pack(side="left", fill="both", expand=True)

    # ---------- навигация по RAM ----------
    def cur_lo(self):
        if self.follow.get():
            return max(256, self.vm.ram[SP] + 3 - self.ROWS)
        return self.lo

    def jump(self, a):
        self.follow.set(False)
        self.lo = max(0, min(a, RAM_SIZE - self.ROWS))
        self.refresh()

    def jump_reg(self, idx):
        self.jump(self.vm.ram[idx] - 3)

    def jump_entry(self):
        try:
            self.jump(int(self.addr_e.get()) - 3)
        except ValueError:
            pass

    def scroll(self, d):
        self.lo = self.cur_lo()
        self.follow.set(False)
        self.jump(self.lo + d)

    # ---------- действия ----------
    def log(self, s):
        self.log_t.insert("end", s + "\n\n")
        self.log_t.see("end")

    def load_example(self):
        self.code.delete("1.0", "end")
        self.code.insert("1.0", EXAMPLES[self.ex.get()])
        self.reset()

    def reset(self):
        self.running = False
        try:
            self.vm.load(self.code.get("1.0", "end"))
        except ValueError as e:
            self.log("ОШИБКА В КОДЕ: " + str(e))
            return
        self.vm.reset()
        self.follow.set(True)
        self.log_t.delete("1.0", "end")
        self.log(INTRO)
        self.log("— сброс —\n" + self.vm.note)
        self.refresh()

    def do_step(self):
        txt = self.vm.step()
        if txt is None:
            self.log("Программа завершена. Нажми «Сброс».")
            self.running = False
            return
        self.log(f"#{self.vm.steps}  {txt}")
        self.refresh()

    def run(self):
        if self.running or self.vm.halted:
            return
        self.running = True
        self.tick()

    def pause(self):
        self.running = False

    def tick(self):
        if not self.running:
            return
        self.do_step()
        if self.vm.halted:
            self.running = False
            return
        self.after(int(self.speed.get()), self.tick)

    def manual_pp(self):
        self.manual([self.m_op.get(), self.m_seg.get(), self.m_idx.get().strip()])

    def manual(self, t):
        try:
            txt = self.vm.manual(t)
        except (RuntimeError, ValueError) as e:
            self.log("ОШИБКА: " + str(e))
            return
        self.log("[вручную] " + txt)
        self.refresh()

    # ---------- отрисовка ----------
    def refresh(self):
        vm = self.vm
        self.code.tag_remove("cur", "1.0", "end")
        if not vm.halted and vm.pc < len(vm.prog):
            ln = vm.prog[vm.pc]["line"] + 1
            self.code.tag_add("cur", f"{ln}.0", f"{ln}.end+1c")
            self.code.see(f"{ln}.0")
        for nm, (lb, idx) in self.reg_lbl.items():
            lb.config(text=f"{nm}\n{vm.ram[idx]}",
                      bg="#ffd54f" if idx in vm.changed else "#eceff1")
        self.seg_lbl.config(text=self.segs_text())
        self.cs_lbl.config(text="стек вызовов: " + (" → ".join(vm.callstack) if vm.callstack else "—"))
        state = "конец" if vm.halted else f"следующая команда: {' '.join(vm.prog[vm.pc]['t'])}"
        self.status.set(f"шагов: {vm.steps}   |   {state}")
        self.draw()

    def segs_text(self):
        vm = self.vm

        def cells(base, n):
            out = []
            for i in range(n):
                a = base + i
                out.append(f"{i}:{vm.ram[a]}" if 0 <= a < RAM_SIZE else f"{i}:?")
            return "  ".join(out)

        L = []
        for seg, (p, nm) in SEG_PTR.items():
            b = vm.ram[p]
            L.append(f"{seg:<9}{nm:<5}→ RAM[{b}+i]   {cells(b, 4)}")
        L.append(f"{'temp':<9}{'':<5}→ RAM[5+i]     {cells(5, 8)}")
        L.append(f"{'pointer':<9}{'':<5}→ RAM[3+i]     0(THIS):{vm.ram[3]}  1(THAT):{vm.ram[4]}")
        L.append(f"{'static':<9}{'':<5}→ RAM[16+i]    {cells(16, 4)}")
        L.append(f"{'constant':<9}{'':<5}→ не память: значение = i")
        return "\n".join(L)

    @staticmethod
    def name_of(a):
        if a < 5:
            return ("SP", "LCL", "ARG", "THIS", "THAT")[a]
        if a < 13:
            return f"temp {a - 5}"
        if a < 16:
            return f"R{a}"
        if a < 256:
            return f"static {a - 16}"
        if a < 2048:
            return "stack"
        return "heap"

    def draw(self):
        c, vm = self.canvas, self.vm
        c.delete("all")
        lo = self.cur_lo()
        sp = vm.ram[SP]
        marks = {}
        for nm, idx in REGS:
            marks.setdefault(vm.ram[idx], []).append(nm)
        for row in range(self.ROWS):
            a = lo + self.ROWS - 1 - row
            if a >= RAM_SIZE:
                continue
            y = 6 + row * self.CH
            live = 256 <= a < sp
            if a in vm.changed:
                fill = "#ffd54f"
            elif live:
                fill = "#bbdefb"
            elif a < 256 or a >= 2048:
                fill = "#c8e6c9" if vm.ram[a] else "#e0e0e0"
            else:
                fill = "#f5f5f5"
            c.create_text(8, y + 12, text=str(a), anchor="w", font=BOLD)
            c.create_text(62, y + 12, text=self.name_of(a), anchor="w", font=("Consolas", 9), fill="#777")
            c.create_rectangle(140, y, 270, y + self.CH - 2, fill=fill, outline="#555")
            dim = (256 <= a < 2048) and not live and a not in vm.changed
            c.create_text(205, y + 12, text=str(vm.ram[a]), font=BOLD,
                          fill="#aaa" if dim else "#111")
            if a in marks:
                c.create_text(276, y + 12, text="◀ " + ", ".join(marks[a]), anchor="w",
                              fill="#c62828", font=BOLD)


if __name__ == "__main__":
    App().mainloop()