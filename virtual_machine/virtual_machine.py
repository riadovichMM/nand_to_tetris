from pathlib import Path


class virtual_machine:

    def __init__(self, dir_or_file):

        self.dir_or_file = dir_or_file
        self.files = {}
        self.asm_code = []


        if '.vm' in dir_or_file:
            self.read_file()
        else:
            self.open_directory_and_read_files()


    def read_file(self):
        f = open(self.dir_or_file, 'r')
        clean_name = self.dir_or_file.split('/')[-1]
        self.files[clean_name] = f.readlines()
        f.close()

    def open_directory_and_read_files(self):
        dir_path = Path(self.dir_or_file)

        files = [f for f in dir_path.iterdir() if f.is_file()]

        for file in files:
            f = open(self.dir_or_file + file.name, 'r')
            self.files[file.name] = f.readlines()
            f.close()


    def get_clean_code(self, code):
        clean_code = []
        for line in code:
            if line.startswith('//') or line == '\n':
                continue

            if '//' in line:
                line = line.split('//')[0]

            clean_code.append(line.strip())
        return clean_code

    def translate(self):
        for file in self.files:
            code = self.get_clean_code(self.files[file])

            print('---'*30)
            print(file)
            for line in code:
                print(line)

                parts = line.split()
                print(parts)

                if parts[0] in ['push', 'pop']:
                    self.push_pop_command(parts)


    def push_pop_command(self, parts):
        if parts[0] == 'push':
            if parts[1] == 'constant':
                pass
            pass
        pass
