import re


JACK_CODE = """
class Simple {
    field int x;

    method int calculate(int a, int b) {
        let x = a + b;
        return x;
    }

}
"""


class SimpleCompiler:

    def __init__(self, source):
        # Разбиваем исходный код на токены.
        self.tokens = re.findall(
            r"[A-Za-z_]\w*|[0-9]+|[{}()\[\].,;+\-<>=]",
            source
        )
        self.pos = 0
        self.vm = []
        self.class_name = ''

        self.local_table = {}
        self.local_index = 0

        self.arg_table = {}
        self.arg_index = 0

        self.field_table = {}
        self.field_index = 0


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

        while self.current() == 'field':
            self.compile_fields()

        while self.current() in ['function', 'method']:
            self.compile_function()

        self.consume('}')




    def compile_fields(self):
        self.consume('field')
        field_type = self.consume()

        while True:
            field_name = self.consume()
            self.field_table[field_name] = self.field_index
            self.field_index += 1

            if self.current() == ';':
                break

            self.consume(',')
        self.consume(';')



    def compile_function(self):
        kind_of_func = self.consume() # method or function

        return_type = self.consume() # type
        function_name = self.consume()

        self.arg_table = {}
        if kind_of_func == 'method':
            self.arg_index = 1
        else:
            self.arg_index = 0

        self.consume('(')
        self.compile_arguments()
        self.consume(')')
        self.consume('{')

        self.local_table = {}
        self.local_index = 0

        # var declaration
        while self.current() == 'var':
            self.compile_var()


        self.emit(f'function {self.class_name}.{function_name} {self.local_index}')

        if kind_of_func == 'method':
            self.emit('push argument 0')
            self.emit('pop pointer 0')

        # main statements/code of functions
        self.compile_statements()
        
        self.consume('}')
    #--------------------------------------------------------------





    def compile_arguments(self):
        while self.current() != ')':
            arg_type = self.consume() # type
            name = self.consume()

            self.arg_table[name] = self.arg_index
            self.arg_index += 1

            if self.current() == ',':
                self.consume(',')



    def compile_var(self):
        self.consume('var')
        var_type = self.consume()

        while True:
            name = self.consume()
            self.local_table[name] = self.local_index
            self.local_index += 1

            if self.current() != ',':
                break

            self.consume(',')
        self.consume(';')



    def compile_statements(self):
        while self.current() != '}':
            print(self.current())
            if self.current() == 'let':
                self.compile_let()
            elif self.current() == 'return':
                self.compile_return()
            elif self.current() == 'if':
                self.compile_if()
            elif self.current() == 'while':
                self.compile_while()
            # elif self.current() == 'do':
            #     self.compile_do()




    # statements
    def compile_let(self):
        self.consume('let')
        name = self.consume()
        self.consume('=')

        self.compile_expression()
        self.consume(';')

        if name in self.local_table:
            index = self.local_table[name]
            self.emit(f'pop local {index}')
        elif name in self.arg_table:
            index = self.arg_table[name]
            self.emit(f'pop argument {index}')
        elif name in self.field_table:
            index = self.field_table[name]
            self.emit(f'pop this {index}')


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



    def compile_while(self):
        self.emit('label WHILE_START')
        self.consume('while')
        self.consume('(')
        self.compile_expression()

        self.consume(')')

        self.emit('if-goto WHILE_BODY')
        self.emit('goto WHILE_END')

        self.emit('label WHILE_BODY')
        self.consume('{')
        self.compile_statements()
        self.consume('}')
        self.emit('goto WHILE_START')

        self.emit('label WHILE_END')


    # service functions
    def compile_expression(self):
        self.compile_term()
        while self.current() in ['+', '<']:
            operation = self.consume()
            self.compile_term()

            if operation == '+':
                self.emit('add')
            if operation == '<':
                self.emit('lt')


    def compile_term(self):
        token = self.current()

        if token.isdigit():
            self.consume()
            self.emit(f'push constant {token}')
        if token in self.local_table:
            self.consume()
            index = self.local_table[token]
            self.emit(f'push local {index}')
        elif token in self.arg_table:
            self.consume()
            index = self.arg_table[token]
            self.emit(f'push argument {index}')
        elif token in self.field_table:
            self.consume()
            index = self.field_table[token]
            self.emit(f'push this {index}')






def main():
    compiler = SimpleCompiler(JACK_CODE)
    print(compiler.tokens)
    compiler.compile()

    print('-----------------------')
    for line in compiler.vm:
        print(line)

    pass


main()