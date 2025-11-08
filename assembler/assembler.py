symbol_table = {
    # Виртуальные регистры R0-R15
    'R0': 0,  'R1': 1,  'R2': 2,  'R3': 3,
    'R4': 4,  'R5': 5,  'R6': 6,  'R7': 7,
    'R8': 8,  'R9': 9,  'R10': 10, 'R11': 11,
    'R12': 12, 'R13': 13, 'R14': 14, 'R15': 15,
    
    # Указатели виртуальной машины
    'SP': 0,    # Stack Pointer (совпадает с R0)
    'LCL': 1,   # Local Pointer (совпадает с R1)
    'ARG': 2,   # Argument Pointer (совпадает с R2)
    'THIS': 3,  # This Pointer (совпадает с R3)
    'THAT': 4,  # That Pointer (совпадает с R4)
    
    # Порты ввода/вывода
    'SCREEN': 16384,  # Базовый адрес экрана
    'KBD': 24576      # Адрес клавиатуры
}

free_variable_cell = 16

comp_keys = {
    # a=0
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
    
    # a=1 (работа с памятью через M)
    'M':   '1110000',
    '!M':  '1110001',
    '-M':  '1110011',
    'M+1': '1110111',
    'M-1': '1110010',
    'D+M': '1000010',
    'D-M': '1010011',
    'M-D': '1000111',
    'D&M': '1000000',
    'D|M': '1010101'
}


dest_keys = {
    None: '000',  # Результат не сохраняется
    'M':    '001',  # Только в память (RAM[A])
    'D':    '010',  # Только в регистр D
    'MD':   '011',  # В D и память
    'A':    '100',  # Только в регистр A
    'AM':   '101',  # В A и память
    'AD':   '110',  # В A и D
    'AMD':  '111'   # Во все три места (A, D, M)
}


jump_keys = {
    None: '000',  # Нет прыжка
    'JGT':  '001',  # Прыжок если comp > 0
    'JEQ':  '010',  # Прыжок если comp == 0
    'JGE':  '011',  # Прыжок если comp >= 0
    'JLT':  '100',  # Прыжок если comp < 0
    'JNE':  '101',  # Прыжок если comp != 0
    'JLE':  '110',  # Прыжок если comp <= 0
    'JMP':  '111'   # Безусловный прыжок
}



def open_file_and_get_code(filename):
    asm_code = []

    file = open(filename, 'r')
    for line in file:
        if '//' not in line and len(line) != 0 and line != '\n':
            asm_code.append(line.replace(' ', '').replace('\n', ''))
    file.close()

    return asm_code


def process_code(asm_code):
    binary_code = []
    print(asm_code)
    for instruction in asm_code:
        if instruction.startswith('@'):
            # A instr
            # убираем @ и смотрим начинается ли инструкция с числа или с символа
            # если с символа то это либо зарезервированная переменная либо переменной которой пока не существет в таблице символов
            # устанавливаем
            # если это число то переводим его в двоичное 

            instruction = instruction[1:]
            if instruction[0].isdigit():
                binary = bin(int(instruction))[2:]  # Получаем двоичное представление и убираем '0b'
                binary = binary.zfill(16)
                binary_code.append(binary)
            else:
                pass
        else:
            # C instr
            dest = None
            comp = None
            jump = None
            #dest=comp;jump
            instruction_parts = instruction.split('=')
            if len(instruction_parts) == 1:
                if ';' in instruction_parts[0]:
                    comp, jump = instruction_parts[0].split(';')
                else:
                    comp = instruction_parts[0]
            else:
                dest = instruction_parts[0]
                if ';' in instruction_parts[1]:
                    comp, jump = instruction_parts[1].split(';')
                else:
                    comp = instruction_parts[1]
            binary_code.append(f'111{comp_keys[comp]}{dest_keys[dest]}{jump_keys[jump]}')

    return binary_code


def write_binary_file(filename, binary_code):
    file = open('./my/my_' + filename.split('.')[0] + '.hack', 'w+')
    for instruction in binary_code:
        file.write(str(instruction) + '\n')
    file.close()



def main():
    # filename = input("input your filename: ")
    filename = 'add.asm'
    asm_code = open_file_and_get_code(filename)
    binary_code = process_code(asm_code)
    print(binary_code)
    write_binary_file(filename, binary_code)



main()


