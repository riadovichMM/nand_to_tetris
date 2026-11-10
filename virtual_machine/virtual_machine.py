from pathlib import Path


class virtual_machine:

    def __init__(self, dir_or_file):

        self.dir_or_file = dir_or_file
        self.files = {}

        if '.vm' in dir_or_file:
            self.read_file()
        else:
            self.open_directory_and_read_files()


        for file in self.files:
            print('---' * 20)
            print(file, self.files[file])

    def read_file(self):
        f = open(self.dir_or_file, 'r')
        clean_name = self.dir_or_file.split('/')[-1]
        self.files[clean_name] = f.readlines()
        f.close()

    def open_directory_and_read_files(self):
        dir_path = Path(self.dir_or_file)

        files = [f for f in dir_path.iterdir() if f.is_file()]

        for file in files:
            print('file', self.dir_or_file, file.name)
            f = open(self.dir_or_file + file.name, 'r')
            self.files[file.name] = f.readlines()
            f.close()


    def translate(self):
        pass