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
            None: '000',
            'M': '001',
            'D': '010',
            'MD': '011',
            'A': '100',
            'AM': '101',
            'AD': '110',
            'AMD': '111'
        }

        self.jump_keys = {
            None: '000',
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

        self.all_labels = []
        self.free_memory_cell = 16

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
                self.all_labels.append(line.strip('()\n'))

        file.close()

        self.asm_code = clean_code


    def first_pass(self):
        # проход по коду запсываем метки и адреса на которые они указывают в таблицу символов
        for instruction_idx in range(len(self.asm_code)):
            # print('instruction', instruction_idx)
            if '(' in self.asm_code[instruction_idx]['code'] and ')' in self.asm_code[instruction_idx]['code']:
                label_name = self.asm_code[instruction_idx]['code'].strip('()')
                if label_name not in self.symbol_table:
                    j = 1
                    while self.asm_code[instruction_idx + j]['address'] == 'label':
                        j = j + 1

                    self.symbol_table[label_name] = self.asm_code[instruction_idx+j]['address']



    def second_pass(self):
        # проход по коду записываем переменные которые не являются адресами меток
        for line_code in self.asm_code:
            if '@' in line_code['code']:
                a_instr = line_code['code'].strip('@')
                if not a_instr.isdigit():
                    if a_instr not in self.all_labels and a_instr not in self.symbol_table:
                        self.symbol_table[a_instr] = self.free_memory_cell
                        self.free_memory_cell+=1


    def third_pass(self):
        # собираем бинарный код заменяем теперь @VARIABLE_OR_LABEL на то что в таблице символов
        binary_code = []
        for line_code in self.asm_code:
            if line_code['address'] == 'label':
                continue
            if '@' in line_code['code']:
                # a instr
                a_instr = line_code['code'].strip('@')
                if a_instr in self.symbol_table:
                    value = self.symbol_table[a_instr]
                    print('value', value)
                    binary_code.append(self.to_binary(value))
                else:
                    if a_instr.isdigit():
                        binary_code.append(self.to_binary(a_instr))
            else:
                # c instr
                # dest=comp;jump
                dest = None
                comp = None
                jump = None

                instruction_part = line_code['code'].split('=')
                if len(instruction_part) == 2:
                    dest = instruction_part[0]

                    if ';' in instruction_part[1]:
                        comp, jump = instruction_part[1].split(';')
                    else:
                        comp = instruction_part[1]
                if len(instruction_part) == 1:
                    if ';' in instruction_part[0]:
                        comp, jump = instruction_part[0].split(';')
                    else:
                        comp = instruction_part[0]
                print(dest, comp, jump, line_code['code'])
                binary_code.append(f'111{self.comp_keys[comp]}{self.dest_keys[dest]}{self.jump_keys[jump]}')
        self.binary_code = binary_code


    def write_into_file(self, filename):
        file = open('./binary/' + filename, 'w+')
        for line in self.binary_code:
            file.write(line + '\n')
        file.close()

    def to_binary(self, value):
        return bin(int(value))[2:].zfill(16)




def main():
    assembler = Assembler()
    assembler.open_file_get_code('code.asm')
    assembler.first_pass()
    # print(assembler.symbol_table)
    assembler.second_pass()
    # print(assembler.symbol_table)

    assembler.third_pass()
    assembler.write_into_file('my_code.hack')



main()