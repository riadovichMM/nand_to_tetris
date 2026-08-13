class analyzer:

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.xml = ''
        self.level = 0

    def write_xml(self, code):
        self.xml =  self.xml + (self.level * '  ') + code + '\n'

    def process(self, type, value=None):
        current_token = self.tokens[self.index]
        if current_token[0] != type:
            raise ValueError('Type token is not match')
        if value and current_token[1] != value:
            raise ValueError('Value token is not match')
        self.write_xml(f'<{current_token[0]}>{current_token[1]}</{current_token[0]}>')
        self.index += 1

    def compile_class(self):
        self.write_xml('<class>')
        self.level+=1

        self.process('keyword', 'class')
        self.process('identifier')
        self.process('symbol', '{')


        # class_var_dec
        current_token = self.tokens[self.index]
        while current_token[1] in ['static', 'field']:
            self.compile_class_var_dec()
            current_token = self.tokens[self.index]

        # subroutine dec
        current_token = self.tokens[self.index]
        while current_token[1] in ['constructor', 'function', 'method']:
            self.compile_subroutine_dec()
            current_token = self.tokens[self.index]



        self.level-=1
        self.write_xml('</class>')
        print(self.xml)

    def compile_class_var_dec(self):
        self.write_xml('<classVarDec>')
        self.level+=1

        self.process('keyword') # static | field

        # type
        self.type()
        self.process('identifier')

        current_token = self.tokens[self.index]
        while current_token[1] == ',':
            self.process('symbol', ',')
            self.process('identifier')
        self.process('symbol', ';')


        self.level-=1
        self.write_xml('</classVarDec>')

        pass

    def type(self):
        current_type = self.tokens[self.index]
        if current_type[1] in ['int', 'char', 'boolean']:
            self.process('keyword')
        elif current_type[0] == 'identifier':
            self.process('identifier')
        else:
            raise ValueError('Type Error')


    def compile_subroutine_dec(self):
        self.write_xml('<subroutineDec>')
        self.level+=1

        self.process('keyword') # constructor | function | method

        current_token = self.tokens[self.index]
        if current_token[1] == 'void':
            self.process('keyword', 'void')
        else:
            self.type()
        pass

        self.process('identifier')
        self.process('symbol', '(')
        self.compile_parameter_list()
        self.process('symbol', ')')
        self.compile_subroutine_body()

        self.level-=1
        self.write_xml('<subroutineDec>')

    def compile_parameter_list(self):
        self.write_xml('<parameterList>')
        self.level+=1

        current_token = self.tokens[self.index]
        if current_token[0] != 'symbol':
            self.type()
            self.process('identifier')

        current_token = self.tokens[self.index]
        while current_token[1] != ')':
            self.process('symbol', ',')
            self.type()
            self.process('identifier')
            current_token = self.tokens[self.index]


        self.level-=1
        self.write_xml('</parameterList>')


    def compile_subroutine_body(self):
        self.write_xml('<subroutineBody>')
        self.level+=1

        self.process('symbol', '{')

        self.compile_var_dec()
        self.compile_statements()

        self.level-=1
        self.write_xml('</subroutineBody>')


    def compile_var_dec(self):
        self.write_xml('<varDec>')
        self.level+=1

        self.process('keyword', 'var')
        self.type()
        self.process('identifier')

        current_token = self.tokens[self.index]
        while current_token[1] == ',':
            self.process('symbol', ',')
            self.process('identifier')
            current_token = self.tokens[self.index]

        self.process('symbol', ';')

        self.level-=1
        self.write_xml('</varDec>')

    def compile_statements(self):
        self.write_xml('<statements>')
        self.level+=1

        current_token = self.tokens[self.index]
        flag = True
        while flag:
            if current_token[1] == 'let':
                self.compile_let_statement()
            if current_token[1] == 'if':
                self.compile_if_statement()
            if current_token[1] == 'while':
                self.compile_while_statement()
            if current_token[1] == 'do':
                self.compile_do_statement()
            if current_token[1] == 'return':
                self.compile_return_statement()
                flag = False
            current_token = self.tokens[self.index]

        self.level-=1
        self.write_xml('</statements>')


    def compile_let_statement(self):
        self.write_xml('<letStatement>')
        self.level+=1

        self.process('keyword', 'let')
        self.process('identifier')

        current_token = self.tokens[self.index]
        if current_token[1] == '[':
            self.process('symbol', '[')
            self.compile_expression()
            self.process('symbol', ']')

        self.process('symbol', '=')
        self.compile_expression()
        self.process('symbol', ';')

        self.level-=1
        self.write_xml('</letStatement>')

    def compile_if_statement(self):
        self.write_xml('<ifStatement>')
        self.level+=1

        self.process('keyword', 'if')

        self.process('symbol', '(')
        self.compile_expression()
        self.process('symbol', ')')

        self.process('symbol', '{')
        self.compile_statements()
        self.process('symbol', '}')

        current_token = self.tokens[self.index]
        if current_token[1] == 'else':
            self.process('keyword', 'else')
            self.process('symbol', '{')
            self.compile_statements()
            self.process('symbol', '}')



        self.level-=1
        self.write_xml('</ifStatement>')

    def compile_while_statement(self):
        self.write_xml('<whileStatement>')
        self.level+=1

        self.process('keyword', 'while')
        self.process('symbol', '(')
        self.compile_expression()
        self.process('symbol', ')')

        self.process('symbol', '{')
        self.compile_statements()
        self.process('symbol', '}')

        self.level-=1
        self.write_xml('</whileStatement>')

    def compile_do_statement(self):
        self.write_xml('<doStatement>')
        self.level+=1

        self.process('keyword', 'do')
        self.compile_subroutine_call()
        self.process('symbol', ';')


        self.level-=1
        self.write_xml('</doStatement>')


    def compile_return_statement(self):
        self.write_xml('<doStatement>')
        self.level+=1

        self.process('keyword', 'return')
        current_token = self.tokens[self.index]
        if current_token[1] != ';':
            self.compile_expression()
        self.process('symbol', ';')

        self.level-=1
        self.write_xml('</doStatement>')


    def compile_expression(self):
        self.write_xml('<expression>')
        self.level+=1

        self.compile_term()
        current_token = self.tokens[self.index]
        while current_token[1] in ['+', '-', '*', '/', '&', '|', '<', '>', '=']:
            self.compile_op()
            self.compile_term()

        self.level-=1
        self.write_xml('</expression>')

    def compile_term(self):
        self.write_xml('<term>')
        self.level+=1


        self.level-=1
        self.write_xml('</term>')
        
        pass

    def compile_op(self):
        self.write_xml('<op>')
        self.level+=1

        self.process('symbol')

        self.level-=1
        self.write_xml('</op>')