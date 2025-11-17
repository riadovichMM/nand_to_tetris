class VM:

    def __init__(self):
        self.vm_code = []
        self.asm_code = []
        pass

    def open_file_and_get_code(self):
        file = open('./vm_code/code.vm', 'r+')
        self.vm_code = [line.strip() for line in file.readlines()]
        file.close()
        print(self.vm_code)

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
                self.put_to_asm_code([f'@{line_code_part[2]}', 'D=A', '@SP', 'A=M', 'M=D', '@SP', 'M=M+1'])
            


    def arithmetic_logic(self, command):
        if command == 'add':
            self.put_to_asm_code([''])



def main():
    vm = VM()
    vm.open_file_and_get_code()
    vm.analys()
    print(vm.asm_code)



main()