import re

class Assambler:

    def __init__(self):
        self.symbol_table = {
            'SP': 0, 'LCL': 1, 'ARG': 2, 'THIS': 3, 'THAT': 4,
            'R0': 0, 'R1': 1, 'R2': 2, 'R3': 3, 'R4': 4, 'R5': 5,
            'R6': 6, 'R7': 7, 'R8': 8, 'R9': 9, 'R10': 10,
            'R11': 11, 'R12': 12, 'R13': 13, 'R14': 14, 'R15': 15,
            'SCREEN': 16384, 'KBD': 24576
        }
        
        # Таблицы для C-инструкций
        self.comp_table = {
            '0': '0101010', '1': '0111111', '-1': '0111010',
            'D': '0001100', 'A': '0110000', '!D': '0001101',
            '!A': '0110001', '-D': '0001111', '-A': '0110011',
            'D+1': '0011111', 'A+1': '0110111', 'D-1': '0001110',
            'A-1': '0110010', 'D+A': '0000010', 'D-A': '0010011',
            'A-D': '0000111', 'D&A': '0000000', 'D|A': '0010101',
            'M': '1110000', '!M': '1110001', '-M': '1110011',
            'M+1': '1110111', 'M-1': '1110010', 'D+M': '1000010',
            'D-M': '1010011', 'M-D': '1000111', 'D&M': '1000000',
            'D|M': '1010101'
        }
        
        self.dest_table = {
            'null': '000', 'M': '001', 'D': '010', 'MD': '011',
            'A': '100', 'AM': '101', 'AD': '110', 'AMD': '111'
        }
        
        self.jump_table = {
            'null': '000', 'JGT': '001', 'JEQ': '010', 'JGE': '011',
            'JLT': '100', 'JNE': '101', 'JLE': '110', 'JMP': '111'
        }

        self.next_variable_address = 16


    def first_pass_labels(self, code):
        rom_address = 0
        for line in code:
            if line.startswith('(') and line.endswith(')'):
                label = line[1:-1]
                self.symbol_table[label] = rom_address
            else:
                rom_address += 1

    def second_pass(self, code):
        pass


def main():
    filename = 'max.asm'
    code = []
    file = open('./asm_code/' + filename, 'r')

    for line in file:
        line = re.sub(r'//.*', '', line).strip()
        if line:
            code.append(line)

    print(code)
    file.close()


    assembler = Assambler()
    assembler.first_pass_labels(code)

main()