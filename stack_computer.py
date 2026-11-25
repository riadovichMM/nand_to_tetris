#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SC-16 — 16-битный стековый компьютер + язык SC («Stack C»).
Один файл, только стандартная библиотека:   python sc16.py

  * CPU: стековая машина (данные + возвраты + указатель кадра), 44 команды
  * Память: 32К слов, экран 128x80 (1 бит/пиксель) и клавиатура — как в nand2tetris
  * Язык SC: маленький Си (int, массивы, указатели, функции, рекурсия)
  * Полнота по Тьюрингу: условный переход + чтение/запись памяти + арифметика
    (пример «Brainf*ck» запускает интерпретатор BF внутри этой машины)
"""
import bisect
import random
import re
import time
import tkinter as tk
from tkinter import ttk

# ============================================================================
#  КАРТА ПАМЯТИ (адресуются 16-битные слова, адрес 15 бит)
# ============================================================================
RAM_END = 16384                      # 0..16383  — обычное ОЗУ (код, данные, кадры)
SCREEN = 16384                       # экран: 80 строк по 8 слов
SCR_W, SCR_H = 128, 80
WPR = SCR_W // 16                    # слов в строке экрана
SCREEN_END = SCREEN + SCR_H * WPR    # 17024; дальше до 24575 — ещё ОЗУ
KBD = 24576                          # клавиатура (код нажатой клавиши, 0 — нет)
CLOCK = 24577                        # миллисекунды (младшие 16 бит)
RND = 24578                          # случайное слово при каждом чтении
LEDS = 24579                         # 16 лампочек
FONT = 24832                         # ПЗУ знакогенератора: 8 слов на символ ASCII 32..126
MEM_SIZE = 32768
DSTACK, RSTACK = 256, 1024
ZOOM = 4

# Шрифт 5x7 (колонки, бит0 = верхняя строка) ASCII 32..126
_FONT5 = """
00 00 00 00 00|00 00 5F 00 00|00 07 00 07 00|14 7F 14 7F 14|24 2A 7F 2A 12|23 13 08 64 62|36 49 55 22 50|00 05 03 00 00
00 1C 22 41 00|00 41 22 1C 00|14 08 3E 08 14|08 08 3E 08 08|00 50 30 00 00|08 08 08 08 08|00 60 60 00 00|20 10 08 04 02
3E 51 49 45 3E|00 42 7F 40 00|42 61 51 49 46|21 41 45 4B 31|18 14 12 7F 10|27 45 45 45 39|3C 4A 49 49 30|01 71 09 05 03
36 49 49 49 36|06 49 49 29 1E|00 36 36 00 00|00 56 36 00 00|08 14 22 41 00|14 14 14 14 14|00 41 22 14 08|02 01 51 09 06
32 49 79 41 3E|7E 11 11 11 7E|7F 49 49 49 36|3E 41 41 41 22|7F 41 41 22 1C|7F 49 49 49 41|7F 09 09 09 01|3E 41 49 49 7A
7F 08 08 08 7F|00 41 7F 41 00|20 40 41 3F 01|7F 08 14 22 41|7F 40 40 40 40|7F 02 0C 02 7F|7F 04 08 10 7F|3E 41 41 41 3E
7F 09 09 09 06|3E 41 51 21 5E|7F 09 19 29 46|46 49 49 49 31|01 01 7F 01 01|3F 40 40 40 3F|1F 20 40 20 1F|3F 40 38 40 3F
63 14 08 14 63|07 08 70 08 07|61 51 49 45 43|00 7F 41 41 00|02 04 08 10 20|00 41 41 7F 00|04 02 01 02 04|40 40 40 40 40
00 01 02 04 00|20 54 54 54 78|7F 48 44 44 38|38 44 44 44 20|38 44 44 48 7F|38 54 54 54 18|08 7E 09 01 02|0C 52 52 52 3E
7F 08 04 04 78|00 44 7D 40 00|20 40 44 3D 00|7F 10 28 44 00|00 41 7F 40 00|7C 04 78 04 78|7C 08 04 04 78|38 44 44 44 38
7C 14 14 14 08|08 14 14 18 7C|7C 08 04 04 08|48 54 54 54 20|04 3F 44 40 20|3C 40 40 20 7C|1C 20 40 20 1C|3C 40 30 40 3C
44 28 10 28 44|0C 50 50 50 3C|44 64 54 4C 44|00 08 36 41 00|00 00 7F 00 00|00 41 36 08 00|10 08 08 10 08
"""


def _build_font_rom():
    """Переводим колонки в строки: слово = 6 бит строки глифа (бит0 = левый пиксель)."""
    glyphs = [[int(b, 16) for b in g.split()] for g in _FONT5.replace("\n", "|").split("|") if g.strip()]
    assert len(glyphs) == 95, len(glyphs)
    rom = []
    for cols in glyphs:
        for r in range(8):
            rom.append(sum(((cols[c] >> r) & 1) << c for c in range(5)) if r < 7 else 0)
    return rom


FONT_ROM = _build_font_rom()

# ============================================================================
#  НАБОР КОМАНД
#   слово с битом 15 = 1  → LIT (положить 15-битное число 0..32767)
#   иначе слово — номер команды без операндов (адреса берутся со стека)
# ============================================================================
OPS = ['NOP', 'HALT', 'DUP', 'DROP', 'SWAP', 'OVER', 'ROT',
       'ADD', 'SUB', 'MUL', 'DIV', 'MOD', 'AND', 'OR', 'XOR', 'NOT', 'NEG',
       'SHL', 'SHR', 'SAR',
       'EQ', 'NE', 'LT', 'LE', 'GT', 'GE', 'LNOT',
       'LOAD', 'STORE', 'JMP', 'JZ', 'JNZ', 'CALL', 'RET',
       'TOR', 'FROMR', 'RFETCH',
       'FPGET', 'FPSET', 'ENTER', 'LEAVE', 'LGET', 'LSET', 'LADDR']
OP = {n: i for i, n in enumerate(OPS)}


class Fault(Exception):
    pass


def s16(x):
    return x - 65536 if x & 0x8000 else x


class CPU:
    def __init__(self):
        self.mem = [0] * MEM_SIZE
        self.ds, self.rs = [], []
        self.dirty = set()
        self.full_redraw = True
        self.key = 0
        self.t0 = time.time()
        self.pc, self.fp, self.limit = 0, RAM_END, 0
        self.halted, self.fault, self.steps = True, None, 0
        self.optab = self._build_optab()

    # ---- загрузка -----------------------------------------------------
    def load(self, image):
        self.mem[:] = [0] * MEM_SIZE
        self.mem[:len(image)] = image
        self.ds.clear()
        self.rs.clear()
        self.pc, self.fp, self.limit = 0, RAM_END, len(image)
        self.halted, self.fault, self.steps = False, None, 0
        self.key = 0
        self.t0 = time.time()
        self.dirty.clear()
        self.full_redraw = True

    # ---- ввод/вывод ---------------------------------------------------
    def io_read(self, a):
        if a == KBD:
            return self.key
        if a == CLOCK:
            return int((time.time() - self.t0) * 1000) & 0xFFFF
        if a == RND:
            return random.getrandbits(16)
        if FONT <= a < FONT + len(FONT_ROM):
            return FONT_ROM[a - FONT]
        return self.mem[a]

    def io_write(self, a, v):
        if SCREEN <= a < SCREEN_END:
            self.mem[a] = v
            self.dirty.add(a)
        elif a < KBD or a == LEDS:
            self.mem[a] = v
        # KBD, CLOCK, RND, ПЗУ шрифта — только чтение

    # ---- выполнение ---------------------------------------------------
    def run(self, n):
        mem, ds, optab = self.mem, self.ds, self.optab
        pc = self.pc
        i = 0
        try:
            while i < n:
                pc = self.pc
                w = mem[pc]
                self.pc = (pc + 1) & 0x7FFF
                if w & 0x8000:
                    ds.append(w & 0x7FFF)
                else:
                    optab[w]()
                if len(ds) > DSTACK:
                    raise Fault('переполнение стека данных')
                i += 1
                if self.halted:
                    break
        except Fault as e:
            self.pc, self.fault, self.halted = pc, str(e), True
        except IndexError:
            self.pc, self.fault, self.halted = pc, 'стек данных пуст (не хватает операндов)', True
        self.steps += i

    def _build_optab(self):
        cpu, ds, rs, mem = self, self.ds, self.rs, self.mem
        T = {}

        def op(f):
            T[f.__name__.rstrip('_').upper()] = f
            return f

        @op
        def nop(): pass

        @op
        def halt(): cpu.halted = True

        @op
        def dup(): ds.append(ds[-1])

        @op
        def drop(): ds.pop()

        @op
        def swap(): ds[-1], ds[-2] = ds[-2], ds[-1]

        @op
        def over(): ds.append(ds[-2])

        @op
        def rot(): ds.append(ds.pop(-3))               # ( a b c -- b c a )

        @op
        def add():
            b = ds.pop(); ds[-1] = (ds[-1] + b) & 0xFFFF

        @op
        def sub():
            b = ds.pop(); ds[-1] = (ds[-1] - b) & 0xFFFF

        @op
        def mul():
            b = ds.pop(); ds[-1] = (ds[-1] * b) & 0xFFFF

        @op
        def div():
            b = s16(ds.pop()); a = s16(ds[-1])
            if b == 0:
                raise Fault('деление на ноль')
            q = abs(a) // abs(b)
            ds[-1] = (-q if (a < 0) != (b < 0) else q) & 0xFFFF

        @op
        def mod():
            b = s16(ds.pop()); a = s16(ds[-1])
            if b == 0:
                raise Fault('деление на ноль')
            r = abs(a) % abs(b)
            ds[-1] = (-r if a < 0 else r) & 0xFFFF

        @op
        def and_():
            b = ds.pop(); ds[-1] &= b

        @op
        def or_():
            b = ds.pop(); ds[-1] |= b

        @op
        def xor():
            b = ds.pop(); ds[-1] ^= b

        @op
        def not_(): ds[-1] ^= 0xFFFF

        @op
        def neg(): ds[-1] = (-ds[-1]) & 0xFFFF

        @op
        def shl():
            n = ds.pop(); ds[-1] = ((ds[-1] << n) & 0xFFFF) if n < 16 else 0

        @op
        def shr():
            n = ds.pop(); ds[-1] = (ds[-1] >> n) if n < 16 else 0

        @op
        def sar():
            n = ds.pop(); ds[-1] = (s16(ds[-1]) >> min(n, 15)) & 0xFFFF

        @op
        def eq():
            b = ds.pop(); ds[-1] = 1 if ds[-1] == b else 0

        @op
        def ne():
            b = ds.pop(); ds[-1] = 1 if ds[-1] != b else 0

        @op
        def lt():
            b = s16(ds.pop()); ds[-1] = 1 if s16(ds[-1]) < b else 0

        @op
        def le():
            b = s16(ds.pop()); ds[-1] = 1 if s16(ds[-1]) <= b else 0

        @op
        def gt():
            b = s16(ds.pop()); ds[-1] = 1 if s16(ds[-1]) > b else 0

        @op
        def ge():
            b = s16(ds.pop()); ds[-1] = 1 if s16(ds[-1]) >= b else 0

        @op
        def lnot(): ds[-1] = 1 if ds[-1] == 0 else 0

        @op
        def load():
            a = ds[-1] & 0x7FFF
            ds[-1] = mem[a] if a < KBD else cpu.io_read(a)

        @op
        def store():                                     # ( v addr -- )
            a = ds.pop() & 0x7FFF; v = ds.pop()
            if a < RAM_END:
                mem[a] = v
            else:
                cpu.io_write(a, v)

        @op
        def jmp(): cpu.pc = ds.pop() & 0x7FFF

        @op
        def jz():                                        # ( flag addr -- )
            a = ds.pop()
            if ds.pop() == 0:
                cpu.pc = a & 0x7FFF

        @op
        def jnz():
            a = ds.pop()
            if ds.pop() != 0:
                cpu.pc = a & 0x7FFF

        @op
        def call():
            a = ds.pop()
            rs.append(cpu.pc)
            if len(rs) > RSTACK:
                raise Fault('переполнение стека возвратов')
            cpu.pc = a & 0x7FFF

        @op
        def ret():
            if not rs:
                raise Fault('RET при пустом стеке возвратов')
            cpu.pc = rs.pop()

        @op
        def tor(): rs.append(ds.pop())

        @op
        def fromr():
            if not rs:
                raise Fault('стек возвратов пуст')
            ds.append(rs.pop())

        @op
        def rfetch():
            if not rs:
                raise Fault('стек возвратов пуст')
            ds.append(rs[-1])

        @op
        def fpget(): ds.append(cpu.fp)

        @op
        def fpset(): cpu.fp = ds.pop()

        @op
        def enter():                                     # ( n -- )  FP -= n
            fp = (cpu.fp - ds.pop()) & 0xFFFF
            if fp < cpu.limit or fp > RAM_END:
                raise Fault('переполнение стека кадров (слишком глубокая рекурсия)')
            cpu.fp = fp

        @op
        def leave(): cpu.fp = (cpu.fp + ds.pop()) & 0xFFFF

        @op
        def lget(): ds[-1] = mem[(cpu.fp + ds[-1]) & 0x3FFF]

        @op
        def lset():                                      # ( v i -- )
            i = ds.pop(); mem[(cpu.fp + i) & 0x3FFF] = ds.pop()

        @op
        def laddr(): ds[-1] = (cpu.fp + ds[-1]) & 0xFFFF

        def bad():
            raise Fault('неизвестная команда')

        table = [bad] * 0x8000
        for name, f in T.items():
            table[OP[name]] = f
        return table


def dis(w, syms=None):
    if w & 0x8000:
        v = w & 0x7FFF
        s = 'LIT %d' % v
        if syms and v in syms:
            s += '      ; ' + syms[v]
        elif 32 <= v < 127:
            s += "      ; '%s'" % chr(v)
        return s
    return OPS[w] if w < len(OPS) else '???  0x%04X' % w


# ============================================================================
#  ЯЗЫК SC: лексер, парсер, генератор кода
# ============================================================================
class CompileError(Exception):
    def __init__(self, msg, line=0):
        Exception.__init__(self, msg)
        self.msg, self.line = msg, line


class NotConst(Exception):
    pass


TOKEN_RE = re.compile(r"""
    (?P<ws>   \s+ | //[^\n]* | /\*.*?\*/ )
  | (?P<num>  0[xX][0-9a-fA-F]+ | 0[bB][01]+ | \d+ )
  | (?P<id>   [A-Za-z_][A-Za-z_0-9]* )
  | (?P<chr>  '(?:\\.|[^'\\])' )
  | (?P<str>  "(?:\\.|[^"\\])*" )
  | (?P<op>   >>>=? | <<= | >>= | \+\+ | -- | <= | >= | == | != | && | \|\| | [-+*/%&|^]= | << | >> | [-+*/%&|^~!<>=?:;,(){}\[\]] )
""", re.X | re.S)
KEYWORDS = {'int', 'void', 'if', 'else', 'while', 'do', 'for', 'return', 'break', 'continue', 'const'}
ESC = {'n': '\n', 't': '\t', 'r': '\r', '0': '\0', '\\': '\\', "'": "'", '"': '"', 'b': '\b'}


def unescape(s):
    out, i = [], 0
    while i < len(s):
        if s[i] == '\\' and i + 1 < len(s):
            out.append(ESC.get(s[i + 1], s[i + 1])); i += 2
        else:
            out.append(s[i]); i += 1
    return ''.join(out)


def tokenize(src):
    toks, pos, line = [], 0, 1
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            raise CompileError('неожиданный символ %r' % src[pos], line)
        kind, text = m.lastgroup, m.group()
        if kind == 'num':
            base = 16 if text[:2].lower() == '0x' else 2 if text[:2].lower() == 'b' or text[:2].lower() == '0b' else 10
            toks.append(('num', int(text, base), line))
        elif kind == 'chr':
            toks.append(('num', ord(unescape(text[1:-1])), line))
        elif kind == 'str':
            toks.append(('str', unescape(text[1:-1]), line))
        elif kind == 'id':
            toks.append(('kw' if text in KEYWORDS else 'id', text, line))
        elif kind == 'op':
            toks.append(('op', text, line))
        line += text.count('\n')
        pos = m.end()
    toks.append(('eof', '', line))
    return toks


BINPREC = {'||': 1, '&&': 2, '|': 3, '^': 4, '&': 5, '==': 6, '!=': 6,
           '<': 7, '<=': 7, '>': 7, '>=': 7, '<<': 8, '>>': 8, '>>>': 8,
           '+': 9, '-': 9, '*': 10, '/': 10, '%': 10}
ASSIGN_OPS = {'=', '+=', '-=', '*=', '/=', '%=', '&=', '|=', '^=', '<<=', '>>='}


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self, k=0):
        return self.t[min(self.i + k, len(self.t) - 1)]

    def next(self):
        tok = self.t[self.i]
        if tok[0] != 'eof':
            self.i += 1
        return tok

    def is_(self, v):
        tok = self.peek()
        return tok[0] in ('op', 'kw') and tok[1] == v

    def accept(self, v):
        if self.is_(v):
            self.next()
            return True
        return False

    def expect(self, v):
        if not self.accept(v):
            tok = self.peek()
            raise CompileError("ожидалось '%s', а найдено '%s'" % (v, tok[1] or 'конец файла'), tok[2])

    def stars(self):
        while self.accept('*'):          # int *p — звёздочки допустимы (указатель = int)
            pass

    def ident(self):
        tok = self.next()
        if tok[0] != 'id':
            raise CompileError('ожидалось имя', tok[2])
        return tok[1]

    # ---- верхний уровень ---------------------------------------------
    def program(self):
        items = []
        while self.peek()[0] != 'eof':
            line = self.peek()[2]
            if self.accept('const'):
                name = self.ident(); self.expect('=')
                e = self.assign(); self.expect(';')
                items.append(('const', name, e, line))
                continue
            if not (self.accept('int') or self.accept('void')):
                raise CompileError('ожидалось описание: int/void/const', line)
            self.stars()
            name = self.ident()
            if self.accept('('):
                params = []
                if not self.is_(')'):
                    if self.is_('void') and self.peek(1)[1] == ')':
                        self.next()
                    else:
                        while True:
                            self.expect('int'); self.stars(); params.append(self.ident())
                            if not self.accept(','):
                                break
                self.expect(')')
                body = self.block()
                items.append(('func', name, params, body, line))
            else:
                while True:
                    items.append(self.gdecl(name, line))
                    if not self.accept(','):
                        break
                    self.stars()
                    name = self.ident()
                self.expect(';')
        return items

    def gdecl(self, name, line):
        size, is_arr, init = None, False, None
        if self.accept('['):
            is_arr = True
            if not self.is_(']'):
                size = self.assign()
            self.expect(']')
        if self.accept('='):
            init = self.initializer()
        return ('gvar', name, size, is_arr, init, line)

    def initializer(self):
        if self.accept('{'):
            es = []
            while not self.is_('}'):
                es.append(self.assign())
                if not self.accept(','):
                    break
            self.expect('}')
            return ('list', es)
        return self.assign()

    # ---- операторы ----------------------------------------------------
    def block(self):
        self.expect('{')
        st = []
        while not self.is_('}'):
            if self.peek()[0] == 'eof':
                raise CompileError("не закрыта '{'", self.peek()[2])
            st.append(self.stmt())
        self.next()
        return ('block', st)

    def decls(self):
        self.expect('int')
        ds = []
        while True:
            self.stars()
            line = self.peek()[2]
            name = self.ident()
            size, init = None, None
            if self.accept('['):
                size = self.assign()
                self.expect(']')
            if self.accept('='):
                init = self.initializer()
            ds.append(('decl', name, size, init, line))
            if not self.accept(','):
                break
        return ('decls', ds)

    def stmt(self):
        tok = self.peek()
        v, line = tok[1], tok[2]
        if tok[0] == 'op' and v == '{':
            return self.block()
        if tok[0] == 'op' and v == ';':
            self.next(); return ('empty',)
        if tok[0] == 'kw':
            if v == 'int':
                d = self.decls(); self.expect(';'); return d
            if v == 'if':
                self.next(); self.expect('('); c = self.expr(); self.expect(')')
                th = self.stmt()
                el = self.stmt() if self.accept('else') else None
                return ('if', c, th, el)
            if v == 'while':
                self.next(); self.expect('('); c = self.expr(); self.expect(')')
                return ('while', c, self.stmt())
            if v == 'do':
                self.next(); body = self.stmt(); self.expect('while'); self.expect('(')
                c = self.expr(); self.expect(')'); self.expect(';')
                return ('do', body, c)
            if v == 'for':
                self.next(); self.expect('(')
                init = None
                if self.is_('int'):
                    init = self.decls()
                elif not self.is_(';'):
                    init = ('expr', self.expr())
                self.expect(';')
                cond = None if self.is_(';') else self.expr()
                self.expect(';')
                step = None if self.is_(')') else self.expr()
                self.expect(')')
                return ('for', init, cond, step, self.stmt())
            if v == 'return':
                self.next()
                e = None if self.is_(';') else self.expr()
                self.expect(';')
                return ('return', e, line)
            if v == 'break':
                self.next(); self.expect(';'); return ('break', line)
            if v == 'continue':
                self.next(); self.expect(';'); return ('continue', line)
        e = self.expr()
        self.expect(';')
        return ('expr', e)

    # ---- выражения ----------------------------------------------------
    def expr(self):
        return self.assign()

    def assign(self):
        lhs = self.ternary()
        tok = self.peek()
        if tok[0] == 'op' and tok[1] in ASSIGN_OPS:
            self.next()
            if not (lhs[0] in ('var', 'index') or (lhs[0] == 'un' and lhs[1] == '*')):
                raise CompileError('слева от %s должно стоять имя, a[i] или *p' % tok[1], tok[2])
            return ('assign', tok[1], lhs, self.assign(), tok[2])
        return lhs

    def ternary(self):
        c = self.binary(1)
        if self.accept('?'):
            a = self.assign(); self.expect(':'); b = self.ternary()
            return ('cond', c, a, b)
        return c

    def binary(self, minprec):
        lhs = self.unary()
        while True:
            tok = self.peek()
            if tok[0] != 'op' or tok[1] not in BINPREC or BINPREC[tok[1]] < minprec:
                return lhs
            self.next()
            rhs = self.binary(BINPREC[tok[1]] + 1)
            lhs = ('bin', tok[1], lhs, rhs, tok[2])

    def unary(self):
        tok = self.peek()
        if tok[0] == 'op' and tok[1] in ('-', '!', '~', '*', '&'):
            self.next()
            x = self.unary()
            if tok[1] == '-' and x[0] == 'num':
                return ('num', -x[1])
            return ('un', tok[1], x, tok[2])
        if tok[0] == 'op' and tok[1] in ('++', '--'):
            self.next()
            x = self.unary()
            self.check_lv(x, tok[2])
            return ('incdec', tok[1], True, x, tok[2])
        return self.postfix()

    def check_lv(self, x, line):
        if not (x[0] in ('var', 'index') or (x[0] == 'un' and x[1] == '*')):
            raise CompileError('++/-- применимо к имени, a[i] или *p', line)

    def postfix(self):
        e = self.primary()
        while True:
            tok = self.peek()
            if self.accept('['):
                idx = self.expr(); self.expect(']')
                e = ('index', e, idx, tok[2])
            elif tok[0] == 'op' and tok[1] in ('++', '--'):
                self.next()
                self.check_lv(e, tok[2])
                e = ('incdec', tok[1], False, e, tok[2])
            else:
                return e

    def primary(self):
        tok = self.next()
        k, v, line = tok
        if k == 'num':
            return ('num', v)
        if k == 'str':
            return ('str', v)
        if k == 'id':
            if self.accept('('):
                args = []
                if not self.is_(')'):
                    while True:
                        args.append(self.assign())
                        if not self.accept(','):
                            break
                self.expect(')')
                return ('call', v, args, line)
            return ('var', v, line)
        if k == 'op' and v == '(':
            e = self.expr(); self.expect(')')
            return e
        raise CompileError("неожиданный '%s'" % (v or 'конец файла'), line)


def cdiv(a, b):
    if b == 0:
        raise CompileError('деление на ноль в константе')
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def const_eval(e, consts):
    """Вычислить константное выражение (числа, const-имена, операции)."""
    k = e[0]
    if k == 'num':
        return e[1]
    if k == 'var':
        if e[1] in consts:
            return consts[e[1]]
        raise NotConst()
    if k == 'un' and e[1] in ('-', '~', '!'):
        x = const_eval(e[2], consts)
        return -x if e[1] == '-' else ~x if e[1] == '~' else int(x == 0)
    if k == 'cond':
        return const_eval(e[2] if const_eval(e[1], consts) else e[3], consts)
    if k == 'bin':
        op = e[1]
        a, b = const_eval(e[2], consts), const_eval(e[3], consts)
        a, b = s16(a & 0xFFFF), s16(b & 0xFFFF)
        r = {'+': lambda: a + b, '-': lambda: a - b, '*': lambda: a * b,
             '/': lambda: cdiv(a, b), '%': lambda: a - cdiv(a, b) * b,
             '&': lambda: a & b, '|': lambda: a | b, '^': lambda: a ^ b,
             '<<': lambda: a << b if 0 <= b < 16 else 0,
             '>>': lambda: a >> min(max(b, 0), 15),
             '>>>': lambda: (a & 0xFFFF) >> b if 0 <= b < 16 else 0,
             '==': lambda: int(a == b), '!=': lambda: int(a != b),
             '<': lambda: int(a < b), '<=': lambda: int(a <= b),
             '>': lambda: int(a > b), '>=': lambda: int(a >= b),
             '&&': lambda: int(bool(a) and bool(b)), '||': lambda: int(bool(a) or bool(b))}[op]()
        return r
    raise NotConst()


BINOP = {'+': 'ADD', '-': 'SUB', '*': 'MUL', '/': 'DIV', '%': 'MOD', '&': 'AND', '|': 'OR',
         '^': 'XOR', '<<': 'SHL', '>>': 'SAR', '>>>': 'SHR', '==': 'EQ', '!=': 'NE',
         '<': 'LT', '<=': 'LE', '>': 'GT', '>=': 'GE'}
PREDEF = {'SCREEN': SCREEN, 'KBD': KBD, 'CLOCK': CLOCK, 'RND': RND, 'LEDS': LEDS,
          'FONT': FONT, 'SW': SCR_W, 'SH': SCR_H}


def walk(node, out):
    if isinstance(node, tuple):
        if node and node[0] in ('var', 'call') and len(node) > 1 and isinstance(node[1], str):
            out.add(node[1])
        for x in node:
            walk(x, out)
    elif isinstance(node, list):
        for x in node:
            walk(x, out)


class Program:
    def __init__(self, image, syms, code_len):
        self.image, self.syms, self.code_len = image, syms, code_len
        self.funcs = sorted((a, n) for a, n in syms.items() if n.endswith('()'))


class Compiler:
    def __init__(self, funcs, gvars, consts):
        self.funcs, self.gvars, self.consts = funcs, gvars, consts
        self.code, self.data, self.labels = [], [], {}
        self.nlabel, self.strpool = 0, {}

    # ---- низкий уровень ----------------------------------------------
    def emit(self, op): self.code.append(OP[op])

    def lit(self, n):
        n &= 0xFFFF
        if n < 0x8000:
            self.code.append(0x8000 | n)
        else:
            self.code.append(0x8000 | (~n & 0xFFFF))
            self.emit('NOT')

    def litl(self, label): self.code.append(('L', label))

    def place(self, label): self.labels[label] = ('c', len(self.code))

    def newl(self):
        self.nlabel += 1
        return 'L%d' % self.nlabel

    def jump(self, label, op='JMP'):
        self.litl(label); self.emit(op)

    def strlabel(self, s):
        if s not in self.strpool:
            self.strpool[s] = 's%d' % len(self.strpool)
        return self.strpool[s]

    # ---- главная точка --------------------------------------------------
    def run(self):
        if 'main' not in self.funcs:
            raise CompileError('нет функции main()')
        seen, todo = set(), ['main']
        while todo:
            n = todo.pop()
            if n in seen:
                continue
            seen.add(n)
            if n in self.funcs:
                refs = set(); walk(self.funcs[n][3], refs); todo.extend(refs)
        self.litl('f_main'); self.emit('CALL'); self.emit('HALT')
        for name, f in self.funcs.items():
            if name in seen:
                self.gen_func(f)
        for name, g in self.gvars.items():
            if name in seen:
                self.emit_global(g)
        for s, lab in self.strpool.items():
            self.labels[lab] = ('d', len(self.data))
            self.data.extend([ord(c) & 0xFFFF for c in s] + [0])
        return self.link()

    def link(self):
        n = len(self.code)

        def addr(lab):
            kind, i = self.labels[lab]
            return i if kind == 'c' else n + i
        words = [(0x8000 | addr(w[1])) if isinstance(w, tuple) else w for w in self.code]
        words += [addr(w[1]) if isinstance(w, tuple) else w for w in self.data]
        if len(words) > RAM_END - 600:
            raise CompileError('программа слишком большая (%d слов)' % len(words))
        syms = {}
        for lab, (kind, i) in self.labels.items():
            if lab.startswith('f_'):
                syms[addr(lab)] = lab[2:] + '()'
            elif lab.startswith('g_'):
                syms[addr(lab)] = lab[2:]
        return Program(words, syms, n)

    # ---- глобальные данные ---------------------------------------------
    def emit_global(self, g):
        _, name, size_e, is_arr, init, line = g

        def val(e):
            if e[0] == 'str':
                return ('L', self.strlabel(e[1]))
            try:
                return const_eval(e, self.consts) & 0xFFFF
            except NotConst:
                raise CompileError('инициализатор глобальной переменной должен быть константой', line)
        items = []
        if is_arr:
            if init is None:
                if size_e is None:
                    raise CompileError("массив '%s' без размера и без значений" % name, line)
            elif init[0] == 'list':
                items = [val(e) for e in init[1]]
            elif init[0] == 'str':
                items = [ord(c) & 0xFFFF for c in init[1]] + [0]
            else:
                raise CompileError('массиву нужен список {..} или строка', line)
            if size_e is not None:
                try:
                    n = const_eval(size_e, self.consts)
                except NotConst:
                    raise CompileError('размер массива должен быть константой', line)
                if n <= 0 or n > 8000:
                    raise CompileError('плохой размер массива', line)
                if len(items) > n:
                    raise CompileError("слишком много значений для '%s'" % name, line)
                items += [0] * (n - len(items))
        else:
            items = [val(init)] if init is not None else [0]
        self.labels['g_' + name] = ('d', len(self.data))
        self.data.extend(items)

    # ---- функции --------------------------------------------------------
    def alloc(self, n):
        s = self.nslots
        self.nslots += n
        return s

    def gen_func(self, f):
        _, name, params, body, line = f
        self.scopes, self.nslots, self.loops = [{}], 0, []
        self.epilog = 'E_' + name
        for p in params:
            if p in self.scopes[0]:
                raise CompileError("повторный параметр '%s'" % p, line)
            self.scopes[0][p] = ('var', self.alloc(1))
        self.place('f_' + name)
        p_enter = len(self.code); self.lit(0); self.emit('ENTER')
        for i in reversed(range(len(params))):        # последний аргумент — на вершине
            self.lit(i); self.emit('LSET')
        self.gen_stmt(body)
        self.lit(0)                                   # значение по умолчанию
        self.place(self.epilog)
        p_leave = len(self.code); self.lit(0); self.emit('LEAVE'); self.emit('RET')
        if self.nslots > 8000:
            raise CompileError("слишком большой кадр у '%s'" % name, line)
        self.code[p_enter] = self.code[p_leave] = 0x8000 | self.nslots

    def find(self, name, line):
        for sc in reversed(self.scopes):
            if name in sc:
                kind, slot = sc[name]
                return ('local', slot, kind == 'arr')
        if name in self.consts:
            return ('const', self.consts[name], False)
        if name in self.gvars:
            return ('global', 'g_' + name, self.gvars[name][3])
        raise CompileError("неизвестное имя '%s'" % name, line)

    # ---- операторы ------------------------------------------------------
    def gen_decl(self, d):
        _, name, size_e, init, line = d
        if name in self.scopes[-1]:
            raise CompileError("'%s' уже объявлено" % name, line)
        if size_e is not None:
            if init is not None:
                raise CompileError('локальные массивы нельзя инициализировать', line)
            try:
                n = const_eval(size_e, self.consts)
            except NotConst:
                raise CompileError('размер массива должен быть константой', line)
            if n <= 0 or n > 4000:
                raise CompileError('плохой размер массива', line)
            self.scopes[-1][name] = ('arr', self.alloc(n))
        else:
            slot = self.alloc(1)
            self.scopes[-1][name] = ('var', slot)
            if init is not None:
                if init[0] == 'list':
                    raise CompileError('{..} только для массивов', line)
                self.gen(init); self.lit(slot); self.emit('LSET')

    def gen_expr_stmt(self, e):
        if e[0] == 'assign':
            self.gen_assign(e, False)
        elif e[0] == 'incdec':
            self.gen_incdec(e, False)
        else:
            self.gen(e); self.emit('DROP')

    def gen_stmt(self, s):
        k = s[0]
        if k == 'block':
            self.scopes.append({})
            for x in s[1]:
                self.gen_stmt(x)
            self.scopes.pop()
        elif k == 'decls':
            for d in s[1]:
                self.gen_decl(d)
        elif k == 'expr':
            self.gen_expr_stmt(s[1])
        elif k == 'empty':
            pass
        elif k == 'if':
            Lelse = self.newl()
            self.gen(s[1]); self.jump(Lelse, 'JZ')
            self.gen_stmt(s[2])
            if s[3] is not None:
                Lend = self.newl()
                self.jump(Lend); self.place(Lelse)
                self.gen_stmt(s[3]); self.place(Lend)
            else:
                self.place(Lelse)
        elif k == 'while':
            Lt, Le = self.newl(), self.newl()
            self.place(Lt); self.gen(s[1]); self.jump(Le, 'JZ')
            self.loops.append((Le, Lt)); self.gen_stmt(s[2]); self.loops.pop()
            self.jump(Lt); self.place(Le)
        elif k == 'do':
            Lt, Lc, Le = self.newl(), self.newl(), self.newl()
            self.place(Lt)
            self.loops.append((Le, Lc)); self.gen_stmt(s[1]); self.loops.pop()
            self.place(Lc); self.gen(s[2]); self.jump(Lt, 'JNZ'); self.place(Le)
        elif k == 'for':
            _, init, cond, step, body = s
            self.scopes.append({})
            if init is not None:
                self.gen_stmt(init)
            Lt, Lc, Le = self.newl(), self.newl(), self.newl()
            self.place(Lt)
            if cond is not None:
                self.gen(cond); self.jump(Le, 'JZ')
            self.loops.append((Le, Lc)); self.gen_stmt(body); self.loops.pop()
            self.place(Lc)
            if step is not None:
                self.gen_expr_stmt(step)
            self.jump(Lt); self.place(Le)
            self.scopes.pop()
        elif k == 'return':
            if s[1] is None:
                self.lit(0)
            else:
                self.gen(s[1])
            self.jump(self.epilog)
        elif k in ('break', 'continue'):
            if not self.loops:
                raise CompileError("'%s' вне цикла" % k, s[1])
            self.jump(self.loops[-1][0 if k == 'break' else 1])
        else:
            raise CompileError('внутренняя ошибка: оператор ' + k)

    # ---- выражения ------------------------------------------------------
    def gen(self, e):
        k = e[0]
        if k in ('bin', 'un', 'cond'):
            try:
                self.lit(const_eval(e, self.consts))
                return
            except NotConst:
                pass
        if k == 'num':
            self.lit(e[1])
        elif k == 'str':
            self.litl(self.strlabel(e[1]))
        elif k == 'var':
            kind, x, is_arr = self.find(e[1], e[2])
            if kind == 'const':
                self.lit(x)
            elif kind == 'local':
                self.lit(x)
                self.emit('LADDR' if is_arr else 'LGET')
            else:
                self.litl(x)
                if not is_arr:
                    self.emit('LOAD')
        elif k == 'un':
            op = e[1]
            if op == '&':
                self.gen_addr(e[2])
            else:
                self.gen(e[2])
                self.emit({'*': 'LOAD', '-': 'NEG', '~': 'NOT', '!': 'LNOT'}[op])
        elif k == 'index':
            self.gen_addr(e); self.emit('LOAD')
        elif k == 'bin':
            self.gen_bin(e)
        elif k == 'cond':
            Lelse, Lend = self.newl(), self.newl()
            self.gen(e[1]); self.jump(Lelse, 'JZ')
            self.gen(e[2]); self.jump(Lend)
            self.place(Lelse); self.gen(e[3]); self.place(Lend)
        elif k == 'assign':
            self.gen_assign(e, True)
        elif k == 'incdec':
            self.gen_incdec(e, True)
        elif k == 'call':
            name, args, line = e[1], e[2], e[3]
            f = self.funcs.get(name)
            if f is None:
                raise CompileError("неизвестная функция '%s'" % name, line)
            if len(args) != len(f[2]):
                raise CompileError("'%s' ждёт аргументов: %d, дано: %d" % (name, len(f[2]), len(args)), line)
            for a in args:
                self.gen(a)
            self.litl('f_' + name); self.emit('CALL')
        else:
            raise CompileError('внутренняя ошибка: выражение ' + k)

    def gen_bin(self, e):
        op = e[1]
        if op == '&&':
            Lf, Le = self.newl(), self.newl()
            self.gen(e[2]); self.jump(Lf, 'JZ')
            self.gen(e[3]); self.emit('LNOT'); self.emit('LNOT'); self.jump(Le)
            self.place(Lf); self.lit(0); self.place(Le)
        elif op == '||':
            Lt, Le = self.newl(), self.newl()
            self.gen(e[2]); self.jump(Lt, 'JNZ')
            self.gen(e[3]); self.emit('LNOT'); self.emit('LNOT'); self.jump(Le)
            self.place(Lt); self.lit(1); self.place(Le)
        else:
            self.gen(e[2]); self.gen(e[3]); self.emit(BINOP[op])

    def gen_addr(self, x):
        k = x[0]
        if k == 'var':
            kind, v, is_arr = self.find(x[1], x[2])
            if kind == 'local':
                self.lit(v); self.emit('LADDR')
            elif kind == 'global':
                self.litl(v)
            else:
                raise CompileError("у константы '%s' нет адреса" % x[1], x[2])
        elif k == 'index':
            self.gen(x[1]); self.gen(x[2]); self.emit('ADD')
        elif k == 'un' and x[1] == '*':
            self.gen(x[2])
        else:
            raise CompileError('нельзя взять адрес этого выражения', x[-1] if isinstance(x[-1], int) else 0)

    def lvalue(self, e):
        if e[0] == 'var':
            kind, v, is_arr = self.find(e[1], e[2])
            if kind == 'local' and not is_arr:
                return 'local', v
            if kind == 'global' and not is_arr:
                return 'mem', None
            raise CompileError("нельзя присваивать '%s'" % e[1], e[2])
        return 'mem', None

    def gen_assign(self, e, keep):
        _, op, lhs, rhs, line = e
        binop = None if op == '=' else op[:-1]
        kind, slot = self.lvalue(lhs)
        if kind == 'local':
            if binop:
                self.lit(slot); self.emit('LGET'); self.gen(rhs); self.emit(BINOP[binop])
            else:
                self.gen(rhs)
            if keep:
                self.emit('DUP')
            self.lit(slot); self.emit('LSET')
        else:
            self.gen_addr(lhs)
            if binop:
                self.emit('DUP'); self.emit('LOAD'); self.gen(rhs); self.emit(BINOP[binop])
            else:
                self.gen(rhs)
            if keep:
                self.emit('DUP'); self.emit('ROT'); self.emit('STORE')
            else:
                self.emit('SWAP'); self.emit('STORE')

    def gen_incdec(self, e, keep):
        _, op, prefix, lv, line = e
        d = 'ADD' if op == '++' else 'SUB'
        kind, slot = self.lvalue(lv)
        if kind == 'local':
            self.lit(slot); self.emit('LGET')
            if prefix or not keep:
                self.lit(1); self.emit(d)
                if keep:
                    self.emit('DUP')
            else:
                self.emit('DUP'); self.lit(1); self.emit(d)
            self.lit(slot); self.emit('LSET')
        else:
            self.gen_addr(lv); self.emit('DUP'); self.emit('LOAD')
            if prefix or not keep:
                self.lit(1); self.emit(d)
                if keep:
                    self.emit('DUP'); self.emit('ROT'); self.emit('STORE')
                else:
                    self.emit('SWAP'); self.emit('STORE')
            else:
                self.emit('DUP'); self.lit(1); self.emit(d)
                self.emit('ROT'); self.emit('STORE')


# ============================================================================
#  СТАНДАРТНАЯ БИБЛИОТЕКА (на самом SC; в программу попадает только нужное)
# ============================================================================
LIB_SRC = r"""
int cx;
int cy;

int abs(int x) { if (x < 0) return -x; return x; }
int min(int a, int b) { if (a < b) return a; return b; }
int max(int a, int b) { if (a > b) return a; return b; }
int rand() { return *RND; }

void delay(int ms) {
  int t = *CLOCK;
  while (*CLOCK - t < ms) { }
}

// ---------- графика ----------
void cls() {
  int i = 0;
  while (i < 640) { SCREEN[i] = 0; i++; }
  cx = 0; cy = 0;
}

void pset(int x, int y, int c) {
  if (x < 0 || x >= SW || y < 0 || y >= SH) return;
  int a = SCREEN + y * 8 + (x >> 4);
  int m = 1 << (x & 15);
  if (c) *a = *a | m; else *a = *a & ~m;
}

int pget(int x, int y) {
  if (x < 0 || x >= SW || y < 0 || y >= SH) return 0;
  return (SCREEN[y * 8 + (x >> 4)] >> (x & 15)) & 1;
}

void line(int x0, int y0, int x1, int y1, int c) {
  int dx = abs(x1 - x0);
  int dy = -abs(y1 - y0);
  int sx = x0 < x1 ? 1 : -1;
  int sy = y0 < y1 ? 1 : -1;
  int err = dx + dy;
  while (1) {
    pset(x0, y0, c);
    if (x0 == x1 && y0 == y1) break;
    int e2 = 2 * err;
    if (e2 >= dy) { err += dy; x0 += sx; }
    if (e2 <= dx) { err += dx; y0 += sy; }
  }
}

void rect(int x, int y, int w, int h, int c) {
  int i; int j;
  for (j = 0; j < h; j++) for (i = 0; i < w; i++) pset(x + i, y + j, c);
}

// ---------- текст: 21 колонка x 10 строк, символ 6x8 ----------
void drawchar(int c, int col, int row) {
  int x = col * 6;
  int sh = x & 15;
  int base = SCREEN + row * 64 + (x >> 4);
  int g = FONT + (c - 32) * 8;
  int r = 0;
  while (r < 8) {
    int w = base + r * 8;
    int v = g[r];
    int m = 63 << sh;
    w[0] = (w[0] & ~m) | (v << sh);
    if (sh > 10) {
      int s2 = 16 - sh;
      m = 63 >>> s2;
      w[1] = (w[1] & ~m) | (v >>> s2);
    }
    r++;
  }
}

void scroll() {
  int i = 0;
  while (i < 576) { SCREEN[i] = SCREEN[i + 64]; i++; }
  while (i < 640) { SCREEN[i] = 0; i++; }
}

void locate(int col, int row) { cx = col; cy = row; }

void putc(int c) {
  if (c == 10) { cx = 0; cy++; }
  else if (c == 8) { if (cx > 0) { cx--; drawchar(32, cx, cy); } }
  else if (c >= 32 && c < 127) {
    if (cx >= 21) { cx = 0; cy++; }
    if (cy >= 10) { scroll(); cy = 9; }
    drawchar(c, cx, cy);
    cx++;
  }
  if (cy >= 10) { scroll(); cy = 9; }
}

void print(int s) { while (*s) { putc(*s); s++; } }
void puts(int s) { print(s); putc(10); }

void putint(int n) {
  int buf[6];
  int i = 0;
  int neg = n < 0;
  if (n == 0) { putc('0'); return; }
  while (n != 0) {
    int d = n % 10;
    if (d < 0) d = -d;
    buf[i] = '0' + d;
    i++;
    n = n / 10;
  }
  if (neg) putc('-');
  while (i > 0) { i--; putc(buf[i]); }
}

void puthex(int n) {
  int i = 12;
  while (i >= 0) {
    int d = (n >>> i) & 15;
    if (d < 10) putc('0' + d); else putc('A' + d - 10);
    i -= 4;
  }
}

// ---------- клавиатура (коды как в nand2tetris: Enter=128, Backspace=129,
// ---------- влево/вверх/вправо/вниз = 130..133) ----------
int getkey() { return *KBD; }

int waitkey() {
  int k;
  while ((k = *KBD) == 0) { }
  while (*KBD != 0) { }
  return k;
}

int getline(int buf, int max) {
  int n = 0;
  while (1) {
    int k = waitkey();
    if (k == 128 || k == 10) { putc(10); break; }
    if (k == 129) { if (n > 0) { n--; putc(8); } }
    else if (k >= 32 && k < 127 && n < max - 1) { buf[n] = k; n++; putc(k); }
  }
  buf[n] = 0;
  return n;
}

int atoi(int s) {
  int n = 0;
  int neg = 0;
  if (*s == '-') { neg = 1; s++; }
  while (*s >= '0' && *s <= '9') { n = n * 10 + (*s - '0'); s++; }
  return neg ? -n : n;
}
"""


def parse_source(src):
    return Parser(tokenize(src)).program()


def compile_sc(user_src):
    lib_items = parse_source(LIB_SRC)
    user_items = parse_source(user_src)
    consts = dict(PREDEF)
    funcs, gvars, owner = {}, {}, {}
    for tag, items in (('lib', lib_items), ('user', user_items)):
        for it in items:
            kind, name, line = it[0], it[1], it[-1]
            if name in owner:
                if owner[name] == tag or name in PREDEF and tag == 'user' and False:
                    raise CompileError("'%s' уже определено" % name, line)
                funcs.pop(name, None); gvars.pop(name, None); consts.pop(name, None)
            elif name in consts and tag == 'user':
                raise CompileError("'%s' — встроенная константа" % name, line)
            owner[name] = tag
            if kind == 'const':
                try:
                    consts[name] = const_eval(it[2], consts)
                except NotConst:
                    raise CompileError('const требует константное выражение', line)
            elif kind == 'func':
                funcs[name] = it
            else:
                gvars[name] = it
    return Compiler(funcs, gvars, consts).run()


# ============================================================================
#  ПРИМЕРЫ ПРОГРАММ
# ============================================================================
EXAMPLES = {}

EXAMPLES['Привет, мир'] = r"""// Текст, числа, ввод с клавиатуры.
// Чтобы вводить: кликни по экрану, раскладка EN.
void main() {
  cls();
  puts("SC-16 stack computer");
  puts("Hello, world!");
  print("2 + 2 = ");
  putint(2 + 2);
  putc(10);
  print("Press a key: ");
  int k = waitkey();
  putc(10);
  print("code = ");
  putint(k);
  putc(10);
}
"""

EXAMPLES['Простые числа'] = r"""// Решето Эратосфена
int sieve[150];

void main() {
  int i; int j; int count = 0;
  cls();
  for (i = 2; i < 150; i++) sieve[i] = 1;
  for (i = 2; i < 150; i++) {
    if (sieve[i]) {
      putint(i); putc(' ');
      count++;
      for (j = i + i; j < 150; j += i) sieve[j] = 0;
    }
  }
  putc(10);
  print("total: "); putint(count);
}
"""

EXAMPLES['Рекурсия'] = r"""// Рекурсивные функции: у каждого вызова свой кадр локальных переменных
int fact(int n) { if (n <= 1) return 1; return n * fact(n - 1); }
int fib(int n)  { if (n < 2) return n; return fib(n - 1) + fib(n - 2); }

void main() {
  int i;
  cls();
  for (i = 1; i <= 7; i++) {
    putint(i); print("! = "); putint(fact(i)); putc(10);
  }
  for (i = 0; i <= 14; i++) { putint(fib(i)); putc(' '); }
}
"""

EXAMPLES['Рисование (стрелки)'] = r"""// Стрелки двигают точку, C — очистить экран. Кликни по экрану!
void main() {
  int x = 64; int y = 40; int k;
  cls();
  line(0, 0, 127, 0, 1); line(127, 0, 127, 79, 1);
  line(127, 79, 0, 79, 1); line(0, 79, 0, 0, 1);
  while (1) {
    pset(x, y, 1);
    k = *KBD;
    if (k == 130 && x > 0)   x--;
    if (k == 132 && x < 127) x++;
    if (k == 131 && y > 0)   y--;
    if (k == 133 && y < 79)  y++;
    if (k == 'c') cls();
    delay(15);
  }
}
"""

EXAMPLES['Калькулятор'] = r"""// Ввод строк и чисел. Кликни по экрану, раскладка EN, Enter — ввод.
int buf[16];

void main() {
  cls();
  puts("a + b calculator");
  while (1) {
    print("a? "); getline(buf, 16);
    int a = atoi(buf);
    print("b? "); getline(buf, 16);
    int b = atoi(buf);
    print("a+b = "); putint(a + b); putc(10);
  }
}
"""

EXAMPLES['Лампочки (LEDS)'] = r"""// Двоичный счётчик на 16 лампочках (порт LEDS)
void main() {
  int i = 0;
  while (1) {
    *LEDS = i;
    i++;
    delay(60);
  }
}
"""

EXAMPLES['Brainf*ck (полнота по Тьюрингу)'] = r"""// Интерпретатор Brainf*ck на SC, работающий на SC-16.
// BF полон по Тьюрингу => машина тоже (в пределах её памяти).
int prog[] = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++.";
int tape[200];

void run() {
  int ip = 0; int p = 0;
  while (prog[ip] != 0) {
    int c = prog[ip];
    if (c == '>') p++;
    else if (c == '<') p--;
    else if (c == '+') tape[p]++;
    else if (c == '-') tape[p]--;
    else if (c == '.') putc(tape[p]);
    else if (c == ',') tape[p] = waitkey();
    else if (c == '[') {
      if (tape[p] == 0) {
        int d = 1;
        while (d > 0) { ip++; if (prog[ip] == '[') d++; if (prog[ip] == ']') d--; }
      }
    } else if (c == ']') {
      if (tape[p] != 0) {
        int d = 1;
        while (d > 0) { ip--; if (prog[ip] == ']') d++; if (prog[ip] == '[') d--; }
      }
    }
    ip++;
  }
}

void main() { cls(); run(); }
"""

HELP = """\
SC-16 — СПРАВКА

ПАМЯТЬ (слова по 16 бит, адрес 15 бит)
  0 .. 16383        ОЗУ: код, данные, кадры функций (растут вниз от 16383)
  16384 .. 17023    ЭКРАН 128x80, 8 слов на строку, бит0 = левый пиксель, 1 = чёрный
  24576  KBD        код нажатой клавиши (0 — нет); Enter=128, Backspace=129,
                    стрелки: влево 130, вверх 131, вправо 132, вниз 133
  24577  CLOCK      миллисекунды (16 бит)       24578  RND   случайное слово
  24579  LEDS       16 лампочек (запись)
  24832 ..          ПЗУ шрифта: 8 слов на символ ASCII 32..126

КОМАНДЫ (слово с битом 15 = LIT n, число 0..32767; остальные — без операндов)
  стек:    DUP DROP SWAP OVER ROT                      ( a b c -- b c a )
  АЛУ:     ADD SUB MUL DIV MOD AND OR XOR NOT NEG SHL SHR SAR
  сравн.:  EQ NE LT LE GT GE LNOT                      даёт 1 или 0 (знаковые)
  память:  LOAD ( addr -- v )   STORE ( v addr -- )
  переход: JMP ( addr -- )   JZ / JNZ ( flag addr -- )   CALL ( addr -- )   RET
  стек возвратов: TOR  FROMR  RFETCH
  кадры:   FPGET FPSET  ENTER(n: FP-=n)  LEAVE(n: FP+=n)
           LGET ( i -- mem[FP+i] )  LSET ( v i -- )  LADDR ( i -- FP+i )
  прочее:  NOP HALT

ЯЗЫК SC
  Только int (16 бит со знаком); указатель — тоже int. Все функции возвращают int.
  int x = 5, a[10], s[] = "text", t[] = {1,2,3};   // глобальные (локальные массивы — без инициализации)
  const N = 10;                                    // константа
  int f(int a, int b) { ... return a + b; }        // рекурсия разрешена
  if / else / while / do-while / for / break / continue / return
  Операции: + - * / % & | ^ ~ ! << >> (арифм.) >>> (логич.) == != < <= > >= && || ?:
            = += -= *= /= %= &= |= ^= <<= >>=   ++ --   *p  &x  a[i]
  Строка "abc" = адрес массива символов с нулём на конце.
  Встроенные константы: SCREEN KBD CLOCK RND LEDS FONT SW SH.
  Библиотека: cls locate putc print puts putint puthex pset pget line rect
              getkey waitkey getline atoi delay rand abs min max
"""


# ============================================================================
#  ИНТЕРФЕЙС
# ============================================================================
_WSTR = {}


def wstr(w):
    s = _WSTR.get(w)
    if s is None:
        s = ' '.join('#000' if (w >> b) & 1 else '#fff' for b in range(16))
        _WSTR[w] = s
    return s


KEYMAP = {'Return': 128, 'KP_Enter': 128, 'BackSpace': 129, 'Left': 130, 'Up': 131,
          'Right': 132, 'Down': 133, 'Home': 134, 'End': 135, 'Prior': 136, 'Next': 137,
          'Insert': 138, 'Delete': 139, 'Escape': 140}


class App:
    def __init__(self, root):
        self.root = root
        root.title('SC-16 — стековый компьютер')
        self.cpu = CPU()
        self.prog = None
        self.func_addrs, self.func_names = [], []
        self.running = False
        self.pressed = {}
        self.last_heavy = 0.0
        self.last_stacks = None
        self.build_ui()
        self.load_example('Привет, мир')
        self.compile_and_load(False)
        self.tick()

    # ---- построение окна --------------------------------------------------
    def build_ui(self):
        root = self.root
        mono = ('TkFixedFont', 10)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(0, weight=1)
        left = ttk.Frame(root, padding=6)
        left.grid(row=0, column=0, sticky='ns')
        right = ttk.Frame(root, padding=6)
        right.grid(row=0, column=1, sticky='nsew')
        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        # экран
        self.canvas = tk.Canvas(left, width=SCR_W * ZOOM, height=SCR_H * ZOOM, bg='white',
                                highlightthickness=2, highlightbackground='#888', takefocus=1)
        self.canvas.pack()
        self.img = tk.PhotoImage(width=SCR_W, height=SCR_H)
        self.img.put('#fff', to=(0, 0, SCR_W, SCR_H))
        self.big = self.img.zoom(ZOOM, ZOOM)
        self.img_id = self.canvas.create_image(0, 0, image=self.big, anchor='nw')
        self.canvas.bind('<KeyPress>', self.on_key_down)
        self.canvas.bind('<KeyRelease>', self.on_key_up)
        self.canvas.bind('<Button-1>', lambda e: self.canvas.focus_set())
        ttk.Label(left, text='Клавиатура: кликни по экрану (раскладка EN)', foreground='#666').pack(anchor='w')

        # лампочки
        self.led_canvas = tk.Canvas(left, width=SCR_W * ZOOM, height=26, highlightthickness=0)
        self.led_canvas.pack(pady=(4, 0))
        step = SCR_W * ZOOM / 16
        self.leds = [self.led_canvas.create_oval(i * step + 6, 3, i * step + step - 6, 21,
                                                 fill='#400', outline='#222') for i in range(16)]
        self.led_prev = -1
        ttk.Label(left, text='LEDS @24579 (слева бит 15 … справа бит 0)', foreground='#666').pack(anchor='w')

        # управление
        bar = ttk.Frame(left)
        bar.pack(fill='x', pady=4)
        self.run_btn = ttk.Button(bar, text='▶ Запуск', command=self.toggle_run)
        self.run_btn.pack(side='left')
        ttk.Button(bar, text='Шаг', command=self.step).pack(side='left', padx=3)
        ttk.Button(bar, text='Сброс', command=self.reset).pack(side='left')
        self.speed = tk.Scale(bar, from_=0, to=100, orient='horizontal', showvalue=False, length=130,
                              command=lambda v: self.speed_lbl.config(text='%d инстр/тик' % self.batch()))
        self.speed.set(70)
        self.speed.pack(side='left', padx=6)
        self.speed_lbl = ttk.Label(bar, text='')
        self.speed_lbl.pack(side='left')
        self.speed_lbl.config(text='%d инстр/тик' % self.batch())

        # регистры и стеки
        self.regs_var = tk.StringVar()
        tk.Label(left, textvariable=self.regs_var, font=mono, justify='left', anchor='w',
                 relief='sunken', bd=1).pack(fill='x')
        st = ttk.Frame(left)
        st.pack(fill='both', expand=True, pady=4)
        for i, title in enumerate(('Стек данных (вершина сверху)', 'Стек возвратов')):
            f = ttk.Frame(st)
            f.grid(row=0, column=i, sticky='nsew', padx=2)
            st.columnconfigure(i, weight=1)
            ttk.Label(f, text=title).pack(anchor='w')
            t = tk.Text(f, width=24, height=10, font=mono, state='disabled')
            t.pack(fill='both', expand=True)
            setattr(self, 'ds_text' if i == 0 else 'rs_text', t)

        # правая часть: вкладки
        self.nb = ttk.Notebook(right)
        self.nb.grid(row=0, column=0, sticky='nsew')
        # --- код
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text='Код SC')
        tb = ttk.Frame(tab)
        tb.pack(fill='x', pady=2)
        self.ex_var = tk.StringVar()
        cb = ttk.Combobox(tb, textvariable=self.ex_var, values=list(EXAMPLES), state='readonly', width=34)
        cb.pack(side='left')
        cb.bind('<<ComboboxSelected>>', lambda e: (self.load_example(self.ex_var.get()), self.compile_and_load(False)))
        ttk.Button(tb, text='Компилировать', command=lambda: self.compile_and_load(False)).pack(side='left', padx=4)
        ttk.Button(tb, text='Компилировать и запустить (F5)',
                   command=lambda: self.compile_and_load(True)).pack(side='left')
        root.bind('<F5>', lambda e: self.compile_and_load(True))
        ef = ttk.Frame(tab)
        ef.pack(fill='both', expand=True)
        self.editor = tk.Text(ef, font=mono, undo=True, wrap='none', width=70, height=30)
        sy = ttk.Scrollbar(ef, command=self.editor.yview)
        self.editor.config(yscrollcommand=sy.set)
        sy.pack(side='right', fill='y')
        self.editor.pack(side='left', fill='both', expand=True)
        self.editor.tag_config('err', background='#ffb0b0')
        # --- дизассемблер
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text='Дизассемблер')
        self.dis_text = tk.Text(tab, font=mono, state='disabled', width=70, wrap='none')
        self.dis_text.pack(fill='both', expand=True)
        self.dis_text.tag_config('pc', background='#fff2a8')
        # --- память
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text='Память')
        mb = ttk.Frame(tab)
        mb.pack(fill='x', pady=2)
        ttk.Label(mb, text='Адрес:').pack(side='left')
        self.mem_addr = tk.StringVar(value='0')
        e = ttk.Entry(mb, textvariable=self.mem_addr, width=9)
        e.pack(side='left', padx=3)
        e.bind('<Return>', lambda ev: self.refresh_mem())
        for label, fn in (('0', lambda: '0'), ('Данные', lambda: str(self.prog.code_len if self.prog else 0)),
                          ('FP', lambda: str(self.cpu.fp)), ('Экран', lambda: str(SCREEN)),
                          ('I/O', lambda: str(KBD)), ('Шрифт', lambda: str(FONT))):
            ttk.Button(mb, text=label, width=7,
                       command=lambda f=fn: (self.mem_addr.set(f()), self.refresh_mem())).pack(side='left', padx=1)
        self.mem_text = tk.Text(tab, font=mono, state='disabled', width=70, wrap='none')
        self.mem_text.pack(fill='both', expand=True)
        # --- справка
        tab = ttk.Frame(self.nb)
        self.nb.add(tab, text='Справка')
        ht = tk.Text(tab, font=mono, width=70, wrap='none')
        ht.insert('1.0', HELP)
        ht.config(state='disabled')
        ht.pack(fill='both', expand=True)
        # статус
        self.status = tk.Label(right, text='', anchor='w', justify='left', relief='sunken', bd=1)
        self.status.grid(row=1, column=0, sticky='ew', pady=(4, 0))

    def batch(self):
        return max(1, int(2 ** (self.speed.get() / 6.0)))

    # ---- работа с исходником ---------------------------------------------
    def load_example(self, name):
        self.ex_var.set(name)
        self.editor.delete('1.0', 'end')
        self.editor.insert('1.0', EXAMPLES[name])

    def set_status(self, text, bad=False):
        self.status.config(text=text, fg='#b00000' if bad else '#006000')

    def compile_and_load(self, run):
        self.editor.tag_remove('err', '1.0', 'end')
        try:
            prog = compile_sc(self.editor.get('1.0', 'end'))
        except CompileError as e:
            where = ' (строка %d)' % e.line if e.line else ''
            self.set_status('Ошибка компиляции: ' + e.msg + where, True)
            if e.line:
                self.editor.tag_add('err', '%d.0' % e.line, '%d.end' % e.line)
                self.editor.see('%d.0' % e.line)
            return
        self.prog = prog
        self.func_addrs = [a for a, n in prog.funcs]
        self.func_names = [n for a, n in prog.funcs]
        self.running = False
        self.cpu.load(prog.image)
        self.set_status('Скомпилировано: %d слов кода + %d слов данных' %
                        (prog.code_len, len(prog.image) - prog.code_len))
        self.refresh_all()
        if run:
            self.toggle_run()

    def reset(self):
        if self.prog:
            self.running = False
            self.cpu.load(self.prog.image)
            self.set_status('Сброс')
            self.refresh_all()
        self.run_btn.config(text='▶ Запуск')

    def toggle_run(self):
        if self.running:
            self.running = False
            self.run_btn.config(text='▶ Запуск')
            return
        if not self.prog:
            return
        if self.cpu.halted:
            self.cpu.load(self.prog.image)
        self.running = True
        self.run_btn.config(text='⏸ Пауза')
        self.set_status('Работает…')
        self.canvas.focus_set()

    def step(self):
        if not self.prog:
            return
        self.running = False
        self.run_btn.config(text='▶ Запуск')
        if not self.cpu.halted:
            self.cpu.run(1)
        self.after_halt_check()
        self.refresh_all()

    def after_halt_check(self):
        c = self.cpu
        if c.halted:
            if c.fault:
                self.set_status('ОШИБКА выполнения: %s  (PC=%d)' % (c.fault, c.pc), True)
            else:
                self.set_status('Программа завершена (HALT), выполнено команд: %d' % c.steps)

    # ---- клавиатура ---------------------------------------------------------
    def on_key_down(self, ev):
        code = KEYMAP.get(ev.keysym, 0)
        if not code and len(ev.char) == 1 and 32 <= ord(ev.char) < 127:
            code = ord(ev.char)
        if code:
            self.pressed[ev.keysym] = code
            self.cpu.key = code
        return 'break'

    def on_key_up(self, ev):
        code = self.pressed.pop(ev.keysym, None)
        if code is not None:
            self.root.after(40, lambda: self.release(code))
        return 'break'

    def release(self, code):
        if self.cpu.key == code and code not in self.pressed.values():
            self.cpu.key = 0

    # ---- обновление картинки ---------------------------------------------
    def tick(self):
        if self.running:
            self.cpu.run(self.batch())
            if self.cpu.halted:
                self.running = False
                self.run_btn.config(text='▶ Запуск')
                self.after_halt_check()
        self.redraw_screen()
        self.redraw_leds()
        self.refresh_light()
        now = time.time()
        if not self.running or now - self.last_heavy > 0.25:
            self.last_heavy = now
            self.refresh_heavy()
        self.root.after(15, self.tick)

    def redraw_screen(self):
        c = self.cpu
        if c.full_redraw:
            rows = range(SCR_H)
            c.full_redraw = False
        elif c.dirty:
            rows = sorted({(a - SCREEN) // WPR for a in c.dirty})
        else:
            return
        c.dirty.clear()
        mem = c.mem
        for y in rows:
            base = SCREEN + y * WPR
            self.img.put('{' + ' '.join(wstr(mem[base + i]) for i in range(WPR)) + '}', to=(0, y))
        self.big = self.img.zoom(ZOOM, ZOOM)
        self.canvas.itemconfigure(self.img_id, image=self.big)

    def redraw_leds(self):
        v = self.cpu.mem[LEDS]
        if v != self.led_prev:
            self.led_prev = v
            for i, item in enumerate(self.leds):
                self.led_canvas.itemconfigure(item, fill='#ff3030' if (v >> (15 - i)) & 1 else '#400')

    def where(self, a):
        i = bisect.bisect_right(self.func_addrs, a) - 1
        if i < 0:
            return ''
        return '%s+%d' % (self.func_names[i], a - self.func_addrs[i])

    @staticmethod
    def set_text(widget, text):
        widget.config(state='normal')
        widget.delete('1.0', 'end')
        widget.insert('1.0', text)
        widget.config(state='disabled')

    def refresh_light(self):
        c = self.cpu
        self.regs_var.set(' PC %5d  0x%04X    FP %5d  0x%04X\n DS глубина %-4d RS глубина %-4d\n выполнено команд: %d'
                          % (c.pc, c.pc, c.fp, c.fp, len(c.ds), len(c.rs), c.steps))
        ds = tuple(c.ds[-12:])
        rs = tuple(c.rs[-12:])
        if (ds, rs) != self.last_stacks:
            self.last_stacks = (ds, rs)
            self.set_text(self.ds_text, '\n'.join('%04X %7d' % (v, s16(v)) for v in reversed(ds)))
            self.set_text(self.rs_text, '\n'.join('%5d %s' % (v, self.where(v)) for v in reversed(rs)))

    def refresh_heavy(self):
        tab = self.nb.index(self.nb.select())
        if tab == 1:
            self.refresh_disasm()
        elif tab == 2:
            self.refresh_mem()

    def refresh_all(self):
        self.last_stacks = None
        self.refresh_light()
        self.redraw_screen()
        self.refresh_disasm()
        self.refresh_mem()

    def refresh_disasm(self):
        c, p = self.cpu, self.prog
        syms = p.syms if p else {}
        code_len = p.code_len if p else 0
        start = max(0, c.pc - 10)
        out, pcline = [], 1
        for a in range(start, min(start + 44, RAM_END)):
            if a in syms:
                out.append('%s:' % syms[a])
            w = c.mem[a]
            txt = dis(w, syms) if a < code_len else '.word %d   (0x%04X)' % (w, w)
            if a == c.pc:
                pcline = len(out) + 1
            out.append('%s %5d  %04X  %s' % ('►' if a == c.pc else ' ', a, w, txt))
        self.set_text(self.dis_text, '\n'.join(out))
        self.dis_text.tag_add('pc', '%d.0' % pcline, '%d.end' % pcline)

    def refresh_mem(self):
        try:
            a0 = int(self.mem_addr.get().strip(), 0)
        except ValueError:
            a0 = 0
        a0 = max(0, min(a0, MEM_SIZE - 8)) & ~7
        rd = self.cpu.mem
        lines = []
        for a in range(a0, min(a0 + 8 * 26, MEM_SIZE), 8):
            ws = []
            for i in range(8):
                x = a + i
                ws.append(FONT_ROM[x - FONT] if FONT <= x < FONT + len(FONT_ROM) else rd[x])
            asc = ''.join(chr(w) if 32 <= w < 127 else '.' for w in ws)
            lines.append('%5d  %04X: %s  |%s|' % (a, a, ' '.join('%04X' % w for w in ws), asc))
        self.set_text(self.mem_text, '\n'.join(lines))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == '__main__':
    main()