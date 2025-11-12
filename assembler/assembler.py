class Assembler:

    def __init__(self):
        self.comp_keys = {
            '0': '0101010',
            '1': '0111111',
            '-1': '0111010',
            'D': '0001100',
            'A': '0110000',
            '!D': '0001101',
            '!A': '0110001',
            '-D': '0001111',
            '-A': '0110011',
            'D+1': '0011111',
            'A+1': '0110111',
            'D-1': '0001110',
            'A-1': '0110010',
            'D+A': '0000010',
            'D-A': '0010011',
            'A-D': '0000111',
            'D&A': '0000000',
            'D|A': '0010101',
            'M': '1110000',
            '!M': '1110001',
            '-M': '1110011',
            'M+1': '1110111',
            'M-1': '1110010',
            'D+M': '1000010',
            'D-M': '1010011',
            'M-D': '1000111',
            'D&M': '1000000',
            'D|M': '1010101'
        }

        self.dest_keys = {
            '': '000',
            'M': '001',
            'D': '010',
            'MD': '011',
            'A': '100',
            'AM': '101',
            'AD': '110',
            'AMD': '111'
        }

        self.jump_keys = {
            '': '000',
            'JGT': '001',
            'JEQ': '010',
            'JGE': '011',
            'JLT': '100',
            'JNE': '101',
            'JLE': '110',
            'JMP': '111'
        }

        self.symbol_table = {
            'SP': 0,
            'LCL': 1,
            'ARG': 2,
            'THIS': 3,
            'THAT': 4,
            'R0': 0,
            'R1': 1,
            'R2': 2,
            'R3': 3,
            'R4': 4,
            'R5': 5,
            'R6': 6,
            'R7': 7,
            'R8': 8,
            'R9': 9,
            'R10': 10,
            'R11': 11,
            'R12': 12,
            'R13': 13,
            'R14': 14,
            'R15': 15,
            'SCREEN': 16384,
            'KBD': 24576
        }

    def open_file_get_code(self, filename):
        file = open('./asm_code/' + filename, 'r')
        self.asm_code = file.readlines()
        clean_code = []

        address_instruction = 0
        for line in self.asm_code:
            if '//' in line:
                continue
            
            if '(' not in line:
                clean_code.append({'address': address_instruction, 'code': line.strip()})
                address_instruction += 1
            else:
                clean_code.append({'address': 'label', 'code': line.strip()})

        file.close()

        self.asm_code = clean_code


    def first_pass(self):
        for instruction_idx in range(len(self.asm_code)):
            print('instruction', instruction_idx)
            pass
        pass


    def second_pass(self):
        pass



def main():
    assembler = Assembler()
    assembler.open_file_get_code('code.asm')
    assembler.first_pass()



main()