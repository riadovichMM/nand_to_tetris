import re


JACK_CODE = """
class Simple {
    function int calculate() {
        var int x;

        let x = 2 + 3;
        return x;
    }
}
"""


class SimpleCompiler:
    def __init__(self, source):
        # Разбиваем исходный код на токены.
        self.tokens = re.findall(
            r"[A-Za-z_]\w*|[0-9]+|[{}()\[\].,;+\-=]",
            source
        )
        self.pos = 0
        self.vm = []