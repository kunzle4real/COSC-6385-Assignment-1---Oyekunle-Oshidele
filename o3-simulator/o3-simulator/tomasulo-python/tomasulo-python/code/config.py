# Multi-issue extension
# input file parser

'''
read one test-case file containing
1. hardware configuration (# of rs, cycles in EX/MEM, # of FUs)
2. ROB entries and issue width (1-4, default 1)
3. initial register and memory values
4. assembly instructions (case insensitive, commas optional)
'''
import re

# canonical spelling of every supported opcode
OPCODES = {'ld': 'Ld', 'sd': 'Sd',
           'beq': 'Beq', 'bne': 'Bne',
           'add': 'Add', 'add.d': 'Add.d', 'addi': 'Addi',
           'sub': 'Sub', 'sub.d': 'Sub.d', 'mult.d': 'Mult.d'}

UNITS = {'integer adder': 'int_adder', 'fp adder': 'fp_adder',
         'fp multiplier': 'fp_multi', 'load/store unit': 'ld_sd'}

# function: default configuration (same as the original hard-coded main.py)
def default_config():
    return {
        'int_adder': {'rs': 4, 'ex': 1, 'fu': 1},
        'fp_adder':  {'rs': 3, 'ex': 4, 'fu': 1},
        'fp_multi':  {'rs': 2, 'ex': 15, 'fu': 1},
        'ld_sd':     {'rs': 5, 'ex': 1, 'mem': 5, 'fu': 1},
        'rob': 64,
        'issue_width': 1,
        'reg_int': {}, 'reg_fp': {}, 'memory': {},
        'instructions': [],
    }

# function: normalize one instruction into "Op A B C" form
def normalize_instruction(line):
    tokens = line.replace(',', ' ').split()
    op = OPCODES[tokens[0].lower()]
    return ' '.join([op] + [token.upper() for token in tokens[1:]])

# function: parse a number keeping ints as ints
def parse_number(text):
    if re.fullmatch(r'[-+]?\d+', text):
        return int(text)
    return float(text)

# function: read config file
def read_config(path):
    cfg = default_config()
    with open(path) as f:
        lines = f.read().splitlines()
    for raw in lines:
        line = raw.strip()
        lower = line.lower()
        if (line == '') | line.startswith('#'):
            continue
        # functional unit rows
        unit = [u for u in UNITS if lower.startswith(u)]
        if unit:
            numbers = [int(n) for n in re.findall(r'\d+', lower[len(unit[0]):])]
            entry = cfg[UNITS[unit[0]]]
            if UNITS[unit[0]] == 'ld_sd':
                keys = ['rs', 'ex', 'mem', 'fu']
            else:
                keys = ['rs', 'ex', 'fu']
            for key, value in zip(keys, numbers):
                entry[key] = value
            continue
        match = re.match(r'rob entries\s*=\s*(\d+)', lower)
        if match:
            cfg['rob'] = int(match.group(1))
            continue
        match = re.match(r'issue width\s*=\s*(\d+)', lower)
        if match:
            cfg['issue_width'] = int(match.group(1))
            continue
        # memory initialization, e.g. Mem[4]=1, Mem[8]=2
        if lower.startswith('mem'):
            for addr, value in re.findall(r'mem\[\s*(\d+)\s*\]\s*=\s*([-+0-9.eE]+)', lower):
                cfg['memory'][int(addr)] = float(value)
            continue
        # register initialization, e.g. R1=10, F2=30.1
        if re.match(r'[rf]\d+\s*=', lower):
            for kind, num, value in re.findall(r'([rf])(\d+)\s*=\s*([-+0-9.eE]+)', lower):
                if kind == 'r':
                    cfg['reg_int'][int(num)] = parse_number(value)
                else:
                    cfg['reg_fp'][int(num)] = float(value)
            continue
        # instructions
        if lower.split()[0].rstrip(',') in OPCODES:
            cfg['instructions'].append(normalize_instruction(line))
            continue
        raise ValueError('cannot parse line: ' + raw)
    check_config(cfg)
    return cfg

# function: sanity check
def check_config(cfg):
    if not 1 <= cfg['issue_width'] <= 4:
        raise ValueError('issue width must be between 1 and 4')
    for addr in cfg['memory']:
        if not 0 <= addr < 256:
            raise ValueError('memory address out of range (256B): ' + str(addr))
