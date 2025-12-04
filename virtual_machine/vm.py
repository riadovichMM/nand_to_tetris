import sys

class VirtualMachine:

    def __init__(self, vm_filename):
        self.vm_filename = vm_filename
        self.clear_vm_filename = vm_filename.replace('./', '').replace('.vm', '')
        self.vm_code = []
        self.asm_code = []
        self.global_uuid = 0


    def open_file_and_read(self):
        file = open(self.vm_filename, 'r')
        self.vm_code = [line.strip() for line in  file.readlines()]
        file.close()

    def write_asm_file(self):
        file = open('./output.asm', 'w+')
        for line in self.asm_code:
            file.write(line + '\n')
        file.close()

    def put_in_asm_code(self, asm_code):
        for line in asm_code:
            self.asm_code.append(line)


    def parse_vm_code(self):
        for line in self.vm_code:
            parts_of_line = line.split(' ')
            if len(parts_of_line) == 3:
                if parts_of_line[0] == 'push' or parts_of_line[0] == 'pop':
                    self.push_pop_command(parts_of_line)
            if len(parts_of_line) == 1:
                if parts_of_line[0] in ['add', 'sub', 'neg', 'eq', 'gt', 'lt', 'and', 'or', 'not']:
                    self.arithmetic_logic_command(parts_of_line[0])
            self.global_uuid+=1

    def push_pop_command(self, parts_of_line):
        if parts_of_line[0] == 'push':
            if parts_of_line[1] == 'constant':
                self.put_in_asm_code([
                    # push constant n
                    f'@{parts_of_line[2]}',
                    'D=A',
                    '@SP',
                    'A=M',
                    'M=D',
                    '@SP',
                    'M=M+1',
                ])
            if parts_of_line[1] in ['local', 'argument', 'this', 'that']:
                segments = {
                    'local': 'LCL',
                    'argument': 'ARG',
                    'this': 'THIS',
                    'that': 'THAT',
                }

                self.put_in_asm_code([
                    f'@{segments[parts_of_line[1]]}',
                    'D=M',

                    f'@{parts_of_line[2]}',
                    'D=D+A',
                    'A=D',
                    'D=M',

                    '@SP',
                    'A=M',
                    'M=D',

                    '@SP',
                    'M=M+1',
                ])
            if parts_of_line[1] == 'static':
                self.put_in_asm_code([
                    '@SP',
                    'M=M-1',
                    'A=M',
                    'D=M',

                    f'@{self.clear_vm_filename}.{parts_of_line[2]}',
                    'M=D',
                ])

            if parts_of_line[1] in ['temp', 'pointer']:
                segments = {
                    'temp': 5,
                    'pointer': 3
                }

                self.put_in_asm_code([
                    f'@{parts_of_line[2]}',
                    'D=A',

                    f'@{segments[parts_of_line[1]]}',
                    'D=D+A',
                    'A=D',
                    'D=M',

                    '@SP',
                    'A=M',
                    'M=D',

                    '@SP',
                    'M=M+1',
                ])



        if parts_of_line[0] == 'pop':
            if parts_of_line[1] in ['local', 'argument', 'this', 'that']:
                segments = {
                    'local': 'LCL',
                    'argument': 'ARG',
                    'this': 'THIS',
                    'that': 'THAT',
                }

                self.put_in_asm_code([
                    '@SP',
                    'M=M-1',
                    'A=M',
                    'D=M',

                    '@R13',
                    'M=D',

                    f'@{segments[parts_of_line[1]]}',
                    'D=M',

                    f'@{parts_of_line[2]}',
                    'D=D+A',
                    '@R14',
                    'M=D',

                    '@R13',
                    'D=M',

                    '@R14',
                    'A=M',
                    'M=D',
                ])
            if parts_of_line[1] == 'static':
                self.put_in_asm_code([
                    f'@{self.clear_vm_filename}.{parts_of_line[2]}',
                    'D=M',

                    '@SP',
                    'A=M',
                    'M=D',

                    '@SP',
                    'M=M+1',
                ])

            if parts_of_line[1] in ['temp', 'pointer']:
                segments = {
                    'temp': 5,
                    'pointer': 3
                }

                self.put_in_asm_code([
                    f'@{parts_of_line[2]}',
                    'D=A',

                    f'@{segments[parts_of_line[1]]}',
                    'D=D+A',
                    '@R13',
                    'M=D',

                    '@SP',
                    'M=M-1',
                    'A=M',
                    'D=M',

                    '@R13',
                    'A=M',
                    'M=D',
                ])


    def arithmetic_logic_command(self, command):
        if command == 'add':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',
                '@SP',
                'M=M-1',
                'A=M',
                'D=D+M',
                '@SP',
                'A=M',
                'M=D',
                '@SP',
                'M=M+1'
            ])
        if command == 'sub':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',

                '@SP',
                'A=M',
                'M=D',

                '@SP',
                'M=M+1'
            ])
        if command == 'neg':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'M=-M',

                '@SP',
                'M=M+1',
            ])
        if command == 'eq':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',
                
                f'@IS_EQ_{self.global_uuid}',
                'D;JEQ',

                '@SP',
                'A=M',
                'M=0',
                f'@END_EQ_{self.global_uuid}',
                '0;JMP',


                f'(IS_EQ_{self.global_uuid})',
                '@SP',
                'A=M',
                'M=-1',

                f'(END_EQ_{self.global_uuid})',
                '@SP',
                'M=M+1',
            ])
        if command == 'gt':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',
                
                f'@IS_GT_{self.global_uuid}',
                'D;JGT',

                '@SP',
                'A=M',
                'M=0',
                f'@END_GT_{self.global_uuid}',
                '0;JMP',


                f'(IS_GT_{self.global_uuid})',
                '@SP',
                'A=M',
                'M=-1',

                f'(END_GT_{self.global_uuid})',
                '@SP',
                'M=M+1',
            ])
        if command == 'lt':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',
                
                f'@IS_LT_{self.global_uuid}',
                'D;JLT',

                '@SP',
                'A=M',
                'M=0',
                f'@END_LT_{self.global_uuid}',
                '0;JMP',


                f'(IS_LT_{self.global_uuid})',
                '@SP',
                'A=M',
                'M=-1',

                f'(END_LT_{self.global_uuid})',
                '@SP',
                'M=M+1',
            ])
        if command == 'and':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=D&M',

                '@SP',
                'A=M',
                'M=D',
                
                '@SP',
                'M=M+1',
            ])
        if command == 'or':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=D|M',

                '@SP',
                'A=M',
                'M=D',
                
                '@SP',
                'M=M+1',
            ])
        if command == 'not':
            self.put_in_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'M=!M',

                '@SP',
                'M=M+1',
            ])





def main():
    filename = sys.argv[1]
    vm = VirtualMachine(filename)
    vm.open_file_and_read()
    vm.parse_vm_code()
    vm.write_asm_file()


main()