import sys

class assambler_translator:

    def __init__(self, asm_code):
        self.asm_code = asm_code
        self.hack_binary_code = []
        self.table_comp = {
            # a = 0
            '0':   '0101010',
            '1':   '0111111',
            '-1':  '0111010',
            'D':   '0001100',
            'A':   '0110000',
            '!D':  '0001101',
            '!A':  '0110001',
            '-D':  '0001111',
            '-A':  '0110011',
            'D+1': '0011111',
            'A+1': '0110111',
            'D-1': '0001110',
            'A-1': '0110010',
            'D+A': '0000010',
            'D-A': '0010011',
            'A-D': '0000111',
            'D&A': '0000000',
            'D|A': '0010101',
            # a = 1
            'M':   '1110000',
            '!M':  '1110001',
            '-M':  '1110011',
            'M+1': '1110111',
            'M-1': '1110010',
            'D+M': '1000010',
            'D-M': '1010011',
            'M-D': '1000111',
            'D&M': '1000000',
            'D|M': '1010101',
        }

        self.table_dest = {
            '':    '000',
            'M':   '001',
            'D':   '010',
            'MD':  '011',
            'A':   '100',
            'AM':  '101',
            'AD':  '110',
            'AMD': '111',
        }

        self.table_jump = {
            '':    '000',
            'JGT': '001',
            'JEQ': '010',
            'JGE': '011',
            'JLT': '100',
            'JNE': '101',
            'JLE': '110',
            'JMP': '111',
        }

    def translate(self):
        # запоминанеие меток
        for line in self.asm_code:
            print(line)

        for line in self.asm_code:
            if line.startswith('@'):
                # A instruction
                value = line.split('@')[1]
                value = '0' + str(format(int(value), "015b"))
                self.hack_binary_code.append(value)
            else:
                # С instruction
                dest = ''
                comp = ''
                jump = ''
                # dest=comp;jump
                if '=' in line:
                    pass






def main():
    file_path = sys.argv[1]
    print('file_path', file_path)


    f = open(file_path, 'r')
    raw_asm_code = f.readlines()
    f.close()


    asm_code = []

    for line in raw_asm_code:
        if line.startswith('//'):
            continue

        if '//' in line:
            line = line.split('//')[0]
            pass
        pass

        line = line.strip()

        if line == '':
            continue

        asm_code.append(line)

    at = assambler_translator(asm_code)
    at.translate()

main()