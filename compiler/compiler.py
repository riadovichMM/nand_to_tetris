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

        self.variables = {}
        self.local_count = 0

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
        self.vm.append(command)



    def consume(self, type=None, value=None):
        current_token = self.current()

        if type == None and value == None:
            self.pos += 1
            return current_token


        if type and type != current_token[0]:
            raise Exception(f'Types do not match expect: {type} current: {current_token[0]}')
        if value and value != current_token[1]:
            raise Exception(f'Values do not match expect: {value} current: {current_token[1]}')
        self.pos += 1
        return current_token



    def compile(self):
        self.consume('keyword', 'class')
        self.consume('identifier')

        self.consume('symbol', '{')

        current_token = self.current()
        while current_token[1] in ['function']:
            self.compile_subroutine_dec()
            current_token = self.current()



    def compile_subroutine_dec(self):
        self.consume('keyword', 'function')
        self.consume() # type

        function_name = self.consume('identifier')
        print(function_name)

        self.consume('symbol', '(')
        self.consume('symbol', ')')
        self.consume('symbol', '{')

        self.variables = {}
        self.local_count = 0


        while self.current()[1] == 'var':
            self.compile_var()
        





def main():
    comp = compiler(JACK_CODE)
    comp.compile()


main()


