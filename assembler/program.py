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

        self.reserved_labels = {
            'SP':     0,
            'LCL':    1,
            'ARG':    2,
            'THIS':   3,
            'THAT':   4,
            'R0':     0,
            'R1':     1,
            'R2':     2,
            'R3':     3,
            'R4':     4,
            'R5':     5,
            'R6':     6,
            'R7':     7,
            'R8':     8,
            'R9':     9,
            'R10':    10,
            'R11':    11,
            'R12':    12,
            'R13':    13,
            'R14':    14,
            'R15':    15,
            'SCREEN': 16384,
            'KBD':    24576,
        }
        self.next_var = 16
        self.vars = {}


    def translate(self):
        # запоминанеие меток
        i = 0
        labels = {}
        for line in self.asm_code:
            if line.startswith('('):
                labels[line.replace('(', '').replace(')', '')] = i
            else:
                i = i + 1
            pass

        print(labels)

        handled_asm_code = []
        # заменяем метки 
        for line in self.asm_code:
            if line.startswith('('):
                continue
    
            if line.startswith('@'):
                a_instr = line.replace('@', '')

                if a_instr.isdigit():
                    handled_asm_code.append('@' + str(a_instr))
                    continue

                if a_instr in labels:
                    value = labels[a_instr]
                    handled_asm_code.append('@' + str(value))
                elif a_instr in self.reserved_labels:
                    value = self.reserved_labels[a_instr]
                    handled_asm_code.append('@' + str(value))
                else:
                    if a_instr in self.vars:
                        var_num = self.vars[a_instr]
                        handled_asm_code.append('@' + str(var_num))
                    else:
                        self.vars[a_instr] = self.next_var
                        handled_asm_code.append('@' + str(self.next_var))
                        self.next_var += 1
            else:
                handled_asm_code.append(line)

        self.handled_asm_code = handled_asm_code

        for line in handled_asm_code:
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

                if ('=' in line) and (';' not in line):
                    # dest=comp
                    c_instr_parts = line.split('=')
                    dest = c_instr_parts[0]
                    comp = c_instr_parts[1]
                elif (';' in line) and ('=' not in line):
                    # comp;jump
                    c_instr_parts = line.split(';')
                    comp = c_instr_parts[0]
                    jump = c_instr_parts[1]
                elif ('=' in line) and (';' in line):
                    # dest=comp;jump
                    c_instr_parts = line.split('=')
                    dest = c_instr_parts[0]
                    other_part = c_instr_parts[1].split(';')
                    comp = other_part[0]
                    jump = other_part[1]

                
                if comp == '':
                    print('comp=>', comp, line)


                self.hack_binary_code.append('111' + self.table_comp[comp] + self.table_dest[dest] + self.table_jump[jump])

        return self.hack_binary_code





def main():
    file_path = sys.argv[1]

    print(file_path)

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

    print(asm_code)

    at = assambler_translator(asm_code)
    asm_code = at.translate()


    new_file_name = file_path.replace('.asm', '.hack')
    f = open(new_file_name, 'w+')
    f.writelines(f"{line}\n" for line in asm_code)
    f.close()


    new_file_name = file_path.replace('.asm', '.txt')
    f = open(new_file_name, 'w+')
    f.writelines(f"{line}\n" for line in at.handled_asm_code)
    f.close() 

main()