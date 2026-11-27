import re



JACK_CODE = """
class Simple {
    field int x;
    static int y;

    method int calculate(int a, int b) {
        let x = 2 + 3;
        let y = 1;
        return x;
    }

    method int get_x() {
        return x;
    }

    function int get_y() {
        return y;
    }
}
"""


class compiler:

    def __init__(self, jack_code):
        self.jack_code = jack_code
        self.tokens = re.findall(
            r'"[^"]*"|[A-Za-z_]\w*|[0-9]+|[{}()\[\].,;+\-*/&|<>=~]',
            jack_code
        )
        self.marked_tokens = []
        self.vm_code = []
        self.pos = 0

        self.class_name = ''

        self.keywords = [
            'class', 'constructor', 'function', 'method',
            'field', 'static', 'var',
            'int', 'char', 'boolean', 'void',
            'true', 'false', 'null', 'this',
            'let', 'do', 'if', 'else', 'while', 'return',
        ]

        self.symbols = [
            '{', '}', '(', ')', '[', ']',
            '.', ',', ';',
            '+', '-', '*', '/', '&', '|',
            '<', '>', '=', '~',
        ]


        self.local_variables = {}
        self.local_count = 0

        self.argument_variables = {}
        self.argument_count = 0

        self.field_variables = {}
        self.field_count = 0

        self.static_variables = {}
        self.static_count = 0

        self.current_function_type = None


        self.mark_tokens()


    def mark_tokens(self):
        for token in self.tokens:
            if token in self.keywords:
                self.marked_tokens.append(['keyword', token])
            elif token in self.symbols:
                self.marked_tokens.append(['symbol', token])
            elif token.startswith('"'):
                self.marked_tokens.append(['stringConstant', token])
            elif token.isdigit():
                self.marked_tokens.append(['integerConstant', token])
            else:
                self.marked_tokens.append(['identifier', token])


    def current(self):
        if self.pos >= len(self.marked_tokens):
            return [None, None]
        return self.marked_tokens[self.pos]



    def emit(self, command):
        self.vm_code.append(command)



    def consume(self, type=None, value=None):
        current_token = self.current()

        if type == None and value == None:
            self.pos += 1
            return current_token


        if type and type != current_token[0]:
            raise Exception("Types do not match expect: {} current: {}".format(type, current_token[0]))
        if value and value != current_token[1]:
            raise Exception("Values do not match expect: {} current: {}".format(value, current_token[1]))
        self.pos += 1
        return current_token


    # точка входа
    def compile(self):
        self.consume('keyword', 'class')
        self.class_name = self.consume('identifier')[1]

        self.consume('symbol', '{')

        current_token = self.current()
        while current_token[1] in ['field', 'static']:
            self.compile_class_var_dec()
            current_token = self.current()

        print('static', self.static_variables)

        current_token = self.current()
        while current_token[1] in ['function', 'method']:
            print(current_token)
            self.compile_subroutine_dec()
            current_token = self.current()





    def compile_class_var_dec(self):
        field_or_static = None

        if self.current()[1] == 'field':
            self.consume('keyword', 'field')
            field_or_static = 'field'
        else:
            self.consume('keyword', 'static')
            field_or_static = 'static'


        var_type = self.consume()

        while self.current()[1] != ';':
            name = self.consume('identifier')

            if field_or_static == 'field':
                self.field_variables[name[1]] = self.field_count
                self.field_count += 1
            else:
                self.static_variables[name[1]] = self.static_count
                self.static_count += 1
    
            if self.current()[1] == ',':
                self.consume('symbol', ',')
        
        self.consume('symbol', ';')



    def compile_subroutine_dec(self):
        print('compile_subroutine_dec()')
        self.local_variables = {}
        self.local_count = 0

        
        self.argument_variables = {}
        self.argument_count = 0

        if self.current()[1] == 'function':
            self.consume('keyword', 'function')
            self.current_function_type = 'function'

        elif self.current()[1] == 'method':
            self.consume('keyword', 'method')
            self.current_function_type = 'method'

            self.argument_variables['this'] = self.argument_count
            self.argument_count += 1

        self.consume() # type

        function_name = self.consume('identifier')

        self.consume('symbol', '(')
        self.compile_parameter_list()
        self.consume('symbol', ')')
        self.consume('symbol', '{')

        while self.current()[1] == 'var':
            self.compile_vars()

        self.emit(f"function {self.class_name}.{function_name[1]} {len(self.local_variables)}")
        if self.current_function_type == 'method':
            self.emit('push argument 0')
            self.emit('pop pointer 0')

        while self.current()[1] != '}':
            if self.current()[1] == 'let':
                self.compile_let()
            if self.current()[1] == 'return':
                self.compile_return()
        self.consume('symbol', '}')





    def compile_parameter_list(self):
        while self.current()[1] != ')':
            self.consume() # type
            name_arg = self.consume('identifier')

            self.argument_variables[name_arg[1]] = self.argument_count
            self.argument_count += 1

            if self.current()[1] != ',':
                break

            self.consume('symbol', ',')





    def compile_vars(self):
        self.consume('keyword', 'var')
        var_type = self.consume()

        while True:
            var_name = self.consume('identifier')
            self.local_variables[var_name[1]] = self.local_count
            self.local_count += 1

            if self.current()[1] != ',':
                break

            self.consume('symbol', ',')

        self.consume('symbol', ';')





    def compile_let(self):
        self.consume('keyword', 'let')
        name = self.consume('identifier')
        self.consume('symbol', '=')

        self.compile_expression()
        self.consume('symbol', ';')

        if name[1] in self.local_variables:
            index = self.local_variables[name[1]]
            self.emit(f'pop local {index}')
        elif name[1] in self.argument_variables:
            index = self.argument_variables[name[1]]
            self.emit(f'pop argument {index}')
        elif name[1] in self.field_variables and self.current_function_type == 'method':
            index = self.field_variables[name[1]]
            self.emit(f'pop this {index}')
        elif name[1] in self.static_variables:
            index = self.static_variables[name[1]]
            self.emit(f'pop static {index}')



    def compile_return(self):
        self.consume('keyword', 'return')
        if self.current()[1] == ';':
            self.emit('push constant 0')

        self.compile_expression()
        self.consume('symbol', ';')
        self.emit('return')


    def compile_expression(self):
        self.compile_term()

        while self.current()[1] in ['+', '-']:
            operator = self.consume('symbol')[1]
            self.compile_term()

            if operator == '+':
                self.emit('add')
            elif operator == '-':
                self.emit('sub')



    def compile_term(self):
        token = self.current()
        token_value = token[1]

        if token_value.isdigit():
            self.consume()
            self.emit(f'push constant {token_value}')
        elif token_value in self.local_variables:
            self.consume()
            index = self.local_variables[token_value]
            self.emit(f'push local {index}')
        elif token_value in self.argument_variables:
            self.consume()
            index = self.argument_variables[token_value]
            self.emit(f'push argument {index}')
        elif token_value in self.field_variables and self.current_function_type == 'method':
            self.consume()
            index = self.field_variables[token_value]
            self.emit(f'push this {index}')
        elif token_value in self.static_variables:
            self.consume()
            index = self.static_variables[token_value]
            self.emit(f'push static {index}')





def main():
    comp = compiler(JACK_CODE)
    comp.compile()

    for line in comp.vm_code:
        print(line)


main()


