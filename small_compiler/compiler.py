import re

JACK_CODE = """
class Simple {
    function int calculate() {
        var int x;

        let x = 2 + 3;
        return x;
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
        self.variables = {}
        self.class_name = ''
        self.local_count = 0

    def current(self):
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def consume(self, expected=None):
        token = self.current()

        if token is None:
            raise SyntaxError('Неожиданный конец кода')
        if expected is not None and token != expected:
            raise SyntaxError(f'Ожидалось {expected}, получено {token}')

        self.pos += 1
        return token

    def emit(self, command):
        self.vm.append(command)

    def compile(self):
        self.consume('class')
        self.class_name = self.consume()

        self.consume('{')

        while self.current() != '}':
            self.compile_function()
        self.consume('}')

        if self.current() is not None:
            raise SyntaxError('Лишний код после класса')
        
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

        # локальные переменные
        while self.current() == 'var':
            self.compile_var()

        self.emit(f'function {self.class_name}.{function_name} {self.local_count}')

        # инструкции функции
        while self.current() != '}':
            if self.current() == 'let':
                self.compile_let()
            elif self.current() == 'return':
                self.compile_return()
            else:
                raise SyntaxError(
                    'Неизвестная инструкция'
                )
        self.consume('}')

    def compile_var(self):
        self.consume('var')
        var_type = self.consume()

        while True:
            name = self.consume()
            self.variables[name] = self.local_count
            self.local_count += 1

            if self.current != ',':
                break

            self.consume(',')
        self.consume(';')

    def compile_let(self):
        self.consume('let')
        name = self.consume()
        self.consume('=')

        self.compile_expression()
        self.consume(';')

        if name not in self.variables:
            raise SyntaxError(f'Неизвестная переменная {name}')
        index = self.variables[name]
        self.emit(f'pop local {index}')


    def compile_return(self):
        self.consume('return')
        self.compile_expression()
        self.consume(';')
        self.emit('return')

    def compile_expression(self):
        self.compile_term()

        while self.current() in ['+', '-']:
            operator = self.consume()
            self.compile_term()
            if operator == '+':
                self.emit('add')
            else:
                self.emit('sub')

    def compile_term(self):
        token = self.current()

        if token is None:
            raise SyntaxError('Ожидалось выражение')
        
        if token.isdigit():
            self.consume()
            self.emit(f'push constant {token}')
        elif token == '(':
            self.consume('(')
            self.compile_expression()
            self.consume(')')
        elif token in self.variables:
            self.consume()
            index = self.variables[token]
            self.emit(f'push local {index}')

        else:
            raise SyntaxError(f'Неизвестный термин: {token}')



def main():
    compiler = SimpleCompiler(JACK_CODE)
    print(compiler.tokens)
    print(compiler.compile())

main()