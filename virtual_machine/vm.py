class VM:

    def __init__(self):
        self.vm_code = []
        self.asm_code = []
        self.global_uuid_command = 0

    def open_file_and_get_code(self, filename):
        self.filename = filename.split('.')[0]
        file = open('./vm_code/' + self.filename + '.vm', 'r+')
        self.vm_code = [line.strip() for line in file.readlines()]
        file.close()

    def put_to_asm_code(self, code):
        for line in code:
            self.asm_code.append(line)


    def analys(self):
        for line in self.vm_code:
            line_code_parts = line.split(' ')
            if len(line_code_parts) == 3:
                if line_code_parts[0] == 'push' or line_code_parts[0] == 'pop':
                    self.push_pop_segment(line)
            if len(line_code_parts) == 1:
                if line_code_parts[0] in ['add', 'sub', 'neg', 'eq', 'gt', 'lt', 'and', 'or', 'not']:
                    self.arithmetic_logic(line_code_parts[0])


    def push_pop_segment(self, line):
        line_code_part = line.split(' ')
        if line_code_part[0] == 'push':
            if line_code_part[1] == 'constant':
                self.put_to_asm_code([
                    f'@{line_code_part[2]}',
                    'D=A',
                    '@SP',
                    'A=M',
                    'M=D',
                    '@SP',
                    'M=M+1'
                ])

            if line_code_part[1] == 'static':
                self.put_to_asm_code([
                    f'@{self.filename}.{line_code_part[2]}',
                    'D=M',
                    '@SP',
                    'A=M',
                    'M=D',
                    '@SP',
                    'M=M+1'
                ])

        if line_code_part[0] == 'pop':
            if line_code_part[1] == 'static':
                self.put_to_asm_code([
                    '@SP',
                    'M=M-1',
                    'A=M',
                    'D=M',
                    f'@{self.filename}.{line_code_part[2]}',
                    'M=D',
                ])


    def arithmetic_logic(self, command):
        if command == 'add':
            self.put_to_asm_code(['@SP', 'M=M-1', 'A=M', 'D=M', '@SP', 'M=M-1', 'A=M', 'D=D+M', 'M=D', '@SP', 'M=M+1'])
        if command == 'sub':
            self.put_to_asm_code(['@SP', 'M=M-1', 'A=M', 'D=M', '@SP', 'M=M-1', 'A=M', 'D=M-D', 'M=D', '@SP', 'M=M+1'])
        if command == 'neg':
            self.put_to_asm_code(['@SP', 'M=M-1', 'A=M', 'M=-M', '@SP', 'M=M+1'])
        if command == 'gt':
            self.put_to_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',

                f'@TRUE_GT_X_{self.global_uuid_command}',
                'D;JGT',

                '@SP',
                'A=M',
                'M=0',

                f'@END_GT_X_{self.global_uuid_command}',
                '0;JMP',

                f'(TRUE_GT_X_{self.global_uuid_command})',
                '@SP',
                'A=M',
                'M=-1',

                f'(END_GT_X_{self.global_uuid_command})',
                '@SP',
                'M=M+1'
            ])
        if command == 'lt':
            # тут возможно ошибка 
            self.put_to_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',

                f'@TRUE_LT_X_{self.global_uuid_command}',
                'D;JLT',

                '@SP',
                'A=M',
                'M=0',

                f'@END_LT_X_{self.global_uuid_command}',
                '0;JMP',

                f'(TRUE_LT_X_{self.global_uuid_command})',
                '@SP',
                'A=M',
                'M=-1',

                f'(END_LT_X_{self.global_uuid_command})',
                '@SP',
                'M=M+1',
            ])
        if command == 'and':
            self.put_to_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=D&M',
                'M=D',

                '@SP',
                'M=M+1',
            ])
        if command == 'or':
            self.put_to_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=D|M',
                'M=D',

                '@SP',
                'M=M+1',
            ])

        if command == 'not':
            self.put_to_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'M=!M',
                '@SP',
                'M=M+1',
            ])

        if command == 'eq':
            self.put_to_asm_code([
                '@SP',
                'M=M-1',
                'A=M',
                'D=M',

                '@SP',
                'M=M-1',
                'A=M',
                'D=M-D',

                f'@TRUE_EQ_X_{self.global_uuid_command}',
                'D;JEQ',

                '@SP',
                'A=M',
                'M=0',

                f'@END_EQ_X_{self.global_uuid_command}',
                '0;JMP',

                f'(TRUE_EQ_X_{self.global_uuid_command})',
                '@SP',
                'A=M',
                'M=-1',

                f'(END_EQ_X_{self.global_uuid_command})',
                '@SP',
                'M=M+1',
            ])
        self.global_uuid_command+=1




    def write_to_asm_file(self):
        file = open('./asm_code/' + self.filename + '.asm', 'w+')
        for line in self.asm_code:
            file.write(line + '\n')
        file.close()



def main():
    vm = VM()
    vm.open_file_and_get_code('code.vm')
    vm.analys()
    vm.write_to_asm_file()
    print('finish')



main()