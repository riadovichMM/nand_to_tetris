import sys
import os

from tokenizer import tokenizer
from analyzer import analyzer

def main():
        
    dir_path = 'jack_code'
    files = [f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]


    
    for file in files:
        t = tokenizer()
        t.open_file_and_read(os.path.join(dir_path, file))
        t.tokenize()
        # t.generate_xml()

        a = analyzer(t.tokens)
        a.compile_class()
        a.generate_xml(file)



main()
