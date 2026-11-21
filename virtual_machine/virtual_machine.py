from pathlib import Path
import ntpath
import re

class virtual_machine:

    def __init__(self, dir_or_file):

        self.dir_or_file = dir_or_file
        self.files = {}
        self.asm_code = []
        self.global_uid = 0
        self.current_file_name = None
        self.current_function_name_for_prefix = ''

        if '.vm' in dir_or_file:
            self.read_file()
        else:
            self.open_directory_and_read_files()

        self.bootstrap()


    def read_file(self):
        f = open(self.dir_or_file, 'r')
        clean_name = self.dir_or_file.split('/')[-1]
        self.files[clean_name] = f.readlines()
        f.close()

    def open_directory_and_read_files(self):
        dir_path = Path(self.dir_or_file)
        files = [f for f in dir_path.iterdir() if f.is_file()]

        for file in files:
            f = open(self.dir_or_file + file.name, 'r')
            self.files[file.name] = f.readlines()
            f.close()

    def write_asm(self, code):
        self.asm_code.append(code)

    def get_clean_code(self, code):
        clean_code = []
        for line in code:
            if line.startswith('//') or line == '\n':
                continue

            if '//' in line:
                line = line.split('//')[0]

            clean_code.append(line.strip())
        return clean_code

    def generate_asm_file(self):
        if '.vm' in self.dir_or_file:
            new_path = self.dir_or_file.replace('.vm', '.asm')
            f = open(new_path, 'w+')
            for line in self.asm_code:
                f.write(line + '\n')
            f.close()
        else:
            parts = [p for p in re.split(r'[\\/]', self.dir_or_file) if p]
            last_part = parts[-1] if parts else ""
            print(last_part)

            new_path = self.dir_or_file + last_part + '.asm'
            f = open(new_path, 'w+')
            for line in self.asm_code:
                f.write(line + '\n')
            f.close()


    def bootstrap(self):
        self.write_asm('@256')
        self.write_asm('D=A')
        self.write_asm('@SP')
        self.write_asm('M=D')
        self.call_command()


    def call_command(self):
        args = 0
        func_name = 'Sys.init'

        self.write_asm(f'@return_address_{self.global_uid}')
        self.write_asm('D=A')
        self.write_asm('@SP')
        self.write_asm('A=M')
        self.write_asm('M=D')

        self.write_asm('@SP')
        self.write_asm('M=M+1')


        # положить на стек LCL ARG THIS THAT
        for segment in ['@LCL', '@ARG', '@THIS', '@THAT']:
            self.write_asm(segment) #LCL
            self.write_asm('D=M')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=D')

            self.write_asm('@SP')
            self.write_asm('M=M+1')

        # установка ARG
        # ARG = SP - (5 + m)
        self.write_asm(f'@{args}')
        self.write_asm(f'D=A')
        self.write_asm(f'@5')
        self.write_asm('D=D+A')

        self.write_asm('@SP')
        self.write_asm('D=M-D')

        self.write_asm('@ARG')
        self.write_asm('M=D')


        # установка LCL
        # LCL = SP

        self.write_asm('@SP')
        self.write_asm('D=M')

        self.write_asm('@LCL')
        self.write_asm('M=D')

        self.write_asm(f'@{func_name}')
        self.write_asm('0;JMP')

        self.write_asm(f'(return_address_{self.global_uid})')



    def translate(self):
        for file in self.files:
            filename = ntpath.basename(file)
            clean_filename = filename.split('.')[0]
            self.current_file_name = clean_filename

            code = self.get_clean_code(self.files[file])

            for line in code:

                parts = line.split()
                self.write_asm(f'// {line}')
                if parts[0] in ['push', 'pop']:
                    self.push_pop_command(parts)
                if parts[0] in ['eq', 'lt', 'gt', 'add', 'sub', 'and', 'or', 'not', 'neg']:
                    self.logic_arithmetic(parts[0])
                if parts[0] in ['label', 'goto', 'if-goto']:
                    self.branch_commands(parts)
                if parts[0] in ['function', 'call', 'return']:
                    self.function_commands(parts)
                self.global_uid += 1


    def push_pop_command(self, parts):
        if parts[0] == 'push':
            if parts[1] == 'constant':
                self.write_asm(f'@{parts[2]}')
                self.write_asm('D=A')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')
            if parts[1] in ['local', 'argument', 'this', 'that', 'temp', 'pointer']:
                segments = {
                    'local': '@LCL',
                    'argument': '@ARG',
                    'this': '@THIS',
                    'that': '@THAT',

                    'temp': '@5',
                    'pointer': '@3'
                }

                self.write_asm(segments[parts[1]])   # @LCL
                if parts[1] in ['pointer', 'temp']:
                    self.write_asm('D=A')
                else:
                    self.write_asm('D=M')
                self.write_asm(f'@{parts[2]}')
                self.write_asm('D=D+A')
                self.write_asm('A=D')
                self.write_asm('D=M')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')
            if parts[1] == 'static':
                self.write_asm(f'@{self.current_file_name}.{parts[2]}')
                self.write_asm('D=M')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')
        else:
            if parts[1] in ['local', 'argument', 'this', 'that', 'temp', 'pointer']:
                segments = {
                    'local': '@LCL',
                    'argument': '@ARG',
                    'this': '@THIS',
                    'that': '@THAT',

                    'temp': '@5',
                    'pointer': '@3'
                }

                self.write_asm(segments[parts[1]])
                if parts[1] in ['pointer', 'temp']:
                    self.write_asm('D=A')
                else:
                    self.write_asm('D=M')
                self.write_asm(f'@{parts[2]}')
                self.write_asm('D=D+A')

                self.write_asm('@R13')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M-1')
                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('D=M')

                self.write_asm('@R13')
                self.write_asm('A=M')
                self.write_asm('M=D')
            if parts[1] == 'static':
                self.write_asm('@SP')
                self.write_asm('M=M-1')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('D=M')

                self.write_asm(f'@{self.current_file_name}.{parts[2]}')
                self.write_asm('M=D')




    def logic_arithmetic(self, command):

        # оптимизированная версия
        if command in ['sub', 'add', 'and', 'or']:
            operations = {
                'add': 'M=D+M',
                'sub': 'M=M-D',
                'and': 'M=D&M',
                'or':  'M=D|M'
            }

            self.write_asm('@SP')
            self.write_asm('M=M-1')
            self.write_asm('@SP')
            self.write_asm('A=M')

            self.write_asm('D=M')

            self.write_asm('@SP')
            self.write_asm('M=M-1')
            self.write_asm('@SP')
            self.write_asm('A=M')

            self.write_asm(operations[command])

            self.write_asm('@SP')
            self.write_asm('M=M+1')

        if command in ['neg', 'not']:
            operations = {
                'neg': 'M=-M',
                'not': 'M=!M',
            }

            self.write_asm('@SP')
            self.write_asm('M=M-1')
            self.write_asm('A=M')

            self.write_asm(operations[command])

            self.write_asm('@SP')
            self.write_asm('M=M+1')

        if command in ['eq', 'gt', 'lt']:
            operations = {
                'eq': 'D;JEQ',
                'gt': 'D;JGT',
                'lt': 'D;JLT',
            }

            self.write_asm('@SP')
            self.write_asm('M=M-1')
            self.write_asm('A=M')
            self.write_asm('D=M')

            self.write_asm('@SP')
            self.write_asm('M=M-1')
            self.write_asm('A=M')
            self.write_asm('D=M-D')

            self.write_asm(f'@TRUE_BLOCK_{self.global_uid}')
            self.write_asm(operations[command]) # D;JEQ | eq

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=0')
            self.write_asm(f'@END_{self.global_uid}')
            self.write_asm('0;JMP')


            self.write_asm(f'(TRUE_BLOCK_{self.global_uid})')
            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=-1')
            self.write_asm(f'@END_{self.global_uid}')
            self.write_asm('0;JMP')


            self.write_asm(f'(END_{self.global_uid})')
            self.write_asm('@SP')
            self.write_asm('M=M+1')

    def branch_commands(self, parts):
        if parts[0] == 'label':
            if self.current_function_name_for_prefix != '':
                self.write_asm(f'({self.current_function_name_for_prefix}${parts[1]})')
            else:
                self.write_asm(f'({parts[1]})')


        if parts[0] == 'goto':
            if self.current_function_name_for_prefix != '':
                self.write_asm(f'@{self.current_function_name_for_prefix}${parts[1]}')
            else:
                self.write_asm(f'@{parts[1]}')

            self.write_asm('0;JMP')

        if parts[0] == 'if-goto':
            self.write_asm('@SP')
            self.write_asm('M=M-1')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('D=M')

            if self.current_function_name_for_prefix != '':
                self.write_asm(f'@{self.current_function_name_for_prefix}${parts[1]}')
            else:
                self.write_asm(f'@{parts[1]}')

            self.write_asm('D;JNE')


    def function_commands(self, parts):
        if parts[0] == 'function':
            self.current_function_name_for_prefix = parts[1]
            
            self.write_asm(f'({parts[1]})')
            self.write_asm(f'@{parts[2]}') #2 local vars
            self.write_asm('D=A')
            self.write_asm('@R13')
            self.write_asm('M=D')

            self.write_asm(f'(CONDITION_{self.global_uid})')
            self.write_asm('@R13')
            self.write_asm('D=M')
            self.write_asm(f'@END_{self.global_uid}')
            self.write_asm('D;JEQ')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=0')
            self.write_asm('@SP')
            self.write_asm('M=M+1')

            self.write_asm('@R13')
            self.write_asm('M=M-1')

            self.write_asm(f'@CONDITION_{self.global_uid}')
            self.write_asm('0;JMP')

            self.write_asm(f'(END_{self.global_uid})')

        if parts[0] == 'call':
            # положить на стек адресс возврата
            self.write_asm(f'@return_address_{self.global_uid}')
            self.write_asm('D=A')
            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=D')

            self.write_asm('@SP')
            self.write_asm('M=M+1')


            # положить на стек LCL ARG THIS THAT
            for segment in ['@LCL', '@ARG', '@THIS', '@THAT']:
                self.write_asm(segment) #LCL
                self.write_asm('D=M')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')

            # установка ARG
            # ARG = SP - (5 + m)
            self.write_asm(f'@{parts[2]}')
            self.write_asm(f'D=A')
            self.write_asm(f'@5')
            self.write_asm('D=D+A')

            self.write_asm('@SP')
            self.write_asm('D=M-D')

            self.write_asm('@ARG')
            self.write_asm('M=D')


            # установка LCL
            # LCL = SP

            self.write_asm('@SP')
            self.write_asm('D=M')

            self.write_asm('@LCL')
            self.write_asm('M=D')

            self.write_asm(f'@{parts[1]}')
            self.write_asm('0;JMP')

            self.write_asm(f'(return_address_{self.global_uid})')


        if parts[0] == 'return':
            # нужно сохранить доступ к фрейму
            self.write_asm('@LCL')
            self.write_asm('D=M')
            self.write_asm('@frame')
            self.write_asm('M=D')


            # берем адрес возврата и сохраняем его
            self.write_asm('@frame')
            self.write_asm('D=M')
            self.write_asm('@5')
            self.write_asm('D=D-A')
            self.write_asm('A=D')
            self.write_asm('D=M')


            self.write_asm('@R13')
            self.write_asm('M=D')

            # передвигаем результат в ARG
            self.write_asm('@SP')
            self.write_asm('M=M-1')
            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('D=M')

            self.write_asm('@ARG')
            self.write_asm('A=M')
            self.write_asm('M=D')

            # SP = ARG + 1
            self.write_asm('@ARG')
            self.write_asm('D=M+1')

            self.write_asm('@SP')
            self.write_asm('M=D')


            # востановление указателей 
            for index, segment in enumerate(['@THAT', '@THIS', '@ARG', '@LCL']):
                self.write_asm('@frame')
                self.write_asm('D=M')
                self.write_asm(f'@{index + 1}')
                self.write_asm('D=D-A')

                self.write_asm('A=D')
                self.write_asm('D=M')
                self.write_asm(segment)
                self.write_asm('M=D')

            self.write_asm('@R13')
            self.write_asm('A=M')
            self.write_asm('0;JMP')







































