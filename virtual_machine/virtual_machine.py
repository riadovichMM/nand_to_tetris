from pathlib import Path


class virtual_machine:

    def __init__(self, dir_or_file):

        self.dir_or_file = dir_or_file
        self.files = {}

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
        print('code', code)
        for line in code:
            if line.startwith('//'):
                continue

            if '//' in line:
                pass
            print(line)

    def translate(self):
        for file in self.files:
            code = self.get_clean_code(self.files[file])


    