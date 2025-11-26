import sys

class VirtualMachine:

    def __init__(self, vm_filename):
        self.vm_filename = vm_filename
        self.vm_code = []
        self.asm_code = []


    def open_file_and_read(self):
        file = open(self.vm_filename, 'r')
        self.vm_code = [line.strip() for line in  file.readlines()]
        file.close()

    def put_in_asm_code(self, asm_code):
        for line in asm_code:
            self.asm_code.append(line)


    def parse_vm_code(self):
        for line in self.vm_code:
            parts_of_line = line.split(' ')
            if len(parts_of_line) == 3:
                pass
            if len(parts_of_line) == 1:
                pass

    




def main():
    filename = sys.argv[1]
    vm = VirtualMachine(filename)
    vm.open_file_and_read()
    vm.parse_vm_code()


main()