import sys
from virtual_machine import virtual_machine


def main():

    '''
    xxx.vm -> xxx.asm

    prog/(a.vm, b.vm, c.vm) -> prog.asm
    '''

    print(sys.argv)
    dir_or_path = sys.argv[1]

    vm = virtual_machine(dir_or_path)
    vm.translate()


main()