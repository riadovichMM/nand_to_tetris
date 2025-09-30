from vm_parser import Parser
from vm_code_writer import CodeWriter

def main():
    parser = Parser("./code.vm")
    code_writer = CodeWriter("./output.asm")

    while parser.has_more_commands():
        pass
    pass


main()