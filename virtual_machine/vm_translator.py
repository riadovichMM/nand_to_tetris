import os


class vm_translator:

    def __init__(self, file_name, directory):
        self.file_name = file_name
        self.clean_file_name = file_name.split('.')[0]
        self.directory = directory
        self.vm_code = []
        self.asm_code = ''
        self.id_count = 0


        self.open_file_get_code()

    # service function

    def open_file_get_code(self):
        file = open(os.path.join(self.directory, self.file_name), 'r+')
        for line in file:
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
            self.id_count += 1

    def push_pop_command(self, parts):
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

        if command == 'pop':
            pass



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






















