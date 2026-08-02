class tokenizer:

    def __init__(self):
        self.keywords = [
            'class', 'constructor', 'function', 'method',
            'field', 'static', 'var', 
            'int', 'char', 'boolean', 'void', 
            'true', 'false', 'null', 'this', 
            'let', 'do', 'if', 'else', 'while', 'return'
        ]
        self.symbols = [
            '{', '}', '(', ')', '[', ']', 
            '.', ',', ';', 
            '+', '-', '*', '/', 
            '&', '|', '~', 
            '<', '>', '='
        ]
        self.jack_code = ''
        self.index = 0
        self.tokens = []
        self.path = None

        # tokens:
        #   keywords
        #   symbols
        #   identifier
        #   intConstant
        #   stringConstant

    def open_file_and_read(self, path):
        self.path = path
        file = open(path, 'r+')
        code = file.readlines()
        file.close()

        for line in code:
            if line.startswith('//'):
                continue
            line = line.strip()
            self.jack_code = self.jack_code + line + '\n'
        self.jack_code = self.remove_jack_comments(self.jack_code)

    def remove_jack_comments(self, code):
        """
        Удаляет все комментарии из кода на языке Jack.
        Обрабатывает однострочные (//) и многострочные (/* */) комментарии.
        Игнорирует комментарии внутри строковых констант.
        """
        result = []
        i = 0
        in_string = False
        in_multiline_comment = False
        
        while i < len(code):
            # Если мы внутри многострочного комментария
            if in_multiline_comment:
                # Ищем закрывающий */
                if i + 1 < len(code) and code[i] == '*' and code[i + 1] == '/':
                    in_multiline_comment = False
                    i += 2  # Пропускаем */
                    continue
                i += 1
                continue
            
            # Если мы внутри строковой константы
            if in_string:
                result.append(code[i])
                if code[i] == '"':
                    in_string = False
                i += 1
                continue
            
            # Проверяем начало однострочного комментария
            if i + 1 < len(code) and code[i] == '/' and code[i + 1] == '/':
                # Пропускаем всё до конца строки
                while i < len(code) and code[i] != '\n':
                    i += 1
                # Сохраняем символ новой строки, если он есть
                if i < len(code):
                    result.append(code[i])
                    i += 1
                continue
            
            # Проверяем начало многострочного комментария
            if i + 1 < len(code) and code[i] == '/' and code[i + 1] == '*':
                in_multiline_comment = True
                i += 2  # Пропускаем /*
                continue
            
            # Проверяем начало строковой константы
            if code[i] == '"':
                in_string = True
                result.append(code[i])
                i += 1
                continue
            
            # Обычный символ - добавляем в результат
            result.append(code[i])
            i += 1
        
        return ''.join(result)




    def tokenize(self):
        while self.index < len(self.jack_code):
            if self.jack_code[self.index].isalpha():
                self.keyword_or_identifier()
            elif self.jack_code[self.index] in self.symbols:
                token = self.jack_code[self.index]
                self.tokens.append(['symbol', token])
                self.index += 1
            elif self.jack_code[self.index] == '"':
                self.string_constant()
            elif self.jack_code[self.index].isdigit():
                self.integer_constant()
            else:
                self.index += 1


    def keyword_or_identifier(self):
        token = ''
        while self.jack_code[self.index].isalpha():
            token += self.jack_code[self.index]
            self.index+=1
        if token in self.keywords:
            self.tokens.append(['keyword', token])
        else:
            self.tokens.append(['identifier', token])


    def string_constant(self):
        self.index+= 1
        token = ''
        while self.jack_code[self.index] != '"':
            token += self.jack_code[self.index]
            self.index+=1
        self.index+=1
        self.tokens.append(['stringConstant', token])


    def integer_constant(self):
        token = ''
        while self.jack_code[self.index].isdigit():
            token += self.jack_code[self.index]
            self.index+=1
        self.tokens.append(['integerConstant', token])



    def generate_xml(self):
        file_name = self.path.split('\\')[1].split('.')[0] + ".xml"
        file = open('output/'+ file_name, 'w+')
        file.write('<tokens>\n')
        for token in self.tokens:
            file.write(f'<{token[0]}>{token[1]}</{token[0]}>\n')
        file.write('</tokens>\n')
        file.close()


