import re 

 
JACK_CODE = """
class Simple {
    function int calculate() {
        var int x;
 
        let x = 2 + 3 + (1);

        return x;
    }
}
"""

# далее усложнять надо это и вперед

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
        self.symbol_table = {}
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

        self.symbol_table = {}
        self.local_count = 0

        # тут мы компилируем объявления фукнции
        while self.current() == 'var':
            self.compile_var()

        # имя функции с классом и количество локальных переменных нам известно
        # и мы их прописываем в vm
        self.emit(f'function {self.class_name}.{function_name} {self.local_count}')

        # компилируем инструкции функции
        # тут короче мы чекаем за основной код функции где все проиходит
        self.compile_statements()
        self.consume('}')





    def compile_statements(self):
        while self.current() != '}':
            if self.current() == 'let':
                self.compile_let()
            elif self.current() == 'return':
                self.compile_return()
            elif self.current() == 'if':
                self.compile_if()






    def compile_if(self):
        self.consume('if')
        self.consume('(')
        self.compile_expression()
        self.consume(')')

        self.emit('not')
        self.emit('if-goto IF_END')

        self.consume('{')
        self.compile_statements()
        self.consume('}')

        self.emit('label IF_END')





    def compile_if_without_not(self):
        self.consume('if')
        self.consume('(')
        self.compile_expression()
        self.consume(')')

        self.emit('if-goto IF_TRUE')    # условие истинно -> в тело
        self.emit('goto IF_END')        # иначе -> мимо тела
        self.emit('label IF_TRUE')

        self.consume('{')
        self.compile_statements()
        self.consume('}')

        self.emit('label IF_END')






    def compile_var(self):
        self.consume('var')
        var_type = self.consume()

        while True:
            name = self.consume()

            self.symbol_table[name] = self.local_count
            self.local_count +=  1

            if self.current() != ',':
                break

            self.consume(',')
        self.consume(';')



    def compile_let(self):
        self.consume('let')
        var_name = self.consume()
        self.consume('=')
        self.compile_expression()
        self.consume(';')

        if var_name not in self.symbol_table:
            raise SyntaxError(
                f"Неизвестная переменная: {var_name}"
            )

        index = self.symbol_table[var_name]
        self.emit(f"pop local {index}")



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
        elif token in self.symbol_table:
            self.consume()
            index = self.symbol_table[token]
            self.emit(f'push local {index}')
        elif token == '(':
            self.consume('(')
            self.compile_expression()
            self.consume(')')
        else:
            raise SyntaxError(
                f"Неизвестный термин: {token}"
            )


def main():
    compiler = SimpleCompiler(JACK_CODE)
    print(compiler.tokens)
    compiler.compile()
    for line in compiler.vm:
        print(line)




main()