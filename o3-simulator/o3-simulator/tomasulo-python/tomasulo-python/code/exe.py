# Qing 
# 24th May 2017

''' 
1. calculate valid instructions
    -- for ALU instructions, write results into fu_results, remove that fu entry  
    -- for LD/SD, write address result immediately back to ld_sd_queue
2. fetch instructions into function unit with spare space
    -- remove ALU instructions from rs
    -- don't remove ld/sd instructions
3. multi-issue: stages are called in reverse order (commit, wb, mem, exe, issue)
    -- an instruction issued in cycle n starts EX in cycle n+1 at the earliest
    -- an operand broadcast on the CDB in cycle n is used in EX in cycle n+1
    -- every instruction in a FU advances exactly one cycle per call
'''
from init import fu_entry, fu_result

# function: check rs and return the oldest valid instruction index
# operands broadcast in this cycle (wake_cycle==cycle) can only be used next cycle
def check_valid_ins_in_rs(rs, ROB, cycle):
    index = -1
    oldest = -1
    if len(rs)!=0:
        for i in range(len(rs)):
            if (rs[i].valid_1st==1)&(rs[i].valid_2nd==1)&(rs[i].busy==1)&(rs[i].wake_cycle<cycle):
                age = find_ROB_entry(ROB, rs[i].dest_tag)
                if (oldest<0)|(age<oldest):
                    index = i
                    oldest = age
    return index

# function: check ld_sd_queue and return valid instruction index
def check_valid_ins_in_ldsd(ldsd, cycle):
    index = -1
    if len(ldsd)!=0:
        for i in range(len(ldsd)):
            if (ldsd[i].valid==1) & (ldsd[i].ready==0) & (ldsd[i].wake_cycle<cycle):
                index = i
                break
    return index

# function: add entry into fu 
def add_entry_into_fu(fu, ins_in_rs):
    fu[-1].cycle = 0
    fu[-1].op = ins_in_rs.op
    fu[-1].value1 = ins_in_rs.value_1st
    fu[-1].value2 = ins_in_rs.value_2nd
    fu[-1].dest_tag = ins_in_rs.dest_tag

# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            break
    return index

# function: resolve a branch at the end of EX
def resolve_branch(element, ROB, index, cycle, PC):
    if element.op == 'Bne':
        taken = element.value1 != element.value2
    else: # Beq
        taken = element.value1 == element.value2
    if taken:
        offset = ROB[index].dest_tag
        PC.PC = int(ROB[index].PC + 1 + offset/4)
    else:
        PC.PC = ROB[index].PC + 1
    # fetch restarts in the next cycle
    PC.valid = 1
    PC.resume_cycle = cycle + 1

# function: functional units execution 
# advance every instruction in the fu by one cycle
def fu_exe(fu, fu_results, ROB, time_fu, cycle, PC):
    for element in list(fu):
        element.cycle += 1
        index = find_ROB_entry(ROB, element.dest_tag)
        # write starting cycle 
        if element.cycle == 1:
            ROB[index].exe.append(cycle)
        # finish cycle
        if element.cycle == time_fu:
            ROB[index].exe.append(cycle)
            if (element.op=='Bne')|(element.op=='Beq'):
                resolve_branch(element, ROB, index, cycle, PC)
            else:
                # calculation result
                fu_results.append(fu_result())
                fu_results[-1].dest_tag = element.dest_tag
                if (element.op=='Add')|(element.op=='Add.d')|(element.op=='Addi'):
                    fu_results[-1].value = element.value1 + element.value2
                elif (element.op=='Sub')|(element.op=='Sub.d'):
                    fu_results[-1].value = element.value1 - element.value2
                elif (element.op=='Mult.d'):
                    fu_results[-1].value = element.value1 * element.value2
            # remove from fu 
            fu.remove(element)

# function: fetch ready instructions from rs into fu
# pipelined: each of the num_fu units accepts one new instruction per cycle
# unpipelined: a unit accepts a new instruction only when it is idle
def fetch_rs_into_fu(rs, fu, num_fu, pipelined, ROB, cycle):
    if pipelined:
        slots = num_fu
    else:
        slots = num_fu - len(fu)
    for i in range(slots):
        index = check_valid_ins_in_rs(rs, ROB, cycle)
        if index < 0:
            break
        fu.append(fu_entry())
        add_entry_into_fu(fu, rs[index])
        # remove ins from rs 
        rs[index].busy = 0

# function: ld_sd_execution 
def ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle):
    if ld_sd_exe.busy == 1:
        for element in ld_sd_queue:
            if element.ld_sd_tag == ld_sd_exe.dest_tag:
                break
        index = find_ROB_entry(ROB, element.dest_tag)
        # execute 
        ld_sd_exe.cycle += 1
        # write down starting cycle
        if ld_sd_exe.cycle == 1:            
            ROB[index].exe.append(cycle)
        # write address back to ld_sd_queue
        if ld_sd_exe.cycle == time_ld_sd_exe:
            element.address = ld_sd_exe.value1 + ld_sd_exe.value2
            element.ready = 1
            # write down finish cycle
            ROB[index].exe.append(cycle)
            ld_sd_exe.busy = 0

# function: execution
def exe(fu_int_adder, time_fu_int_adder, num_fu_int_adder,
        fu_fp_adder, time_fu_fp_adder, num_fu_fp_adder,
        fu_fp_multi, time_fu_fp_multi, num_fu_fp_multi, results_buffer,
        rs_int_adder, rs_fp_adder, rs_fp_multi, 
        ld_sd_exe, time_ld_sd_exe, ld_sd_queue,
        cycle, ROB, PC):
    '''fetch instructions from rs and ld_sd_queue'''
    # from ld_sd_queue (one dedicated address adder)
    index = check_valid_ins_in_ldsd(ld_sd_queue, cycle)
    if (index>=0)&(ld_sd_exe.busy==0):
        ld_sd_exe.busy = 1
        ld_sd_exe.cycle = 0
        ld_sd_exe.value1 = ld_sd_queue[index].reg_value
        ld_sd_exe.value2 = ld_sd_queue[index].immediate
        ld_sd_exe.dest_tag = ld_sd_queue[index].ld_sd_tag
    # from rs: integer adder is unpipelined, fp adder/multiplier are pipelined
    fetch_rs_into_fu(rs_int_adder, fu_int_adder, num_fu_int_adder, False, ROB, cycle)
    fetch_rs_into_fu(rs_fp_adder, fu_fp_adder, num_fu_fp_adder, True, ROB, cycle)
    fetch_rs_into_fu(rs_fp_multi, fu_fp_multi, num_fu_fp_multi, True, ROB, cycle)
    '''execution in fu and ld_sd address calculation'''
    ld_sd_execution(ld_sd_exe, time_ld_sd_exe, ld_sd_queue, ROB, cycle) 
    # functional units 
    fu_exe(fu_int_adder, results_buffer, ROB, time_fu_int_adder, cycle, PC)
    fu_exe(fu_fp_adder, results_buffer, ROB, time_fu_fp_adder, cycle, PC)
    fu_exe(fu_fp_multi, results_buffer, ROB, time_fu_fp_multi, cycle, PC)
