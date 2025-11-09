import sys
import re

class HackAssembler:
    def __init__(self):
        # Предопределенные символы
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

    def first_pass(self, lines):
        print(lines)
        """Первый проход: обработка меток (Label)"""
        rom_address = 0
        clean_lines = []
        
        for line in lines:
            # Удаление комментариев и лишних пробелов
            line = re.sub(r'//.*', '', line).strip()
            if not line:
                continue
                
            # Обработка меток (LABEL)
            if line.startswith('(') and line.endswith(')'):
                label = line[1:-1]
                self.symbol_table[label] = rom_address
            else:
                clean_lines.append(line)
                rom_address += 1
                
        return clean_lines

    def second_pass(self, lines):
        """Второй проход: трансляция в машинный код"""
        machine_code = []
        
        for line in lines:
            # A-инструкция
            if line.startswith('@'):
                instruction = self.translate_a_instruction(line[1:])
            # C-инструкция
            else:
                instruction = self.translate_c_instruction(line)
            
            machine_code.append(instruction)
            
        return machine_code

    def translate_a_instruction(self, symbol):
        """Трансляция A-инструкции"""
        # Если это число
        if symbol.isdigit():
            address = int(symbol)
        # Если это символ
        else:
            if symbol not in self.symbol_table:
                self.symbol_table[symbol] = self.next_variable_address
                self.next_variable_address += 1
            address = self.symbol_table[symbol]
        
        # Преобразование в 16-битное двоичное число
        return format(address, '016b')

    def translate_c_instruction(self, instruction):
        """Трансляция C-инструкции"""
        # Разделяем на dest, comp, jump
        dest = 'null'
        comp = instruction
        jump = 'null'
        
        # Проверяем наличие jump
        if ';' in instruction:
            parts = instruction.split(';')
            comp = parts[0]
            jump = parts[1]
        
        # Проверяем наличие dest
        if '=' in comp:
            parts = comp.split('=')
            dest = parts[0]
            comp = parts[1]
        
        # Получаем бинарные коды
        comp_bits = self.comp_table.get(comp)
        dest_bits = self.dest_table.get(dest)
        jump_bits = self.jump_table.get(jump)
        
        if not all([comp_bits, dest_bits, jump_bits]):
            raise ValueError(f"Invalid C-instruction: {instruction}")
        
        return '111' + comp_bits + dest_bits + jump_bits

    def assemble(self, asm_code):
        """Основной метод ассемблирования"""
        lines = asm_code.split('\n')
        
        # Первый проход - обработка меток
        clean_lines = self.first_pass(lines)
        
        # Второй проход - трансляция
        machine_code = self.second_pass(clean_lines)
        
        return machine_code

def main():
    if len(sys.argv) != 2:
        print("Использование: python hack_assembler.py input.asm")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = input_file.replace('.asm', '.hack')
    
    try:
        # Чтение исходного кода
        with open(input_file, 'r') as f:
            asm_code = f.read()
        
        # Ассемблирование
        assembler = HackAssembler()
        machine_code = assembler.assemble(asm_code)
        
        # Запись машинного кода
        with open(output_file, 'w') as f:
            for instruction in machine_code:
                f.write(instruction + '\n')
        
        print(f"Успешно скомпилировано: {output_file}")
        
    except FileNotFoundError:
        print(f"Файл {input_file} не найден")
    except Exception as e:
        print(f"Ошибка ассемблирования: {e}")

if __name__ == "__main__":
    main()