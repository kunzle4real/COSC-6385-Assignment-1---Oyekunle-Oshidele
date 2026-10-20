# Qing 
# 29th may 2017
'''
1. commit ROB_buffer
2. fetch header into ROB_buffer
3. multi-issue: commit up to issue_width instructions per cycle, in order
    -- ALU/Ld commit in the cycle after their write back
    -- branches commit in the cycle after they are resolved in EX
    -- Sd writes memory at commit: it needs its address, its data and the
       free memory port, so at most one Sd commits per cycle
'''
from mem import put_entry_into_ld_sd_mem

# function: print ROB entry 
def print_ROB(entry, instructions):
    item = instructions[entry.PC].ljust(30)
    item += str(entry.issue).ljust(15) 
    item += str(entry.exe).ljust(15) 
    item += str(entry.mem).ljust(15)
    item += str(entry.cdb).ljust(15)
    item += str(entry.commit)
    print(item)
# function: modify architectual reg
def modify_arch_reg(entry, reg_int, reg_fp):
    if entry.dest_tag[0] == 'F':
        reg_fp[int(entry.dest_tag[1:])] = entry.value
    elif (entry.dest_tag[0] == 'R')&(entry.dest_tag != 'R0'): # R0 is hardwired to 0
        reg_int[int(entry.dest_tag[1:])] = entry.value
    else:
        pass

# function: find the ld_sd_queue entry of a ROB entry
def find_ldsd_entry(ld_sd_queue, ROB_tag):
    for element in ld_sd_queue:
        if element.dest_tag == ROB_tag:
            return element
    return None

# function: commit
# return the list of committed ROB entries
def commit(ROB, reg_int, reg_fp, cycle, instructions, issue_width,
           ld_sd_queue, ld_sd_mem, time_ld_sd_mem):
    committed = []
    for i in range(issue_width):
        if len(ROB)==0:
            break
        head = ROB[0]
        op = instructions[head.PC].split(' ')[0]
        if (op=='Bne')|(op=='Beq'):
            # resolved in an earlier cycle
            if (len(head.exe)<2) or (head.exe[-1]>=cycle):
                break
        elif op=='Sd':
            entry = find_ldsd_entry(ld_sd_queue, head.ROB_tag)
            # address and data ready, memory port free
            if (entry.ready==0) or ((type(entry.data)!=int)&(type(entry.data)!=float)) or (ld_sd_mem.busy==1):
                break
            # dequeue the Sd and write memory
            ld_sd_queue.remove(entry)
            put_entry_into_ld_sd_mem(ld_sd_mem, entry)
            head.mem.extend([cycle, cycle+time_ld_sd_mem-1])
        else:
            # broadcasted in an earlier cycle
            if (len(head.cdb)==0) or (head.cdb[0]>=cycle):
                break
            modify_arch_reg(head, reg_int, reg_fp)
        head.commit.append(cycle)
        committed.append(ROB.popleft())
    return committed
