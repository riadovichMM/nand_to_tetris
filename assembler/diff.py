def compare_files(file1_path, file2_path):
    """
    Сравнивает два файла построчно.
    Возвращает True если файлы идентичны, False в противном случае.
    """
    try:
        with open(file1_path, 'r', encoding='utf-8') as f1, \
             open(file2_path, 'r', encoding='utf-8') as f2:
            
            lines1 = f1.readlines()
            lines2 = f2.readlines()
            
            # Проверяем количество строк
            if len(lines1) != len(lines2):
                return False
            
            # Сравниваем каждую строку
            for line1, line2 in zip(lines1, lines2):
                if line1.rstrip('\n\r') != line2.rstrip('\n\r'):
                    return False
            
            return True
            
    except Exception:
        return False
    
result = compare_files('./binary/code.hack', './binary/my_code.hack')
if result:
    print("Файлы идентичны")
else:
    print("Файлы различаются")