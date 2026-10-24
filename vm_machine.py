#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Визуальная виртуальная машина NAND2Tetris (проекты 7-8).

Реализует полный набор команд VM-языка:
  Арифметико-логические:  add sub neg eq gt lt and or not
  Работа с памятью:       push/pop {constant,local,argument,this,that,temp,pointer,static} i
  Ветвление:              label L / goto L / if-goto L
  Функции:                function f k / call f n / return

Интерфейс на Tkinter показывает:
  - исходный код с подсветкой текущей команды
  - стек (адреса 256+) с указателем SP
  - регистры SP/LCL/ARG/THIS/THAT
  - сегменты temp / pointer / static
  - стек вызовов функций (call-frame'ы)
  - экран Hack-компьютера (512x256, память 16384-24575), обновляющийся
    в реальном времени по мере выполнения команд
  - память клавиатуры (24576) — можно "печатать" в окно экрана

Запуск:  python3 nand2tetris_vm.py
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from dataclasses import dataclass, field
from typing import Optional, List, Dict

# ----------------------------------------------------------------------
#  Константы адресного пространства Hack
# ----------------------------------------------------------------------
STACK_BASE   = 256
TEMP_BASE    = 5
POINTER_BASE = 3
STATIC_BASE  = 16
SCREEN_BASE  = 16384
KBD_ADDR     = 24576
RAM_SIZE     = 24577 + 1     # включая ячейку клавиатуры

SCREEN_W, SCREEN_H = 512, 256
SCREEN_WORDS = (SCREEN_W * SCREEN_H) // 16   # 8192 слова по 16 бит


def mask16(x: int) -> int:
    """Привести целое число к 16-битному представлению Hack (со знаком)."""
    x &= 0xFFFF
    if x >= 0x8000:
        x -= 0x10000
    return x


# ----------------------------------------------------------------------
#  Разбор VM-кода
# ----------------------------------------------------------------------
ARITH_CMDS = {"add", "sub", "neg", "eq", "gt", "lt", "and", "or", "not"}
SEGMENTS = {"constant", "local", "argument", "this", "that",
            "temp", "pointer", "static"}


@dataclass
class Instr:
    cmd: str                 # "push","pop","add",...,"label","goto","if-goto","function","call","return"
    a1: Optional[str] = None
    a2: Optional[int] = None
    raw: str = ""
    line_no: int = 0
    func: Optional[str] = None   # имя функции, в которой находится команда (для скоупа меток)


class ParseError(Exception):
    pass


def parse(text: str) -> List[Instr]:
    """Разобрать текст VM-программы в плоский список инструкций.

    Метки внутри функций получают внутреннее имя вида "Func$label",
    чтобы goto/if-goto из разных функций не путались друг с другом —
    именно так поступает настоящий транслятор VM.
    """
    instrs: List[Instr] = []
    current_func: Optional[str] = None

    for raw_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        cmd = parts[0]

        if cmd in ARITH_CMDS:
            if len(parts) != 1:
                raise ParseError(f"строка {raw_no}: у «{cmd}» не должно быть аргументов")
            instrs.append(Instr(cmd, raw=raw_line, line_no=raw_no, func=current_func))

        elif cmd in ("push", "pop"):
            if len(parts) != 3 or parts[1] not in SEGMENTS:
                raise ParseError(f"строка {raw_no}: неверный синтаксис «{line}»")
            seg, idx = parts[1], int(parts[2])
            if cmd == "pop" and seg == "constant":
                raise ParseError(f"строка {raw_no}: нельзя «pop constant»")
            instrs.append(Instr(cmd, seg, idx, raw_line, raw_no, current_func))

        elif cmd == "label":
            if len(parts) != 2:
                raise ParseError(f"строка {raw_no}: «label» требует один аргумент")
            name = f"{current_func}$" + parts[1] if current_func else parts[1]
            instrs.append(Instr("label", name, raw=raw_line, line_no=raw_no, func=current_func))

        elif cmd in ("goto", "if-goto"):
            if len(parts) != 2:
                raise ParseError(f"строка {raw_no}: «{cmd}» требует один аргумент")
            instrs.append(Instr(cmd, parts[1], raw=raw_line, line_no=raw_no, func=current_func))

        elif cmd == "function":
            if len(parts) != 3:
                raise ParseError(f"строка {raw_no}: «function» требует имя и число локальных")
            current_func = parts[1]
            instrs.append(Instr("function", parts[1], int(parts[2]), raw_line, raw_no, current_func))

        elif cmd == "call":
            if len(parts) != 3:
                raise ParseError(f"строка {raw_no}: «call» требует имя функции и число аргументов")
            instrs.append(Instr("call", parts[1], int(parts[2]), raw_line, raw_no, current_func))

        elif cmd == "return":
            instrs.append(Instr("return", raw=raw_line, line_no=raw_no, func=current_func))
            current_func = current_func  # return не завершает область видимости функции

        else:
            raise ParseError(f"строка {raw_no}: неизвестная команда «{cmd}»")

    return instrs


def resolve_labels(instrs: List[Instr]):
    """Построить таблицы: имя-функции -> индекс инструкции,
    и полное-имя-метки -> индекс инструкции."""
    func_map: Dict[str, int] = {}
    label_map: Dict[str, int] = {}
    for i, ins in enumerate(instrs):
        if ins.cmd == "function":
            func_map[ins.a1] = i
        elif ins.cmd == "label":
            label_map[ins.a1] = i
    return func_map, label_map


def maybe_bootstrap(instrs: List[Instr]) -> List[Instr]:
    """Если в программе есть функции, но нет ни одной команды верхнего
    уровня (вне function/label и т.п.), автоматически подставляем
    стартовый вызов Sys.init — как это делает настоящий загрузчик Hack."""
    has_top_level = any(ins.func is None and ins.cmd not in ("label",) for ins in instrs)
    func_map, _ = resolve_labels(instrs)
    if not has_top_level and "Sys.init" in func_map:
        boot = Instr("call", "Sys.init", 0, raw="call Sys.init 0   // (авто-бутстрап)", line_no=0, func=None)
        return [boot] + instrs
    return instrs


# ----------------------------------------------------------------------
#  Виртуальная машина
# ----------------------------------------------------------------------
@dataclass
class Frame:
    """Запись для наглядного отображения стека вызовов."""
    name: str
    ret_pc: int
    arg_addr: int
    lcl_addr: int


class VM:
    def __init__(self):
        self.mem = [0] * RAM_SIZE
        self.instrs: List[Instr] = []
        self.func_map: Dict[str, int] = {}
        self.label_map: Dict[str, int] = {}
        self.pc = 0
        self.frames: List[Frame] = []
        self.dirty_screen = set()   # адреса экрана, изменившиеся за последний step()
        self.halted = False
        self.error: Optional[str] = None
        self.steps_done = 0
        self.reset_regs()

    def reset_regs(self):
        self.mem = [0] * RAM_SIZE
        self.mem[0] = STACK_BASE   # SP
        self.pc = 0
        self.frames = []
        self.dirty_screen.clear()
        self.halted = False
        self.error = None
        self.steps_done = 0

    def load(self, instrs: List[Instr]):
        self.instrs = maybe_bootstrap(instrs)
        self.func_map, self.label_map = resolve_labels(self.instrs)
        self.reset_regs()

    # ---- регистры как свойства над memory[0..4] -----------------------
    @property
    def sp(self): return self.mem[0]
    @sp.setter
    def sp(self, v): self.mem[0] = v

    @property
    def lcl(self): return self.mem[1]
    @lcl.setter
    def lcl(self, v): self.mem[1] = v

    @property
    def arg(self): return self.mem[2]
    @arg.setter
    def arg(self, v): self.mem[2] = v

    @property
    def this(self): return self.mem[3]
    @this.setter
    def this(self, v): self.mem[3] = v

    @property
    def that(self): return self.mem[4]
    @that.setter
    def that(self, v): self.mem[4] = v

    # ---- доступ к памяти с отслеживанием "грязных" ячеек экрана -------
    def read_mem(self, addr: int) -> int:
        if addr < 0 or addr >= RAM_SIZE:
            raise IndexError(f"обращение вне памяти: {addr}")
        return self.mem[addr]

    def write_mem(self, addr: int, value: int):
        if addr < 0 or addr >= RAM_SIZE:
            raise IndexError(f"обращение вне памяти: {addr}")
        self.mem[addr] = mask16(value)
        if SCREEN_BASE <= addr < KBD_ADDR:
            self.dirty_screen.add(addr)

    def push(self, value: int):
        self.write_mem(self.sp, value)
        self.sp = self.sp + 1

    def pop(self) -> int:
        self.sp = self.sp - 1
        return self.read_mem(self.sp)

    def seg_base(self, seg: str) -> Optional[int]:
        return {"local": self.lcl, "argument": self.arg,
                "this": self.this, "that": self.that}.get(seg)

    # ---- выполнение одной инструкции -----------------------------------
    def step(self):
        if self.halted or self.error:
            return
        self.dirty_screen.clear()
        if self.pc >= len(self.instrs):
            self.halted = True
            return

        ins = self.instrs[self.pc]
        next_pc = self.pc + 1
        try:
            c = ins.cmd
            if c == "push":
                seg = ins.a1
                if seg == "constant":
                    self.push(ins.a2)
                elif seg == "temp":
                    self.push(self.read_mem(TEMP_BASE + ins.a2))
                elif seg == "pointer":
                    self.push(self.read_mem(POINTER_BASE + ins.a2))
                elif seg == "static":
                    self.push(self.read_mem(STATIC_BASE + ins.a2))
                else:
                    self.push(self.read_mem(self.seg_base(seg) + ins.a2))

            elif c == "pop":
                seg = ins.a1
                val = self.pop()
                if seg == "temp":
                    self.write_mem(TEMP_BASE + ins.a2, val)
                elif seg == "pointer":
                    self.write_mem(POINTER_BASE + ins.a2, val)
                elif seg == "static":
                    self.write_mem(STATIC_BASE + ins.a2, val)
                else:
                    self.write_mem(self.seg_base(seg) + ins.a2, val)

            elif c == "add":
                y, x = self.pop(), self.pop(); self.push(x + y)
            elif c == "sub":
                y, x = self.pop(), self.pop(); self.push(x - y)
            elif c == "neg":
                x = self.pop(); self.push(-x)
            elif c == "and":
                y, x = self.pop(), self.pop(); self.push(x & y & 0xFFFF)
            elif c == "or":
                y, x = self.pop(), self.pop(); self.push(x | y)
            elif c == "not":
                x = self.pop(); self.push(~x)
            elif c in ("eq", "gt", "lt"):
                y, x = self.pop(), self.pop()
                cond = {"eq": x == y, "gt": x > y, "lt": x < y}[c]
                self.push(-1 if cond else 0)

            elif c == "label":
                pass  # метка — просто точка в коде

            elif c == "goto":
                next_pc = self._resolve_label(ins)

            elif c == "if-goto":
                cond = self.pop()
                if cond != 0:
                    next_pc = self._resolve_label(ins)

            elif c == "function":
                k = ins.a2
                for _ in range(k):
                    self.push(0)

            elif c == "call":
                fname, n = ins.a1, ins.a2
                if fname not in self.func_map:
                    raise ParseError(f"вызов неизвестной функции «{fname}»")
                ret_addr = next_pc
                arg_new = self.sp - n
                self.push(ret_addr)
                self.push(self.lcl)
                self.push(self.arg)
                self.push(self.this)
                self.push(self.that)
                self.arg = arg_new
                self.lcl = self.sp
                self.frames.append(Frame(fname, ret_addr, self.arg, self.lcl))
                next_pc = self.func_map[fname]

            elif c == "return":
                frame_addr = self.lcl
                ret_pc = self.read_mem(frame_addr - 5)
                retval = self.pop()
                caller_arg = self.arg
                self.write_mem(caller_arg, retval)
                self.sp = caller_arg + 1
                self.that = self.read_mem(frame_addr - 1)
                self.this = self.read_mem(frame_addr - 2)
                self.arg = self.read_mem(frame_addr - 3)
                self.lcl = self.read_mem(frame_addr - 4)
                next_pc = ret_pc
                if self.frames:
                    self.frames.pop()
            else:
                raise ParseError(f"нереализованная команда «{c}»")

        except Exception as e:
            self.error = f"Ошибка на строке {ins.line_no} («{ins.raw.strip()}»): {e}"
            self.halted = True
            return

        self.pc = next_pc
        self.steps_done += 1
        if self.pc >= len(self.instrs):
            self.halted = True

    def _resolve_label(self, ins: Instr) -> int:
        scoped = f"{ins.func}${ins.a1}" if ins.func else ins.a1
        if scoped in self.label_map:
            return self.label_map[scoped]
        if ins.a1 in self.label_map:
            return self.label_map[ins.a1]
        raise ParseError(f"метка «{ins.a1}» не найдена")


# ----------------------------------------------------------------------
#  Пример программы, демонстрирующий сразу всё: функции, циклы, стек и экран
# ----------------------------------------------------------------------
EXAMPLE_VM = """\
// Демонстрация: функция Main.main закрашивает первые 128 слов экрана
// (это 4 верхние строки экрана из 32 слов по 16 пикселей каждая),
// используя цикл через label/goto/if-goto и сегмент pointer/that.
// Затем Sys.init вызывает Main.main и складывает два числа через стек.

function Main.main 2
    push constant 0
    pop local 0            // i = 0  (счётчик слов)
    push constant 16384
    pop local 1             // addr = SCREEN (16384)

label LOOP
    push local 0
    push constant 128
    lt
    if-goto BODY
    goto END

label BODY
    push local 1
    pop pointer 1           // THAT = addr  (наводим указатель that на экран)
    push constant -1
    pop that 0              // записываем в память по адресу addr: -1 = все 16 бит = чёрный

    push local 1
    push constant 1
    add
    pop local 1             // addr = addr + 1

    push local 0
    push constant 1
    add
    pop local 0             // i = i + 1
    goto LOOP

label END
    push constant 111
    push constant 222
    add                     // 111 + 222 = 333, кладём результат на стек как "возврат"
    return

function Sys.init 0
    call Main.main 0
    pop temp 0              // сохраняем результат (333) в temp[0], просто чтобы его увидеть
label HALT
    goto HALT                // бесконечный цикл — обычная концовка Hack-программы
"""


# ----------------------------------------------------------------------
#  Графический интерфейс
# ----------------------------------------------------------------------
class VMApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("NAND2Tetris — визуальная виртуальная машина (VM)")
        root.geometry("1400x820")

        self.vm = VM()
        self.running = False
        self.after_id = None

        self._build_toolbar()
        self._build_main_area()

        self.text.insert("1.0", EXAMPLE_VM)
        self._parse_and_load(quiet=True)

    # ---------------------------------------------------------------- UI
    def _build_toolbar(self):
        bar = ttk.Frame(self.root, padding=4)
        bar.pack(side="top", fill="x")

        ttk.Button(bar, text="Открыть .vm файл", command=self.load_file).pack(side="left", padx=2)
        ttk.Button(bar, text="Пример", command=self.load_example).pack(side="left", padx=2)
        ttk.Button(bar, text="Разобрать код ▶", command=lambda: self._parse_and_load(quiet=False)).pack(side="left", padx=8)
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(bar, text="⟳ Сброс", command=self.on_reset).pack(side="left", padx=2)
        ttk.Button(bar, text="Шаг →", command=self.on_step).pack(side="left", padx=2)
        self.run_btn = ttk.Button(bar, text="▶ Запуск", command=self.on_run_pause)
        self.run_btn.pack(side="left", padx=2)

        ttk.Label(bar, text="  Скорость:").pack(side="left")
        self.speed = tk.IntVar(value=40)
        ttk.Scale(bar, from_=1, to=300, orient="horizontal", variable=self.speed, length=140)\
            .pack(side="left", padx=4)
        ttk.Label(bar, text="(мс между шагами)").pack(side="left")

        self.status = tk.StringVar(value="Готово.")
        ttk.Label(bar, textvariable=self.status, foreground="#0a5").pack(side="right", padx=6)

    def _build_main_area(self):
        paned = ttk.PanedWindow(self.root, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=4, pady=4)

        # ---------- левая колонка: исходный код ----------
        left = ttk.Frame(paned)
        ttk.Label(left, text="Код VM (можно редактировать)", font=("Consolas", 10, "bold")).pack(anchor="w")
        text_frame = ttk.Frame(left)
        text_frame.pack(fill="both", expand=True)
        self.text = tk.Text(text_frame, font=("Consolas", 11), undo=True, wrap="none")
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=vsb.set)
        self.text.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.text.tag_configure("current", background="#ffe680")
        self.text.tag_configure("error_line", background="#ff9999")
        paned.add(left, weight=3)

        # ---------- средняя колонка: стек / регистры / call-стек ----------
        mid = ttk.Frame(paned)
        paned.add(mid, weight=2)

        regs_frame = ttk.LabelFrame(mid, text="Регистры")
        regs_frame.pack(fill="x", pady=(0, 4))
        self.reg_tree = ttk.Treeview(regs_frame, columns=("val",), show="tree headings", height=5)
        self.reg_tree.heading("#0", text="Регистр")
        self.reg_tree.heading("val", text="Значение")
        self.reg_tree.column("#0", width=90)
        self.reg_tree.column("val", width=90)
        for name in ("SP", "LCL", "ARG", "THIS", "THAT"):
            self.reg_tree.insert("", "end", iid=name, text=name, values=("0",))
        self.reg_tree.pack(fill="x")

        stack_frame = ttk.LabelFrame(mid, text="Стек (снизу вверх, верх = SP)")
        stack_frame.pack(fill="both", expand=True, pady=4)
        self.stack_list = tk.Listbox(stack_frame, font=("Consolas", 10))
        sb1 = ttk.Scrollbar(stack_frame, orient="vertical", command=self.stack_list.yview)
        self.stack_list.configure(yscrollcommand=sb1.set)
        self.stack_list.pack(side="left", fill="both", expand=True)
        sb1.pack(side="right", fill="y")

        segs_frame = ttk.Frame(mid)
        segs_frame.pack(fill="x", pady=4)

        temp_frame = ttk.LabelFrame(segs_frame, text="temp[0..7]")
        temp_frame.pack(side="left", fill="both", expand=True, padx=2)
        self.temp_list = tk.Listbox(temp_frame, font=("Consolas", 9), height=8)
        self.temp_list.pack(fill="both", expand=True)

        ptr_frame = ttk.LabelFrame(segs_frame, text="pointer[0..1]\n(this/that)")
        ptr_frame.pack(side="left", fill="both", expand=True, padx=2)
        self.ptr_list = tk.Listbox(ptr_frame, font=("Consolas", 9), height=8)
        self.ptr_list.pack(fill="both", expand=True)

        static_frame = ttk.LabelFrame(segs_frame, text="static[0..15]")
        static_frame.pack(side="left", fill="both", expand=True, padx=2)
        self.static_list = tk.Listbox(static_frame, font=("Consolas", 9), height=8)
        self.static_list.pack(fill="both", expand=True)

        call_frame = ttk.LabelFrame(mid, text="Стек вызовов функций (call frames)")
        call_frame.pack(fill="both", expand=True, pady=(4, 0))
        self.call_list = tk.Listbox(call_frame, font=("Consolas", 10))
        self.call_list.pack(fill="both", expand=True)

        # ---------- правая колонка: экран ----------
        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        ttk.Label(right, text="Экран Hack (16384-24575), 512×256",
                  font=("Consolas", 10, "bold")).pack(anchor="w")
        canvas_wrap = ttk.Frame(right, relief="sunken", borderwidth=2)
        canvas_wrap.pack()
        self.canvas = tk.Canvas(canvas_wrap, width=SCREEN_W, height=SCREEN_H,
                                 bg="white", highlightthickness=0)
        self.canvas.pack()
        self.screen_img = tk.PhotoImage(width=SCREEN_W, height=SCREEN_H)
        self.canvas.create_image(0, 0, image=self.screen_img, anchor="nw")
        self._clear_screen_image()

        kbd_frame = ttk.LabelFrame(right, text="Клавиатура (память 24576) — кликните на экран и печатайте")
        kbd_frame.pack(fill="x", pady=6)
        self.kbd_var = tk.StringVar(value="код клавиши: 0")
        ttk.Label(kbd_frame, textvariable=self.kbd_var).pack(anchor="w", padx=4)
        self.canvas.bind("<KeyPress>", self._on_key_press)
        self.canvas.bind("<KeyRelease>", self._on_key_release)
        self.canvas.bind("<Button-1>", lambda e: self.canvas.focus_set())

        info = ttk.LabelFrame(right, text="Как это читать")
        info.pack(fill="both", expand=True, pady=(6, 0))
        txt = (
            "• Жёлтым подсвечена команда, которая будет выполнена следующим «Шагом».\n"
            "• Стек показывает реальные адреса памяти начиная с 256 (STACK_BASE).\n"
            "  Верхняя строка списка — самый верх стека (последнее, что положили).\n"
            "• LCL/ARG/THIS/THAT — это указатели (адреса) на области памяти,\n"
            "  через которые push/pop local|argument|this|that обращаются к данным.\n"
            "• «Стек вызовов» показывает, в какой функции вы сейчас находитесь,\n"
            "  и какие ARG/LCL были у неё на момент вызова (call).\n"
            "• Запись в память 16384-24575 сразу отражается на экране\n"
            "  (каждое 16-битное слово — это 16 пикселей одной строки экрана)."
        )
        ttk.Label(info, text=txt, justify="left", wraplength=380).pack(anchor="w", padx=6, pady=6)

    # ------------------------------------------------------------ загрузка
    def load_file(self):
        path = filedialog.askopenfilename(filetypes=[("VM files", "*.vm"), ("Все файлы", "*.*")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self._parse_and_load(quiet=False)

    def load_example(self):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", EXAMPLE_VM)
        self._parse_and_load(quiet=False)

    def _parse_and_load(self, quiet=False):
        self._stop_running()
        src = self.text.get("1.0", "end")
        try:
            instrs = parse(src)
            if not instrs:
                raise ParseError("программа пуста")
            self.vm.load(instrs)
        except ParseError as e:
            messagebox.showerror("Ошибка разбора", str(e))
            self.status.set(f"Ошибка: {e}")
            return
        self.status.set(f"Загружено инструкций: {len(self.vm.instrs)}. Готово к выполнению.")
        self._clear_screen_image()
        self._refresh_all()

    # ------------------------------------------------------------ действия
    def on_reset(self):
        self._stop_running()
        self.vm.reset_regs()
        self._clear_screen_image()
        self.status.set("Сброшено.")
        self._refresh_all()

    def on_step(self):
        if not self.vm.instrs:
            return
        if self.vm.halted or self.vm.error:
            self._stop_running()
            return
        self.vm.step()
        self._apply_screen_updates()
        self._refresh_all()
        if self.vm.error:
            self.status.set(self.vm.error)
            self._stop_running()
        elif self.vm.halted:
            self.status.set(f"Программа завершена (выполнено шагов: {self.vm.steps_done}).")
            self._stop_running()

    def on_run_pause(self):
        if self.running:
            self._stop_running()
        else:
            if self.vm.halted or self.vm.error or not self.vm.instrs:
                return
            self.running = True
            self.run_btn.configure(text="⏸ Пауза")
            self._run_loop()

    def _run_loop(self):
        if not self.running:
            return
        self.on_step()
        if self.running and not self.vm.halted and not self.vm.error:
            self.after_id = self.root.after(max(1, self.speed.get()), self._run_loop)
        else:
            self._stop_running()

    def _stop_running(self):
        self.running = False
        self.run_btn.configure(text="▶ Запуск")
        if self.after_id is not None:
            try:
                self.root.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    # ------------------------------------------------------------ клавиатура
    def _on_key_press(self, event):
        code = event.keysym_num if event.keysym_num < 65536 else 0
        # упрощённое соответствие клавишам Hack-стандарта (базовые ASCII работают "как есть")
        self.vm.write_mem(KBD_ADDR, code)
        self.kbd_var.set(f"код клавиши: {code}  ({event.keysym})")

    def _on_key_release(self, event):
        self.vm.write_mem(KBD_ADDR, 0)
        self.kbd_var.set("код клавиши: 0")

    # ------------------------------------------------------------ отрисовка экрана
    def _clear_screen_image(self):
        self.screen_img.put("white", to=(0, 0, SCREEN_W, SCREEN_H))

    def _apply_screen_updates(self):
        for addr in self.vm.dirty_screen:
            self._redraw_screen_word(addr)

    def _redraw_screen_word(self, addr: int):
        word = self.vm.mem[addr] & 0xFFFF
        rel = addr - SCREEN_BASE
        row = rel // 32
        col_word = rel % 32
        x0 = col_word * 16
        y = row
        colors = []
        for bit in range(16):
            colors.append("black" if (word >> bit) & 1 else "white")
        row_str = "{" + " ".join(colors) + "}"
        self.screen_img.put(row_str, to=(x0, y))

    def _redraw_full_screen(self):
        self._clear_screen_image()
        for addr in range(SCREEN_BASE, KBD_ADDR):
            if self.vm.mem[addr] != 0:
                self._redraw_screen_word(addr)

    # ------------------------------------------------------------ обновление панелей
    def _refresh_all(self):
        self._refresh_code_highlight()
        self._refresh_registers()
        self._refresh_stack()
        self._refresh_segments()
        self._refresh_callstack()

    def _refresh_code_highlight(self):
        self.text.tag_remove("current", "1.0", "end")
        self.text.tag_remove("error_line", "1.0", "end")
        if self.vm.instrs and 0 <= self.vm.pc < len(self.vm.instrs):
            ins = self.vm.instrs[self.vm.pc]
            if ins.line_no > 0:
                start = f"{ins.line_no}.0"
                end = f"{ins.line_no}.end"
                tag = "error_line" if self.vm.error else "current"
                self.text.tag_add(tag, start, end)
                self.text.see(start)

    def _refresh_registers(self):
        for name, val in (("SP", self.vm.sp), ("LCL", self.vm.lcl), ("ARG", self.vm.arg),
                           ("THIS", self.vm.this), ("THAT", self.vm.that)):
            self.reg_tree.item(name, values=(val,))

    def _refresh_stack(self):
        self.stack_list.delete(0, "end")
        sp = self.vm.sp
        top = max(sp - 1, STACK_BASE - 1)
        rows = []
        for addr in range(STACK_BASE, top + 1):
            tags = []
            if addr == self.vm.lcl: tags.append("LCL")
            if addr == self.vm.arg: tags.append("ARG")
            if addr == self.vm.this: tags.append("THIS")
            if addr == self.vm.that: tags.append("THAT")
            tag_str = ("   <- " + ",".join(tags)) if tags else ""
            rows.append(f"[{addr:5d}] = {self.vm.mem[addr]:>6d}{tag_str}")
        for line in reversed(rows):
            self.stack_list.insert("end", line)
        if rows:
            self.stack_list.itemconfig(0, bg="#ffe680")  # верх стека подсвечен

    def _refresh_segments(self):
        self.temp_list.delete(0, "end")
        for i in range(8):
            self.temp_list.insert("end", f"temp[{i}] = {self.vm.mem[TEMP_BASE+i]}")
        self.ptr_list.delete(0, "end")
        self.ptr_list.insert("end", f"pointer[0] (this) = {self.vm.mem[POINTER_BASE]}")
        self.ptr_list.insert("end", f"pointer[1] (that) = {self.vm.mem[POINTER_BASE+1]}")
        self.static_list.delete(0, "end")
        for i in range(16):
            self.static_list.insert("end", f"static[{i}] = {self.vm.mem[STATIC_BASE+i]}")

    def _refresh_callstack(self):
        self.call_list.delete(0, "end")
        if not self.vm.frames:
            self.call_list.insert("end", "(верхний уровень, вне функций)")
        for depth, fr in enumerate(self.vm.frames):
            self.call_list.insert(
                "end",
                f"{'  '*depth}{fr.name}  (ARG={fr.arg_addr}, LCL={fr.lcl_addr}, возврат к #{fr.ret_pc})"
            )


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    app = VMApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()