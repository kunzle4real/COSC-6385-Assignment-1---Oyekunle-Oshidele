# Sequential (one instruction at a time) reference interpreter.
# Uses the simulator's ISA conventions: branch offsets are byte offsets
# (target = PC + 1 + offset/4 instructions) and R0 is hardwired to 0.


def run_reference(cfg, max_steps=100000):
    reg_int = [0] * 32
    reg_fp = [0] * 32
    memory = [0] * 256
    for i, v in cfg['reg_int'].items():
        if i != 0:
            reg_int[i] = v
    for i, v in cfg['reg_fp'].items():
        reg_fp[i] = v
    for a, v in cfg['memory'].items():
        memory[a] = v
    program = cfg['instructions']
    trace = []
    pc = 0
    while pc < len(program):
        trace.append(pc)
        if len(trace) > max_steps:
            raise RuntimeError('reference did not terminate')
        op, *args = program[pc].split(' ')
        idx = lambda r: int(r[1:])
        next_pc = pc + 1
        if op in ('Ld', 'Sd'):
            offset, base = args[1][:-1].split('(')
            addr = reg_int[idx(base)] + int(offset)
            if op == 'Ld':
                reg_fp[idx(args[0])] = memory[addr]
            else:
                memory[addr] = reg_fp[idx(args[0])]
        elif op in ('Bne', 'Beq'):
            a, b = reg_int[idx(args[0])], reg_int[idx(args[1])]
            if (a != b) == (op == 'Bne'):
                next_pc = int(pc + 1 + int(args[2]) / 4)
        elif op in ('Add', 'Sub', 'Addi'):
            a = reg_int[idx(args[1])]
            b = int(args[2]) if op == 'Addi' else reg_int[idx(args[2])]
            if idx(args[0]) != 0:
                reg_int[idx(args[0])] = a - b if op == 'Sub' else a + b
        else:
            a, b = reg_fp[idx(args[1])], reg_fp[idx(args[2])]
            reg_fp[idx(args[0])] = {'Add.d': a + b, 'Sub.d': a - b, 'Mult.d': a * b}[op]
        pc = next_pc
    return trace, reg_int, reg_fp, memory
