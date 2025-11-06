// Test JGT (address 0) - 5 > 3
@5
D=A
@3
D=D-A
@check_jgt
D;JGT
@skip_jgt
0;JMP

(check_jgt)
@1
D=A
@0
M=D

(skip_jgt)

// Test JEQ (address 1) - 4 = 4
@4
D=A
@4
D=D-A
@check_jeq
D;JEQ
@skip_jeq
0;JMP

(check_jeq)
@1
D=A
@1
M=D

(skip_jeq)

// Test JGE (address 2) - 6 >= 4
@6
D=A
@4
D=D-A
@check_jge
D;JGE
@skip_jge
0;JMP

(check_jge)
@1
D=A
@2
M=D

(skip_jge)

// Test JLT (address 3) - 2 < 7
@2
D=A
@7
D=D-A
@check_jlt
D;JLT
@skip_jlt
0;JMP

(check_jlt)
@1
D=A
@3
M=D

(skip_jlt)

// Test JNE (address 4) - 8 ≠ 9
@8
D=A
@9
D=D-A
@check_jne
D;JNE
@skip_jne
0;JMP

(check_jne)
@1
D=A
@4
M=D

(skip_jne)

// Test JLE (address 5) - 4 ≤ 4
@4
D=A
@4
D=D-A
@check_jle
D;JLE
@skip_jle
0;JMP

(check_jle)
@1
D=A
@5
M=D

(skip_jle)

(end)
@end
0;JMP