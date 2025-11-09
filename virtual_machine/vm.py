import sys
import os

class StackMachine:
    def __init__(self):
        # Сегменты памяти
        self.stack = []        # Основной стек
        self.local_seg = {}    # Локальный сегмент (поиндексный)
        self.argument_seg = {} # Аргумент сегмент (поиндексный)
        self.this_seg = {}     # This сегмент
        self.that_seg = {}     # That сегмент
        self.temp_seg = {}     # Temp сегмент (индексы 0-7)
        self.static_seg = {}   # Static сегмент
        self.pointer_seg = {}  # Pointer сегмент (индексы 0-1)
        
        # Регистры
        self.sp = 0           # Stack pointer
        self.lcl = 0          # Local pointer
        self.arg = 0          # Argument pointer
        self.this = 0         # This pointer
        self.that = 0         # That pointer
        
        # Управление выполнением
        self.program = []      # Исходный код VM
        self.pc = 0           # Program counter
        self.labels = {}       # Метки для goto
        self.functions = {}    # Функции
        self.call_stack = []   # Стек вызовов (для return)
        
        # Инициализация temp сегмента
        for i in range(8):
            self.temp_seg[i] = 0
    
    def load_program(self, vm_code):
        """Загружает код VM и парсит его"""
        lines = []
        for line in vm_code.split('\n'):
            # Удаляем комментарии и лишние пробелы
            line = line.split('//')[0].strip()
            if line:
                lines.append(line)
        self.program = lines
        self._parse_labels_and_functions()
    
    def _parse_labels_and_functions(self):
        """Предварительно парсит метки и функции"""
        current_function = None
        
        for i, line in enumerate(self.program):
            parts = line.split()
            if not parts:
                continue
                
            if parts[0] == "function":
                func_name = parts[1]
                self.functions[func_name] = i
                current_function = func_name
            elif parts[0] == "label":
                label_name = parts[1]
                # Метки уникальны в пределах функции
                full_label = f"{current_function}${label_name}" if current_function else label_name
                self.labels[full_label] = i
    
    def run(self):
        """Выполняет загруженную программу"""
        print("=== Запуск виртуальной машины ===")
        
        while self.pc < len(self.program):
            line = self.program[self.pc]
            self._execute_instruction(line)
            self.pc += 1
            
            # Отладочный вывод состояния
            if "push" in line or "pop" in line or "call" in line or "return" in line:
                print(f"PC:{self.pc:3d} | {line:20} | SP:{self.sp:3d} | Stack: {self.stack}")
    
    def _execute_instruction(self, instruction):
        """Выполняет одну инструкцию VM"""
        parts = instruction.split()
        if not parts:
            return
            
        cmd = parts[0]
        
        # Арифметические команды
        if cmd == "add":
            self._arithmetic_add()
        elif cmd == "sub":
            self._arithmetic_sub()
        elif cmd == "neg":
            self._arithmetic_neg()
        elif cmd == "eq":
            self._arithmetic_eq()
        elif cmd == "gt":
            self._arithmetic_gt()
        elif cmd == "lt":
            self._arithmetic_lt()
        elif cmd == "and":
            self._arithmetic_and()
        elif cmd == "or":
            self._arithmetic_or()
        elif cmd == "not":
            self._arithmetic_not()
        
        # Команды доступа к памяти
        elif cmd == "push":
            segment = parts[1]
            index = int(parts[2])
            self._push(segment, index)
        elif cmd == "pop":
            segment = parts[1]
            index = int(parts[2])
            self._pop(segment, index)
        
        # Команды управления программой
        elif cmd == "label":
            # Метки уже обработаны при загрузке
            pass
        elif cmd == "goto":
            label = parts[1]
            self._goto(label)
        elif cmd == "if-goto":
            label = parts[1]
            self._if_goto(label)
        elif cmd == "function":
            func_name = parts[1]
            n_locals = int(parts[2])
            self._function(func_name, n_locals)
        elif cmd == "call":
            func_name = parts[1]
            n_args = int(parts[2])
            self._call(func_name, n_args)
        elif cmd == "return":
            self._return()
    
    def _arithmetic_add(self):
        """Сложение: x + y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для сложения")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(x + y)
        self.sp -= 1
    
    def _arithmetic_sub(self):
        """Вычитание: x - y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для вычитания")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(x - y)
        self.sp -= 1
    
    def _arithmetic_neg(self):
        """Отрицание: -y"""
        if len(self.stack) < 1:
            raise Exception("Недостаточно элементов в стеке для отрицания")
        y = self.stack.pop()
        self.stack.append(-y)
    
    def _arithmetic_eq(self):
        """Равенство: x == y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для сравнения")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(1 if x == y else 0)
        self.sp -= 1
    
    def _arithmetic_gt(self):
        """Больше: x > y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для сравнения")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(1 if x > y else 0)
        self.sp -= 1
    
    def _arithmetic_lt(self):
        """Меньше: x < y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для сравнения")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(1 if x < y else 0)
        self.sp -= 1
    
    def _arithmetic_and(self):
        """Логическое И: x & y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для AND")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(x & y)
        self.sp -= 1
    
    def _arithmetic_or(self):
        """Логическое ИЛИ: x | y"""
        if len(self.stack) < 2:
            raise Exception("Недостаточно элементов в стеке для OR")
        y = self.stack.pop()
        x = self.stack.pop()
        self.stack.append(x | y)
        self.sp -= 1
    
    def _arithmetic_not(self):
        """Логическое НЕ: !y"""
        if len(self.stack) < 1:
            raise Exception("Недостаточно элементов в стеке для NOT")
        y = self.stack.pop()
        self.stack.append(0 if y != 0 else 1)
    
    def _push(self, segment, index):
        """Команда push - помещает значение в стек"""
        value = 0
        
        if segment == "constant":
            value = index
        elif segment == "local":
            value = self.local_seg.get(self.lcl + index, 0)
        elif segment == "argument":
            value = self.argument_seg.get(self.arg + index, 0)
        elif segment == "this":
            value = self.this_seg.get(self.this + index, 0)
        elif segment == "that":
            value = self.that_seg.get(self.that + index, 0)
        elif segment == "temp":
            if 0 <= index < 8:
                value = self.temp_seg.get(index, 0)
            else:
                raise Exception(f"Недопустимый индекс temp сегмента: {index}")
        elif segment == "static":
            value = self.static_seg.get(index, 0)
        elif segment == "pointer":
            if index == 0:
                value = self.this
            elif index == 1:
                value = self.that
            else:
                raise Exception(f"Недопустимый индекс pointer сегмента: {index}")
        else:
            raise Exception(f"Неизвестный сегмент: {segment}")
        
        self.stack.append(value)
        self.sp += 1
    
    def _pop(self, segment, index):
        """Команда pop - извлекает значение из стека"""
        if len(self.stack) < 1:
            raise Exception("Стек пуст для операции pop")
        
        value = self.stack.pop()
        self.sp -= 1
        
        if segment == "local":
            self.local_seg[self.lcl + index] = value
        elif segment == "argument":
            self.argument_seg[self.arg + index] = value
        elif segment == "this":
            self.this_seg[self.this + index] = value
        elif segment == "that":
            self.that_seg[self.that + index] = value
        elif segment == "temp":
            if 0 <= index < 8:
                self.temp_seg[index] = value
            else:
                raise Exception(f"Недопустимый индекс temp сегмента: {index}")
        elif segment == "static":
            self.static_seg[index] = value
        elif segment == "pointer":
            if index == 0:
                self.this = value
            elif index == 1:
                self.that = value
            else:
                raise Exception(f"Недопустимый индекс pointer сегмента: {index}")
        else:
            raise Exception(f"Неизвестный сегмент: {segment}")
    
    def _goto(self, label):
        """Безусловный переход"""
        current_function = self._get_current_function()
        full_label = f"{current_function}${label}" if current_function else label
        
        if full_label in self.labels:
            self.pc = self.labels[full_label] - 1  # -1 потому что после выполнения pc увеличится
        else:
            raise Exception(f"Метка не найдена: {label}")
    
    def _if_goto(self, label):
        """Условный переход (если вершина стека != 0)"""
        if len(self.stack) < 1:
            raise Exception("Недостаточно элементов в стеке для if-goto")
        
        condition = self.stack.pop()
        self.sp -= 1
        
        if condition != 0:
            self._goto(label)
    
    def _function(self, func_name, n_locals):
        """Объявление функции"""
        # Инициализация локальных переменных нулями
        for i in range(n_locals):
            self.local_seg[self.lcl + i] = 0
    
    def _call(self, func_name, n_args):
        """Вызов функции"""
        # Сохраняем возвращаемый адрес
        return_address = self.pc + 1
        
        # Сохраняем состояние вызывающей функции
        self.call_stack.append({
            'return_address': return_address,
            'local': self.lcl,
            'argument': self.arg,
            'this': self.this,
            'that': self.that
        })
        
        # Устанавливаем новое значение LCL (текущий SP)
        self.lcl = self.sp
        
        # Устанавливаем новое значение ARG (SP - n_args - 5)
        self.arg = self.sp - n_args - 5
        
        # Переходим к функции
        if func_name in self.functions:
            self.pc = self.functions[func_name] - 1  # -1 потому что после выполнения pc увеличится
        else:
            raise Exception(f"Функция не найдена: {func_name}")
    
    def _return(self):
        """Возврат из функции"""
        if not self.call_stack:
            raise Exception("Нет активных вызовов функций")
        
        # Восстанавливаем состояние вызывающей функции
        state = self.call_stack.pop()
        
        # Возвращаемое значение помещаем в ARG[0]
        return_value = self.stack.pop() if self.stack else 0
        self.argument_seg[state['argument']] = return_value
        
        # Восстанавливаем указатели сегментов
        self.lcl = state['local']
        self.arg = state['argument']
        self.this = state['this']
        self.that = state['that']
        
        # Переходим по возвращаемому адресу
        self.pc = state['return_address'] - 1  # -1 потому что после выполнения pc увеличится
    
    def _get_current_function(self):
        """Определяет текущую выполняемую функцию"""
        for func_name, line_num in self.functions.items():
            if line_num <= self.pc:
                # Ищем самую "близкую" функцию перед текущей инструкцией
                current_func = func_name
        return current_func if 'current_func' in locals() else None


def main():
    if len(sys.argv) != 2:
        print("Использование: python vm.py <файл.vm>")
        return
    
    vm_file = sys.argv[1]
    
    if not os.path.exists(vm_file):
        print(f"Файл {vm_file} не найден")
        return
    
    # Читаем VM код из файла
    with open(vm_file, 'r') as f:
        vm_code = f.read()
    
    # Создаем и запускаем виртуальную машину
    vm = StackMachine()
    vm.load_program(vm_code)
    vm.run()

if __name__ == "__main__":
    main()