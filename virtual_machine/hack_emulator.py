import tkinter as tk
from tkinter import filedialog, messagebox


class HackCPU:
    """Эмулятор CPU Hack (16-бит, архитектура Nand2Tetris)."""

    def __init__(self):
        self.rom = []
        self.reset()

    def reset(self):
        self.ram = [0] * 24577          # 0..16383 RAM, 16384..24575 screen, 24576 kbd
        self.pc = 0
        self.A = 0
        self.D = 0
        # ROM не трогаем — он загружается отдельно

    def load_hack(self, filename):
        """Загружает .hack файл (текстовый, по строке бинарного кода)."""
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            self.rom = []
            for line in f:
                line = line.strip()
                if not line or line.startswith('//'):
                    continue
                if '//' in line:
                    line = line[:line.index('//')].strip()
                if line:
                    try:
                        self.rom.append(int(line, 2))
                    except ValueError:
                        pass
        self.pc = 0
        self.A = 0
        self.D = 0
        self.ram = [0] * 24577

    def step(self):
        """Выполняет одну инструкцию. Возвращает False если PC за пределами ROM."""
        if self.pc < 0 or self.pc >= len(self.rom):
            return False
        instr = self.rom[self.pc]

        # A-инструкция: 0vvvvvvvvvvvvvvv
        if (instr & 0x8000) == 0:
            self.A = instr & 0x7FFF
            self.pc += 1
            return True

        # C-инструкция: 111 a c1c2c3c4c5c6 d1d2d3 j1j2j3
        a    = (instr >> 12) & 1
        comp = (instr >> 6)  & 0x3F
        dest = (instr >> 3)  & 0x7
        jump =  instr        & 0x7

        M = self.ram[self.A] if self.A < 24577 else 0
        x = self.A if a == 0 else M

        # Таблица comp
        if   comp == 0x2A: out = 0
        elif comp == 0x3F: out = 1
        elif comp == 0x3A: out = 0xFFFF
        elif comp == 0x0C: out = self.D
        elif comp == 0x30: out = x
        elif comp == 0x0D: out = (~self.D) & 0xFFFF
        elif comp == 0x31: out = (~x)      & 0xFFFF
        elif comp == 0x0F: out = (-self.D) & 0xFFFF
        elif comp == 0x33: out = (-x)      & 0xFFFF
        elif comp == 0x1F: out = (self.D + 1) & 0xFFFF
        elif comp == 0x37: out = (x      + 1) & 0xFFFF
        elif comp == 0x06: out = (self.D - 1) & 0xFFFF
        elif comp == 0x32: out = (x      - 1) & 0xFFFF
        elif comp == 0x02: out = (self.D + x) & 0xFFFF
        elif comp == 0x13: out = (self.D - x) & 0xFFFF
        elif comp == 0x07: out = (x      - self.D) & 0xFFFF
        elif comp == 0x00: out = self.D & x
        elif comp == 0x15: out = self.D | x
        else:              out = 0

        out &= 0xFFFF

        # Dest
        if dest & 0x4: self.A = out
        if dest & 0x2: self.D = out
        if dest & 0x1:
            if self.A < 24577:
                self.ram[self.A] = out

        # Jump (знаковое сравнение)
        signed_out = out if out < 0x8000 else out - 0x10000
        do_jump = False
        if   jump == 0x7: do_jump = True
        elif jump == 0x6: do_jump = signed_out <=  0   # JLE
        elif jump == 0x5: do_jump = signed_out !=  0   # JNE
        elif jump == 0x4: do_jump = signed_out >=  0   # JGE
        elif jump == 0x3: do_jump = signed_out <   0   # JLT
        elif jump == 0x2: do_jump = signed_out ==  0   # JEQ
        elif jump == 0x1: do_jump = signed_out >   0   # JGT

        self.pc = self.A if do_jump else self.pc + 1
        return True


class HackEmulator:
    """GUI эмулятора на Tkinter."""

    def __init__(self, root):
        self.root = root
        self.root.title("Nand2Tetris Hack Emulator")
        self.cpu = HackCPU()
        self.running = False
        self.filename = None
        self.prev_screen = [0] * 8192

        self.setup_ui()
        self.update_display()

    # ---------- UI ----------
    def setup_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(top, text="Load .hack", command=self.load_file).pack(side=tk.LEFT, padx=2)
        self.run_btn = tk.Button(top, text="Run", command=self.toggle_run, width=7)
        self.run_btn.pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Step", command=self.step_once).pack(side=tk.LEFT, padx=2)
        tk.Button(top, text="Reset", command=self.reset_cpu).pack(side=tk.LEFT, padx=2)

        tk.Label(top, text="  Steps/frame:").pack(side=tk.LEFT)
        self.speed_var = tk.IntVar(value=1000)
        tk.Scale(top, from_=1, to=100000, orient=tk.HORIZONTAL,
                 variable=self.speed_var, length=220).pack(side=tk.LEFT)

        self.instr_label = tk.Label(top, text="Instr: -", font=('monospace', 10))
        self.instr_label.pack(side=tk.RIGHT, padx=5)

        main = tk.Frame(self.root)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Левая часть: экран + клавиатура ---
        left = tk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(left, text="Screen 512x256 (memory 16384..24575)",
                 font=('sans-serif', 10, 'bold')).pack(anchor=tk.W)
        self.screen_canvas = tk.Canvas(left, width=512, height=256,
                                       bg='black', highlightthickness=1,
                                       highlightbackground='gray')
        self.screen_canvas.pack(pady=4)
        self.screen_image = tk.PhotoImage(width=512, height=256)
        self.screen_canvas.create_image(0, 0, anchor=tk.NW, image=self.screen_image)

        self.kbd_label = tk.Label(left, text="Keyboard: (none)",
                                  font=('monospace', 10), anchor=tk.W)
        self.kbd_label.pack(fill=tk.X, pady=4)

        tk.Label(left, text="(кликните на экран, чтобы захватить клавиатуру)",
                 fg='gray').pack(anchor=tk.W)

        # --- Правая часть: регистры + память ---
        right = tk.Frame(main)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        reg_frame = tk.LabelFrame(right, text="Registers / Status", padx=6, pady=6)
        reg_frame.pack(fill=tk.X, padx=4, pady=4)

        self.reg_labels = {}
        for name in ['PC', 'A', 'D', 'M', 'RAM[0]', 'RAM[1]', 'RAM[2]', 'Keyboard']:
            row = tk.Frame(reg_frame)
            row.pack(fill=tk.X)
            tk.Label(row, text=f"{name:>10}:", width=11, anchor=tk.W,
                     font=('monospace', 10)).pack(side=tk.LEFT)
            lbl = tk.Label(row, text="0", width=10, anchor=tk.E,
                           font=('monospace', 10, 'bold'))
            lbl.pack(side=tk.LEFT, padx=5)
            self.reg_labels[name] = lbl

        mem_frame = tk.LabelFrame(right, text="Memory view", padx=6, pady=6)
        mem_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self.mem_text = tk.Text(mem_frame, width=28, height=24,
                                font=('monospace', 9), state=tk.DISABLED,
                                bg='#f4f4f4')
        self.mem_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb = tk.Scrollbar(mem_frame, command=self.mem_text.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.mem_text.config(yscrollcommand=sb.set)

        # Клавиатура
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<KeyRelease>', self.on_key_release)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- Файл ----------
    def load_file(self):
        fn = filedialog.askopenfilename(
            filetypes=[("Hack files", "*.hack"), ("All files", "*.*")])
        if not fn:
            return
        try:
            self.cpu.load_hack(fn)
            self.filename = fn
            self.prev_screen = [0] * 8192
            self.update_display()
            self.root.title(f"Hack Emulator — {fn.split('/')[-1].split(chr(92))[-1]}")
        except Exception as e:
            messagebox.showerror("Load error", str(e))

    # ---------- Управление ----------
    def toggle_run(self):
        self.running = not self.running
        self.run_btn.config(text="Pause" if self.running else "Run")
        if self.running:
            self.run_loop()

    def run_loop(self):
        if not self.running:
            return
        n = self.speed_var.get()
        ok = True
        for _ in range(n):
            if not self.cpu.step():
                ok = False
                break
        self.update_display()
        if ok:
            self.root.after(16, self.run_loop)   # ~60 FPS
        else:
            self.running = False
            self.run_btn.config(text="Run")

    def step_once(self):
        self.cpu.step()
        self.update_display()

    def reset_cpu(self):
        self.running = False
        self.run_btn.config(text="Run")
        self.cpu.reset()
        self.prev_screen = [0] * 8192
        self.update_display()

    def on_close(self):
        self.running = False
        self.root.destroy()

    # ---------- Клавиатура ----------
    _KEY_MAP = {
        'Return': 128, 'BackSpace': 129,
        'Left': 130, 'Up': 131, 'Right': 132, 'Down': 133,
        'Home': 134, 'End': 135, 'Prior': 136, 'Next': 137,
        'Insert': 138, 'Delete': 139, 'Escape': 140,
    }

    def hack_keycode(self, event):
        ks = event.keysym
        if ks in self._KEY_MAP:
            return self._KEY_MAP[ks]
        if ks.startswith('F') and ks[1:].isdigit():
            n = int(ks[1:])
            if 1 <= n <= 12:
                return 140 + n
        if len(event.char) == 1 and event.char.isprintable():
            return ord(event.char)
        return None

    def on_key_press(self, event):
        code = self.hack_keycode(event)
        if code is not None:
            self.cpu.ram[24576] = code
            self.update_kbd()

    def on_key_release(self, event):
        self.cpu.ram[24576] = 0
        self.update_kbd()

    def update_kbd(self):
        code = self.cpu.ram[24576]
        if code == 0:
            self.kbd_label.config(text="Keyboard: (none)")
            return
        if 32 <= code < 127:
            ch = repr(chr(code))
        elif code == 128: ch = 'Enter'
        elif code == 129: ch = 'Backspace'
        elif code == 140: ch = 'Escape'
        elif 130 <= code <= 133:
            ch = ['Left', 'Up', 'Right', 'Down'][code - 130]
        elif 141 <= code <= 152:
            ch = f'F{code - 140}'
        else:
            ch = f'code {code}'
        self.kbd_label.config(text=f"Keyboard: {ch}  (value = {code})")

    # ---------- Экран ----------
    def update_screen(self):
        img = self.screen_image
        ram = self.cpu.ram
        prev = self.prev_screen
        for i in range(8192):
            word = ram[16384 + i]
            if word == prev[i]:
                continue
            prev[i] = word
            y = i // 32
            x_base = (i % 32) * 16
            # очищаем 16-пиксельную полоску
            img.put('black', to=(x_base, y, x_base + 16, y + 1))
            if word == 0:
                continue
            if word == 0xFFFF:
                img.put('white', to=(x_base, y, x_base + 16, y + 1))
                continue
            # побитово
            for bit in range(16):
                if word & (0x8000 >> bit):
                    img.put('white', to=(x_base + bit, y, x_base + bit + 1, y + 1))

    # ---------- Общий апдейт ----------
    def update_display(self):
        self.update_screen()

        M = self.cpu.ram[self.cpu.A] if self.cpu.A < 24577 else 0
        self.reg_labels['PC'].config(text=str(self.cpu.pc))
        self.reg_labels['A'].config(text=str(self.cpu.A))
        self.reg_labels['D'].config(text=str(self.cpu.D))
        self.reg_labels['M'].config(text=str(M))
        self.reg_labels['RAM[0]'].config(text=str(self.cpu.ram[0]))
        self.reg_labels['RAM[1]'].config(text=str(self.cpu.ram[1]))
        self.reg_labels['RAM[2]'].config(text=str(self.cpu.ram[2]))
        self.reg_labels['Keyboard'].config(text=str(self.cpu.ram[24576]))

        if 0 <= self.cpu.pc < len(self.cpu.rom):
            instr = self.cpu.rom[self.cpu.pc]
            self.instr_label.config(
                text=f"ROM[{self.cpu.pc}] = {instr:016b}  (0x{instr:04X})")
        else:
            self.instr_label.config(text="ROM[PC] = (out of bounds)")

        # Память
        t = self.mem_text
        t.config(state=tk.NORMAL)
        t.delete('1.0', tk.END)
        t.insert(tk.END, " Addr   Value\n")
        t.insert(tk.END, "-------------\n")
        for a in range(32):
            t.insert(tk.END, f" {a:4d}   {self.cpu.ram[a]:5d}\n")
        t.insert(tk.END, "  ...\n")
        t.insert(tk.END, " Screen (16384..):\n")
        for a in range(16384, 16416):
            t.insert(tk.END, f" {a:5d}  {self.cpu.ram[a]:5d}\n")
        t.insert(tk.END, "  ...\n")
        t.insert(tk.END, f" Kbd [24576] = {self.cpu.ram[24576]}\n")
        t.config(state=tk.DISABLED)

        self.update_kbd()


def main():
    root = tk.Tk()
    root.geometry("1150x640")
    HackEmulator(root)
    root.mainloop()


if __name__ == '__main__':
    main()