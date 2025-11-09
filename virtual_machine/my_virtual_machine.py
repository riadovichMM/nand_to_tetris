class StackMachine :

    def __init__(self):
        self.stack = []
        self.ram = [0] * 65_535

        

    def load_vm_code(self):
        pass


stack_machine = StackMachine()
print(stack_machine.ram)