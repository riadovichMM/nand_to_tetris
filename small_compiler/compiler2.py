import re


JACK_CODE = """
class Simple {
    function int calculate() {
        var int x;

        let x = 2 + 3;
    }
}
"""


class SimpleCompiler:
    def __init__(self, source):
        # Разбиваем исходный код на токены.
        self.tokens = re.findall(
            r"[A-Za-z_]\w*|[0-9]+|[{}()\[\].,;+\-=]",
            source
        )

        self.pos = 0
        self.vm = []
        self.class_name = ""
        self.variables = {}
        self.local_count = 0



    def current(self):
            if self.pos >= len(self.tokens):
                return None
            return self.tokens[self.pos]



    def consume(self, expected=None):
        token = self.current()

        if token is None:
            raise SyntaxError("Неожиданный конец кода")

        if expected is not None and token != expected:
            raise SyntaxError(
                f"Ожидалось {expected!r}, получено {token!r}"
            )

        self.pos += 1
        return token




    def emit(self, *commands):
        self.vm.extend(commands)


    # основные методы

    def compile(self):
        self.consume('class')
        self.class_name = self.consume()

        self.consume('{')

        while self.current() != '}':
            self.compile_function()
        self.consume('}')

        if self.current() is not None:
            raise SyntaxError("Лишний код после класса")

        return "\n".join(self.vm)



    def compile_function(self):
        self.consume('function')
        return_type = self.consume()
        function_name = self.consume()

        self.consume('(')
        self.consume(')')
        self.consume('{')

        self.variables = {}
        self.local_count = 0

        while self.current() == "var":
            self.compile_var()

        self.emit(
            f"function {self.class_name}.{function_name} "
            f"{self.local_count}"
        )


        while self.current() != '}':
            if self.current() == 'let':
                self.compile_let()
            elif self.current() == 'return':
                self.compile_return()
            else:
                raise SyntaxError(
                    f"Неизвестная инструкция: {self.current()}"
                )
        self.consume('}')





    def compile_var(self):
        self.consume("var")
        var_type = self.consume()

        while True:
            name = self.consume()

            self.variables[name] = self.local_count
            self.local_count += 1

            if self.current() != ",":
                break

            self.consume(",")

        self.consume(";")




    def compile_let(self):
        self.consume('let')
        name = self.consume()
        self.consume('=')

        self.compile_expression()
        self.consume(';')

        if name not in self.variables:
            raise SyntaxError(f'Unknown variable name: {name}')

        index = self.variables[name]
        self.emit(f'pop local {index}')





    def compile_expression(self):
        self.compile_term()

        while self.current() in ['+']:
            operator = self.consume()
            self.compile_term()

            if operator == '+':
                self.emit('add')





    def compile_term(self):
        token = self.current()
        print(token)

        if token is None:
            raise SyntaxError("Ожидалось выражение")

        if token.isdigit():
            self.consume()
            self.emit(f"push constant {token}")





def main():
    compiler = SimpleCompiler(JACK_CODE)
    compiler.compile()

    for line in compiler.vm:
        print(line)


main()