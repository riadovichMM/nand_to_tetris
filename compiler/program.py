from compiler import compiler
from pathlib import Path
import sys


def main():
    dir_or_file = sys.argv[1]

    if '.jack' in dir_or_file:
        # open file and read
        file = open(dir_or_file, 'r+')
        code = file.readlines()
        file.close()
        code = ''.join(code).replace('\n', '')

        comp = compiler(code)
        comp.compile()
    else:
        directory = Path(dir_or_file)

        # List only files (ignores subdirectories)
        files = [f.name for f in directory.iterdir() if f.is_file()]

        for file_name in files:
            file = open(dir_or_file + file_name, 'r+')
            code = file.readlines()
            file.close()

            code = ''.join(code).replace('\n', '')
            comp = compiler(code)
            comp.compile()



main()