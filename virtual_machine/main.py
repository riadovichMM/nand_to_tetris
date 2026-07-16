import os
import sys
from vm_translator import vm_translator


def generate_one_output(files_and_codes):
    output_file = open('output.asm', 'w+')
    for file in files_and_codes:
        output_file.write(files_and_codes[file])
    output_file.close()


def main():
    dir_path = sys.argv[1]
    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]

    files_and_codes = {}

    for file in files:
        vm_obj = vm_translator(file, dir_path)
        vm_obj.translate()
        files_and_codes[file] = vm_obj.get_code()

    print(files_and_codes)
    generate_one_output(files_and_codes)




main()