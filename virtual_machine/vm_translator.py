import os


class vm_translator:

    def __init__(self, file_name, directory):
        self.file_name = file_name
        self.clean_file_name = file_name.split('.')[0]
        self.directory = directory
        self.vm_code = []
        self.asm_code = ''
        self.id_count = 0
        self.current_function = ''

        self.open_file_get_code()

    # service function

    def open_file_get_code(self):
        file = open(os.path.join(self.directory, self.file_name), 'r+')
        for line in file:
            if line.startswith('//'):
                continue

            if '//' in line:
                line = line[:line.index('//')]

            line = line.strip()

            line = line.replace('\n', '')
            if not line.startswith('//') and not line == '':
                self.vm_code.append(line)
        file.close()

    def write_asm(self, text):
        self.asm_code = self.asm_code + text + '\n'

    def get_code(self):
        return self.asm_code

    # translate functions
    def translate(self):
        for line in self.vm_code:
            parts = line.split(' ')

            command = parts[0]
            if parts[0] in ['push', 'pop']:
                self.push_pop_command(parts)
            if parts[0] in ['add', 'sub', 'and', 'or', 'neg', 'not', 'eq', 'gt', 'lt']:
                self.arithmetic_logic_command(parts)
            if parts[0] in ['label', 'goto', 'if-goto']:
                self.program_flow_command(parts)
            if parts[0] in ['function', 'call', 'return']:
                self.function_calling_command(parts)
            self.id_count += 1

    def push_pop_command(self, parts):
        print(parts)
        command, segment, index = parts

        if command == 'push':
            if segment == 'constant':
                self.write_asm(f'@{index}')
                self.write_asm('D=A')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')
            if segment in ['local', 'argument', 'this', 'that']:
                segments = {
                    'local': '@LCL',
                    'argument': '@ARG',
                    'this': '@THIS',
                    'that': '@THAT',
                }
                self.write_asm(segments[segment])
                self.write_asm('D=M')

                self.write_asm(f'@{index}')
                self.write_asm('D=D+A')
                self.write_asm('A=D')

                self.write_asm('D=M')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')
            if segment in ['temp', 'pointer']:
                segments = {
                    'temp': '@5',
                    'pointer': '@3'
                }
                self.write_asm(f'@{index}')
                self.write_asm('D=A')

                self.write_asm(segments[segment])
                self.write_asm('D=D+A')

                self.write_asm('A=D')
                self.write_asm('D=M')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')
            if segment == 'static':
                self.write_asm(f'@{self.clean_file_name}.{index}')
                self.write_asm('D=M')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('M=D')

                self.write_asm('@SP')
                self.write_asm('M=M+1')

        if command == 'pop':
            if segment in ['local', 'argument', 'this', 'that']:
                
                segments = {
                    'local': '@LCL',
                    'argument': '@ARG',
                    'this': '@THIS',
                    'that': '@THAT',
                }

                self.write_asm(segments[segment])
                self.write_asm('D=M')

                self.write_asm(f'@{index}')
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

            if segment in ['temp', 'pointer']:
                segments = {
                    'temp': '@5',
                    'pointer': '@3'
                }
                self.write_asm(f'@{index}')
                self.write_asm('D=A')

                self.write_asm(segments[segment])
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

            if segment == 'static':
                self.write_asm('@SP')
                self.write_asm('M=M-1')

                self.write_asm('@SP')
                self.write_asm('A=M')
                self.write_asm('D=M')

                self.write_asm(f'@{self.clean_file_name}.{index}')
                self.write_asm('M=D')



    def arithmetic_logic_command(self, parts):
        command = parts[0]

        if command in ['add', 'sub', 'and', 'or']:
            operation = {
                'add': 'M=D+M',
                'sub': 'M=M-D',
                'and': 'M=D&M',
                'or': 'M=D|M',
            }
            # извлекаем y
            self.write_asm('@SP')
            self.write_asm('M=M-1')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('D=M')

            # извлекаем x и проводим операцию
            self.write_asm('@SP')
            self.write_asm('M=M-1')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm(operation[command])
            
            # увеличиваем счетчик
            self.write_asm('@SP')
            self.write_asm('M=M+1')

        if command in ['eq', 'gt', 'lt']:
            alias = {
                'eq': 'EQ',
                'gt': 'GT',
                'lt': 'LT',
            }
            jmps = {
                'eq': 'JEQ',
                'gt': 'JGT',
                'lt': 'JLT',
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

            self.write_asm('D=M-D')

            self.write_asm(f'@{alias[command]}_TRUE_{self.clean_file_name}_{self.id_count}')
            self.write_asm(f'D;{jmps[command]}')
            
            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=0')

            self.write_asm(f'@{alias[command]}_END_{self.clean_file_name}_{self.id_count}')
            self.write_asm('0;JMP')

            self.write_asm(f'({alias[command]}_TRUE_{self.clean_file_name}_{self.id_count})')
            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=-1')

            self.write_asm(f'({alias[command]}_END_{self.clean_file_name}_{self.id_count})')
            self.write_asm('@SP')
            self.write_asm('M=M+1')
        
        if command in ['neg', 'not']:
            operations = {
                'neg': 'M=-M',
                'not': 'M=!M',
            }
            self.write_asm('@SP')
            self.write_asm('M=M-1')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm(operations[command])

            self.write_asm('@SP')
            self.write_asm('M=M+1')


    def program_flow_command(self, parts):
        command = parts[0]
        label = parts[1]
        if command == 'label':
            if self.current_function:
                self.write_asm(f'({self.current_function}${label})')
            else:
                self.write_asm(f'({label})')
        if command == 'goto':
            if self.current_function:
                self.write_asm(f'@{self.current_function}${label}')
            else:
                self.write_asm(f'@{label}')

            self.write_asm('0;JMP')
        if command == 'if-goto':
            self.write_asm('@SP')
            self.write_asm('M=M-1')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('D=M')

            if self.current_function:
                self.write_asm(f'@{self.current_function}${label}')
            else:
                self.write_asm(f'@{label}')

            self.write_asm('D;JNE')

    def function_calling_command(self, parts):
        command = parts[0]

        if command == 'function':
            function_name = parts[1]
            local_vars = parts[2]
            self.write_asm(f'({function_name})')
            self.write_asm(f'@{local_vars}')
            self.write_asm('D=A')
            self.write_asm('@R13')
            self.write_asm('M=D')

            self.write_asm(f'(LOOP_{self.id_count})')
            self.write_asm('@R13')
            self.write_asm('D=M')

            self.write_asm(f'@END_LOOP_{self.id_count}')
            self.write_asm('D;JEQ')

            self.write_asm('@SP')
            self.write_asm('A=M')
            self.write_asm('M=0')

            self.write_asm('@SP')
            self.write_asm('M=M+1')


            self.write_asm('@R13')
            self.write_asm('M=M-1')
            self.write_asm(f'@LOOP_{self.id_count}')
            self.write_asm('0;JMP')
            
            self.write_asm(f'(END_LOOP_{self.id_count})')

        if command == 'call':
            pass








