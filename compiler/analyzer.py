class analyzer:

    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.xml = ''

    def write_xml(self, code):
        self.xml = self.xml + code + '\n'

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
        self.process('keyword', 'class')
        self.process('identifier')
        self.process('symbol', '{')

        current_token = self.tokens[self.index]
        if current_token[1] in ['static', 'field']:
            self.compile_class_var_dec()
            current_token = self.tokens[self.index]

        self.compile_class_var_dec()

        self.write_xml('</class>')
        print(self.xml)

    def compile_class_var_dec(self):
        self.write_xml('<classVarDec>')
        self.process('keyword') # static | field

        # type
        # self.type()

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
