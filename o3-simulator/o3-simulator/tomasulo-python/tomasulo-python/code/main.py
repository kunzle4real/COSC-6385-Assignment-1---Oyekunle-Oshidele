# Qing
# 21st May 2017
# multi-issue (1-4 instructions, in order) extension

'''
usage: python main.py [test_case_file] [-w ISSUE_WIDTH]
    -- test_case_file defaults to test_case.txt
    -- the issue width is read from the file ("Issue width = N", default 1);
       -w overrides it
'''
import argparse
from copy import deepcopy
from collections import deque, namedtuple
from init import read_instruction, build_rs, ld_sd_entry, ld_sd_exe, ld_sd_mem, cdb, ROB_entry, PC
from print_status import ps, pss
from issue import issue, check_rs_space
from exe import exe
from mem import mem
from wb import wb
from commit import commit, print_ROB
from config import read_config

# guard against a program that can never finish
MAX_CYCLES = 100000

# function: run the simulation for one configuration
def simulate(cfg, verbose=True):
    issue_width = cfg['issue_width']
    instructions = cfg['instructions']
    '''initialize regs, RAT, memory'''
    # integer REG
    reg_int = []
    for i in range(32):
        reg_int.extend([0])
    for i, value in cfg['reg_int'].items():
        if i != 0: # R0 is hardwired to 0
            reg_int[i] = value
    rat_int = deepcopy(reg_int)
    # fp REG
    reg_fp = []
    for i in range(32):
        reg_fp.extend([0])
    for i, value in cfg['reg_fp'].items():
        reg_fp[i] = value
    rat_fp = deepcopy(reg_fp)
    # memory
    memory = []
    for i in range(256):
        memory.extend([0])
    for addr, value in cfg['memory'].items():
        memory[addr] = value
    '''intialize reservation stations'''
    rs_int_adder = build_rs(cfg['int_adder']['rs'])
    rs_fp_adder = build_rs(cfg['fp_adder']['rs'])
    rs_fp_multi = build_rs(cfg['fp_multi']['rs'])
    '''initilize function unit'''
    # integer adder (unpipelined)
    fu_int_adder = deque()
    time_fu_int_adder = cfg['int_adder']['ex']
    num_fu_int_adder = cfg['int_adder']['fu']
    # fp adder (pipelined)
    fu_fp_adder = deque()
    time_fu_fp_adder = cfg['fp_adder']['ex']
    num_fu_fp_adder = cfg['fp_adder']['fu']
    # fp multiplier (pipelined)
    fu_fp_multi = deque()
    time_fu_fp_multi = cfg['fp_multi']['ex']
    num_fu_fp_multi = cfg['fp_multi']['fu']
    '''initialize load/store queue'''
    ld_sd_queue = deque()
    size_ld_sd_queue = cfg['ld_sd']['rs']
    ld_sd_exe_unit = ld_sd_exe()
    ld_sd_exe_unit.busy = 0
    time_ld_sd_exe = cfg['ld_sd']['ex']
    ld_sd_mem_unit = ld_sd_mem()
    ld_sd_mem_unit.busy = 0
    time_ld_sd_mem = cfg['ld_sd']['mem']
    '''initialize ROB'''
    ROB = deque()
    size_ROB = cfg['rob']
    '''initialize CDB'''
    results_buffer = deque()
    cdb_bus = cdb()
    cdb_bus.valid = 0
    """issue first instruction"""
    # instruction pointer
    pc = PC()
    pc.PC = 0
    pc.valid = 1
    pc.resume_cycle = 0
    cycle = 1
    committed = []

    # main
    # stages are called in reverse pipeline order, so every stage only sees
    # what earlier stages produced in previous cycles
    while (len(ROB)>0)|(pc.PC<len(instructions))|(ld_sd_mem_unit.busy==1):

        '''COMMIT stage'''
        committed.extend(commit(ROB, reg_int, reg_fp, cycle, instructions, issue_width,
                                ld_sd_queue, ld_sd_mem_unit, time_ld_sd_mem))

        '''CDB stage'''
        wb(cdb_bus, rat_int, rat_fp,
            rs_int_adder, rs_fp_adder, rs_fp_multi,
            ld_sd_queue, ROB, cycle,
            results_buffer, issue_width)

        '''MEM stage'''
        mem(ld_sd_queue, ld_sd_mem_unit, time_ld_sd_mem, results_buffer,
            memory, ROB, cycle)

        '''EXE stage'''
        exe(fu_int_adder, time_fu_int_adder, num_fu_int_adder,
            fu_fp_adder, time_fu_fp_adder, num_fu_fp_adder,
            fu_fp_multi, time_fu_fp_multi, num_fu_fp_multi, results_buffer,
            rs_int_adder, rs_fp_adder, rs_fp_multi,
            ld_sd_exe_unit, time_ld_sd_exe, ld_sd_queue,
            cycle, ROB, pc)

        '''ISSUE stage'''
        issue(cycle, pc, instructions, ROB, size_ROB,
                rs_int_adder,
                rs_fp_adder,
                rs_fp_multi,
                ld_sd_queue, size_ld_sd_queue,
                rat_int, rat_fp, issue_width)

        # cycle number
        cycle +=1
        if cycle > MAX_CYCLES:
            raise RuntimeError('simulation did not finish in %d cycles' % MAX_CYCLES)

    result = {'committed': committed, 'reg_int': reg_int, 'reg_fp': reg_fp,
              'memory': memory, 'cycles': committed[-1].commit[0] if committed else 0}
    if verbose:
        print_results(cfg, result)
    return result

# function: print instruction status table, registers and non-zero memory
def print_results(cfg, result):
    print('Issue width = %d' % cfg['issue_width'])
    item = ''.ljust(30)
    item += 'ISSUE'.ljust(15)
    item += 'EXE'.ljust(15)
    item += 'MEM'.ljust(15)
    item += 'WB'.ljust(15)
    item += 'COMMIT'.ljust(15)
    print (item)
    for entry in result['committed']:
        print_ROB(entry, cfg['instructions'])
    count = len(result['committed'])
    print('')
    print('Instructions committed: %d, cycles: %d, IPC: %.3f'
          % (count, result['cycles'], count/float(max(result['cycles'], 1))))
    print('')
    print('REGISTER VALUES')
    for prefix, regs in (('R', result['reg_int']), ('F', result['reg_fp'])):
        for start in range(0, 32, 8):
            print(''.ljust(8) + ''.join((prefix+str(i)).ljust(10) for i in range(start, start+8)))
            print('value:'.ljust(8) + ''.join(str(regs[i]).ljust(10) for i in range(start, start+8)))
    print('')
    print('NON-ZERO MEMORY VALUES')
    print('Addresses'.ljust(12) + 'Values')
    for addr in range(len(result['memory'])):
        if result['memory'][addr] != 0:
            print(str(addr).ljust(12) + str(result['memory'][addr]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Multi-issue Tomasulo simulator')
    parser.add_argument('test_case', nargs='?', default='test_case.txt')
    parser.add_argument('-w', '--issue-width', type=int, choices=[1, 2, 3, 4])
    args = parser.parse_args()
    cfg = read_config(args.test_case)
    if args.issue_width is not None:
        cfg['issue_width'] = args.issue_width
    simulate(cfg)
