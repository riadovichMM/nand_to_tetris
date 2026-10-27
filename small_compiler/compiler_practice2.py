import re


JACK_CODE = """
class Simple {
    function int calculate() {
        var int x, y;

        let x = 2 + 3;

        if (1) {
            let y = 10;
        } else {
            let y = 0
        }

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
        self.class_name = ''
        self.symbol_table = {}
        self.local_index = 0


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




    # main functions
    def compile(self):
        self.consume('class')
        self.class_name = self.consume()
        self.consume('{')

        while self.current() != '}':
            self.compile_function()

        self.consume('}')

    def compile_function(self):
        self.consume('function')
        return_type = self.consume() #type
        function_name = self.consume()

        self.consume('(')
        self.consume(')')
        self.consume('{')

        self.symbol_table = {}
        self.local_index = 0

        # var declaration
        while self.current() == 'var':
            self.compile_var()


        self.emit(f'function {self.class_name}.{function_name} {self.local_index}')

        # main statements/code of functions
        self.compile_statements()
        
        self.consume('}')
    #--------------------------------------------------------------




    def compile_var(self):
        self.consume('var')
        var_type = self.consume()

        while True:
            name = self.consume()
            self.symbol_table[name] = self.local_index
            self.local_index += 1

            if self.current() != ',':
                break

            self.consume(',')
        self.consume(';')



    def compile_statements(self):
        while self.current() != '}':
            if self.current() == 'let':
                self.compile_let()
            elif self.current() == 'return':
                self.compile_return()
            elif self.current() == 'if':
                self.compile_if()
            print(self.current())


    # statements
    def compile_let(self):
        self.consume('let')
        name = self.consume()
        self.consume('=')

        self.compile_expression()
        self.consume(';')

        index = self.symbol_table[name]
        self.emit(f'pop local {index}')



    def compile_return(self):
        self.consume('return')

        self.compile_expression()

        self.consume(';')
        self.emit('return')



    def compile_if(self):
        self.consume('if')
        self.consume('(')
        self.compile_expression()
        self.consume(')')

        self.emit('if-goto THEN')
        self.emit('goto ELSE')

        self.emit('label THEN')
        self.consume('{')
        self.compile_statements()
        self.consume('}')

        if self.current() == 'else':
            self.consume('else')
            self.emit('goto END')

            self.emit('label ELSE')
            self.consume('{')
            self.compile_statements()
            self.consume('}')

            self.emit('label END')
        else:
            self.emit('label ELSE')



    # service functions
    def compile_expression(self):
        self.compile_term()

        while self.current() in ['+']:
            operation = self.consume()
            self.compile_term()

            if operation == '+':
                self.emit('add')


    def compile_term(self):
        token = self.current()

        if token.isdigit():
            self.consume()
            self.emit(f'push constant {token}')
        if token in self.symbol_table:
            self.consume()
            index = self.symbol_table[token]
            self.emit(f'push local {index}')






def main():
    compiler = SimpleCompiler(JACK_CODE)
    compiler.compile()
    print(compiler.tokens)

    print('-----------------------')
    for line in compiler.vm:
        print(line)

    pass


main()