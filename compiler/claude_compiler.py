#!/usr/bin/env python3
"""
jackc.py - компилятор языка Jack в VM-код (nand2tetris, проект 11).

Использование:
    python3 jackc.py Prog.jack       # создаст Prog.vm рядом с исходником
    python3 jackc.py ./MyProgram/    # скомпилирует все *.jack в папке

Структура файла (как в книге):
    tokenize()          лексер: текст -> список токенов
    SymbolTable         таблицы символов (уровень класса и уровень подпрограммы)
    VMWriter            запись VM-команд
    CompilationEngine   рекурсивный спуск: разбор и генерация кода за один проход

Условия if/while генерируются без `not`:
    условие / if-goto TRUE / goto FALSE_ИЛИ_END / label TRUE ...
"""

import re
import sys
from collections import namedtuple
from pathlib import Path

KEYWORDS = {
    "class", "constructor", "function", "method", "field", "static", "var",
    "int", "char", "boolean", "void", "true", "false", "null", "this",
    "let", "do", "if", "else", "while", "return",
}

# kind: keyword | symbol | int | string | ident | eof
Token = namedtuple("Token", "kind value line")


class CompileError(Exception):
    pass


# --------------------------------------------------------------------------
# 1. Лексер
# --------------------------------------------------------------------------

# Порядок альтернатив важен: комментарии должны проверяться раньше символа '/'.
TOKEN_RE = re.compile(
    r"""
      (?P<ws>\s+)
    | (?P<line_comment>//[^\n]*)
    | (?P<block_comment>/\*.*?\*/)
    | (?P<bad_comment>/\*)
    | (?P<int>\d+)
    | (?P<str>"[^"\n]*")
    | (?P<id>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<sym>[{}()\[\].,;+\-*/&|<>=~])
    """,
    re.VERBOSE | re.DOTALL,
)


def tokenize(src):
    tokens = []
    pos, line = 0, 1
    while pos < len(src):
        m = TOKEN_RE.match(src, pos)
        if not m:
            if src[pos] == '"':
                raise CompileError(f"line {line}: unterminated string constant")
            raise CompileError(f"line {line}: unexpected character {src[pos]!r}")
        kind, text = m.lastgroup, m.group()
        if kind == "bad_comment":
            raise CompileError(f"line {line}: unterminated comment")
        elif kind == "int":
            if int(text) > 32767:
                raise CompileError(f"line {line}: integer {text} is larger than 32767")
            tokens.append(Token("int", int(text), line))
        elif kind == "str":
            tokens.append(Token("string", text[1:-1], line))
        elif kind == "id":
            tokens.append(Token("keyword" if text in KEYWORDS else "ident", text, line))
        elif kind == "sym":
            tokens.append(Token("symbol", text, line))
        line += text.count("\n")
        pos = m.end()
    tokens.append(Token("eof", "", line))
    return tokens


# --------------------------------------------------------------------------
# 2. Таблица символов
# --------------------------------------------------------------------------

# kind в таблице -> сегмент VM
SEGMENT = {"static": "static", "field": "this", "arg": "argument", "var": "local"}


class SymbolTable:
    """Две области видимости: класс (static, field) и подпрограмма (arg, var).
    Индексы считаются отдельно для каждого kind."""

    def __init__(self):
        self.class_scope = {}   # name -> (type, kind, index)
        self.sub_scope = {}
        self.counts = {"static": 0, "field": 0, "arg": 0, "var": 0}

    def start_subroutine(self):
        self.sub_scope = {}
        self.counts["arg"] = 0
        self.counts["var"] = 0

    def _scope_for(self, kind):
        return self.class_scope if kind in ("static", "field") else self.sub_scope

    def defined_here(self, name, kind):
        return name in self._scope_for(kind)

    def define(self, name, type_, kind):
        self._scope_for(kind)[name] = (type_, kind, self.counts[kind])
        self.counts[kind] += 1

    def count(self, kind):
        return self.counts[kind]

    def lookup(self, name):
        # локальная область перекрывает область класса
        return self.sub_scope.get(name) or self.class_scope.get(name)


# --------------------------------------------------------------------------
# 3. Запись VM-кода
# --------------------------------------------------------------------------

class VMWriter:
    def __init__(self):
        self.lines = []

    def push(self, segment, index):
        self.lines.append(f"push {segment} {index}")

    def pop(self, segment, index):
        self.lines.append(f"pop {segment} {index}")

    def arithmetic(self, command):
        self.lines.append(command)

    def label(self, name):
        self.lines.append(f"label {name}")

    def goto(self, name):
        self.lines.append(f"goto {name}")

    def if_goto(self, name):
        self.lines.append(f"if-goto {name}")

    def call(self, name, n_args):
        self.lines.append(f"call {name} {n_args}")

    def function(self, name, n_locals):
        self.lines.append(f"function {name} {n_locals}")

    def ret(self):
        self.lines.append("return")

    def text(self):
        return "\n".join(self.lines) + "\n"


# --------------------------------------------------------------------------
# 4. Разбор и генерация кода
# --------------------------------------------------------------------------

def describe(tok):
    return "end of file" if tok.kind == "eof" else repr(tok.value)


class CompilationEngine:
    # операторы, которым соответствует одна VM-команда
    BINARY_OPS = {"+": "add", "-": "sub", "&": "and", "|": "or",
                  "<": "lt", ">": "gt", "=": "eq"}
    # * и / в VM нет: это вызовы функций операционной системы
    OS_OPS = {"*": "Math.multiply", "/": "Math.divide"}

    def __init__(self, tokens):
        self.toks = tokens
        self.i = 0
        self.vm = VMWriter()
        self.st = SymbolTable()
        self.class_name = ""
        self.sub_kind = ""      # constructor | function | method
        self.if_n = 0           # счётчики меток (сбрасываются в каждой подпрограмме)
        self.while_n = 0

    # ---- работа с потоком токенов ----

    def peek(self, k=0):
        j = min(self.i + k, len(self.toks) - 1)   # последний токен всегда eof
        return self.toks[j]

    def advance(self):
        tok = self.peek()
        if tok.kind != "eof":
            self.i += 1
        return tok

    def error(self, msg, tok=None):
        tok = tok or self.peek()
        raise CompileError(f"line {tok.line}: {msg}")

    def at(self, *values):
        t = self.peek()
        return t.kind in ("keyword", "symbol") and t.value in values

    def at_symbol(self, k, *values):
        t = self.peek(k)
        return t.kind == "symbol" and t.value in values

    def eat(self, *values):
        if self.at(*values):
            return self.advance()
        expected = " or ".join(repr(v) for v in values)
        self.error(f"expected {expected}, found {describe(self.peek())}")

    def ident(self):
        t = self.peek()
        if t.kind != "ident":
            self.error(f"expected identifier, found {describe(t)}")
        return self.advance().value

    def type_(self):
        t = self.peek()
        if t.kind == "keyword" and t.value in ("int", "char", "boolean"):
            return self.advance().value
        if t.kind == "ident":
            return self.advance().value
        self.error(f"expected a type, found {describe(t)}")

    def declare(self, name, type_, kind, tok):
        if self.st.defined_here(name, kind):
            self.error(f"'{name}' is already declared", tok)
        self.st.define(name, type_, kind)

    def lookup(self, name, tok):
        sym = self.st.lookup(name)
        if sym is None:
            self.error(f"undeclared variable '{name}'", tok)
        type_, kind, index = sym
        return type_, SEGMENT[kind], index

    # ---- структура класса ----

    def compile_class(self):
        self.eat("class")
        self.class_name = self.ident()
        self.eat("{")
        while self.at("static", "field"):
            self.class_var_dec()
        while self.at("constructor", "function", "method"):
            self.subroutine()
        self.eat("}")
        if self.peek().kind != "eof":
            self.error("unexpected tokens after the end of the class")
        return self.vm.text()

    def class_var_dec(self):
        kind = self.advance().value              # static | field
        type_ = self.type_()
        while True:
            tok = self.peek()
            self.declare(self.ident(), type_, kind, tok)
            if not self.at(","):
                break
            self.advance()
        self.eat(";")

    def subroutine(self):
        self.sub_kind = self.advance().value     # constructor | function | method
        self.st.start_subroutine()
        self.if_n = self.while_n = 0

        if self.at("void"):
            self.advance()
        else:
            self.type_()
        name = self.ident()

        # у метода первый аргумент (argument 0) - неявный this
        if self.sub_kind == "method":
            self.st.define("this", self.class_name, "arg")

        self.eat("(")
        self.parameter_list()
        self.eat(")")

        self.eat("{")
        while self.at("var"):
            self.var_dec()

        # число локальных известно только после всех var, поэтому строка
        # `function` пишется здесь, а не раньше
        self.vm.function(f"{self.class_name}.{name}", self.st.count("var"))

        if self.sub_kind == "constructor":
            # размер объекта = число полей (static не считаются)
            self.vm.push("constant", self.st.count("field"))
            self.vm.call("Memory.alloc", 1)
            self.vm.pop("pointer", 0)            # THIS = адрес нового объекта
        elif self.sub_kind == "method":
            self.vm.push("argument", 0)
            self.vm.pop("pointer", 0)            # THIS = объект, на котором вызвали метод

        self.statements()
        self.eat("}")

    def parameter_list(self):
        if self.at(")"):
            return
        while True:
            type_ = self.type_()
            tok = self.peek()
            self.declare(self.ident(), type_, "arg", tok)
            if not self.at(","):
                break
            self.advance()

    def var_dec(self):
        self.eat("var")
        type_ = self.type_()
        while True:
            tok = self.peek()
            self.declare(self.ident(), type_, "var", tok)
            if not self.at(","):
                break
            self.advance()
        self.eat(";")

    # ---- операторы ----

    def statements(self):
        while True:
            if self.at("let"):
                self.let_statement()
            elif self.at("if"):
                self.if_statement()
            elif self.at("while"):
                self.while_statement()
            elif self.at("do"):
                self.do_statement()
            elif self.at("return"):
                self.return_statement()
            else:
                return

    def let_statement(self):
        self.eat("let")
        tok = self.peek()
        name = self.ident()
        _, segment, index = self.lookup(name, tok)

        if self.at("["):
            # let a[i] = expr;
            self.advance()
            self.vm.push(segment, index)         # база массива
            self.expression()                    # индекс
            self.eat("]")
            self.vm.arithmetic("add")            # адрес элемента ждёт на стеке
            self.eat("=")
            self.expression()                    # правая часть может сама читать массив
            self.eat(";")
            self.vm.pop("temp", 0)               # прячем значение
            self.vm.pop("pointer", 1)            # THAT = адрес элемента
            self.vm.push("temp", 0)
            self.vm.pop("that", 0)
        else:
            self.eat("=")
            self.expression()
            self.eat(";")
            self.vm.pop(segment, index)

    def block_has_else(self):
        """Смотрим вперёд: за блоком { ... } идёт `else`? Нужно, чтобы выбрать
        схему меток до генерации тела."""
        j, depth = self.i, 0
        while j < len(self.toks):
            t = self.toks[j]
            if t.kind == "symbol" and t.value == "{":
                depth += 1
            elif t.kind == "symbol" and t.value == "}":
                depth -= 1
                if depth == 0:
                    nxt = self.toks[min(j + 1, len(self.toks) - 1)]
                    return nxt.kind == "keyword" and nxt.value == "else"
            j += 1
        return False

    def if_statement(self):
        n = self.if_n                            # номер берём до тела: вложенные if
        self.if_n += 1                           # получат следующие номера
        self.eat("if")
        self.eat("(")
        self.expression()
        self.eat(")")
        has_else = self.block_has_else()

        self.vm.if_goto(f"IF_TRUE{n}")
        self.vm.goto(f"IF_FALSE{n}" if has_else else f"IF_END{n}")
        self.vm.label(f"IF_TRUE{n}")
        self.eat("{")
        self.statements()
        self.eat("}")
        if has_else:
            self.vm.goto(f"IF_END{n}")
            self.vm.label(f"IF_FALSE{n}")
            self.eat("else")
            self.eat("{")
            self.statements()
            self.eat("}")
        self.vm.label(f"IF_END{n}")

    def while_statement(self):
        n = self.while_n
        self.while_n += 1
        self.eat("while")
        self.vm.label(f"WHILE_EXP{n}")
        self.eat("(")
        self.expression()
        self.eat(")")
        self.vm.if_goto(f"WHILE_TRUE{n}")
        self.vm.goto(f"WHILE_END{n}")
        self.vm.label(f"WHILE_TRUE{n}")
        self.eat("{")
        self.statements()
        self.eat("}")
        self.vm.goto(f"WHILE_EXP{n}")            # назад, на повторную проверку
        self.vm.label(f"WHILE_END{n}")

    def do_statement(self):
        self.eat("do")
        self.subroutine_call()
        self.eat(";")
        self.vm.pop("temp", 0)                   # результат вызова выбрасываем

    def return_statement(self):
        self.eat("return")
        if self.at(";"):
            self.vm.push("constant", 0)          # void тоже возвращает значение
        else:
            self.expression()
        self.eat(";")
        self.vm.ret()

    # ---- выражения ----

    def expression(self):
        # приоритетов в Jack нет: всё слева направо
        self.term()
        while self.peek().kind == "symbol" and (
                self.peek().value in self.BINARY_OPS or self.peek().value in self.OS_OPS):
            op = self.advance().value
            self.term()
            if op in self.OS_OPS:
                self.vm.call(self.OS_OPS[op], 2)
            else:
                self.vm.arithmetic(self.BINARY_OPS[op])

    def term(self):
        t = self.peek()

        if t.kind == "int":
            self.advance()
            self.vm.push("constant", t.value)

        elif t.kind == "string":
            self.advance()
            self.vm.push("constant", len(t.value))
            self.vm.call("String.new", 1)
            for ch in t.value:
                if ord(ch) > 127:
                    self.error(f"unsupported character {ch!r} in string constant", t)
                self.vm.push("constant", ord(ch))
                self.vm.call("String.appendChar", 2)   # возвращает ту же строку

        elif t.kind == "keyword" and t.value in ("true", "false", "null", "this"):
            self.advance()
            if t.value == "true":
                self.vm.push("constant", 0)
                self.vm.arithmetic("not")              # true = -1 (все биты единицы)
            elif t.value in ("false", "null"):
                self.vm.push("constant", 0)
            else:
                if self.sub_kind == "function":
                    self.error("'this' can't be used inside a function", t)
                self.vm.push("pointer", 0)

        elif t.kind == "ident":
            if self.at_symbol(1, "["):
                # чтение a[i]
                self.advance()
                _, segment, index = self.lookup(t.value, t)
                self.advance()                          # [
                self.vm.push(segment, index)
                self.expression()
                self.eat("]")
                self.vm.arithmetic("add")
                self.vm.pop("pointer", 1)
                self.vm.push("that", 0)
            elif self.at_symbol(1, "(", "."):
                self.subroutine_call()
            else:
                self.advance()
                _, segment, index = self.lookup(t.value, t)
                self.vm.push(segment, index)

        elif self.at("("):
            self.advance()
            self.expression()
            self.eat(")")

        elif self.at("-", "~"):
            op = self.advance().value
            self.term()
            self.vm.arithmetic("neg" if op == "-" else "not")

        else:
            self.error(f"expected an expression, found {describe(t)}")

    def subroutine_call(self):
        tok = self.peek()
        first = self.ident()
        n_args = 0

        if self.at("."):
            self.advance()
            name = self.ident()
            sym = self.st.lookup(first)
            if sym is not None:
                # first - переменная: это метод объекта; класс берём из ТИПА
                type_, kind, index = sym
                self.vm.push(SEGMENT[kind], index)
                class_name = type_
                n_args = 1
            else:
                # first - имя класса: function или constructor, объекта нет
                class_name = first
        else:
            # вызов без точки: метод текущего объекта
            if self.sub_kind == "function":
                self.error(f"can't call method '{first}' without an object inside a function", tok)
            name = first
            class_name = self.class_name
            self.vm.push("pointer", 0)
            n_args = 1

        self.eat("(")
        n_args += self.expression_list()
        self.eat(")")
        self.vm.call(f"{class_name}.{name}", n_args)

    def expression_list(self):
        if self.at(")"):
            return 0
        count = 1
        self.expression()
        while self.at(","):
            self.advance()
            self.expression()
            count += 1
        return count


# --------------------------------------------------------------------------
# 5. Запуск
# --------------------------------------------------------------------------

def compile_source(src):
    return CompilationEngine(tokenize(src)).compile_class()


def main(argv):
    if len(argv) != 2:
        print("usage: jackc.py <file.jack | directory>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    files = sorted(path.glob("*.jack")) if path.is_dir() else [path]
    if not files:
        print(f"no .jack files in {path}", file=sys.stderr)
        return 2

    failed = False
    for f in files:
        try:
            out = f.with_suffix(".vm")
            out.write_text(compile_source(f.read_text()))
            print(f"{f} -> {out}")
        except (CompileError, OSError) as e:
            print(f"{f.name}: {e}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))