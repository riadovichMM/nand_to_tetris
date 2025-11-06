def binary_to_hex_fixed_width(input_file, output_file):
    """
    Читает файл с двоичными числами, преобразует их в шестнадцатеричные
    и записывает результат в новый файл с фиксированной шириной 4 символа.
    
    Args:
        input_file (str): путь к входному файлу с двоичными числами
        output_file (str): путь к выходному файлу с шестнадцатеричными числами
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as infile, \
             open(output_file, 'w', encoding='utf-8') as outfile:
            
            for line_num, line in enumerate(infile, 1):
                # Убираем пробелы и переводы строк
                binary_str = line.strip()
                
                # Пропускаем пустые строки
                if not binary_str:
                    continue
                
                try:
                    # Преобразуем двоичную строку в целое число (основание 2)
                    decimal_num = int(binary_str, 2)
                    
                    # Преобразуем в шестнадцатеричное и убираем '0x'
                    hex_num = hex(decimal_num)[2:]
                    
                    # Дополняем нулями слева до 4 символов и переводим в верхний регистр
                    hex_fixed = hex_num.zfill(4).upper()
                    
                    # Записываем результат в выходной файл
                    outfile.write(hex_fixed + '\n')
                    
                except ValueError as e:
                    print(f"Ошибка в строке {line_num}: '{binary_str}' - неверный двоичный формат")
                    
        print(f"Преобразование завершено! Результат сохранен в файл: {output_file}")
        
    except FileNotFoundError:
        print(f"Ошибка: Файл '{input_file}' не найден")
    except Exception as e:
        print(f"Произошла ошибка: {e}")


# Пример использования
if __name__ == "__main__":
    # Укажите пути к вашим файлам
    input_filename = "binary.txt"   # Входной файл с двоичными числами
    output_filename = "hex_numbers.txt"     # Выходной файл с шестнадцатеричными числами
    
    # Запускаем преобразование
    binary_to_hex_fixed_width(input_filename, output_filename)
