# Qing 
# 26th May 2017

''' 
1. Ld forward check from Sd in ld_sd_queue
    -- search older Sd instructions from nearest to farthest
    -- an older Sd with unknown address blocks the Ld (conservative disambiguation)
    -- forwarding takes 1 cycle
2. fetch new Ld instruction into ld_sd_mem (single-ported, non-pipelined)
    -- Ld is removed from ld_sd_queue once it is sent to memory
    -- Sd instructions are sent to ld_sd_mem by the commit stage (commit.py)
3. execute LD/SD instruction in ld_sd_mem
    -- Ld data is put into results_buffer when the access finishes
    -- Sd data is written into memory when the access finishes
'''
from init import fu_result

# function: forward check from older Sd instructions
# return ('forward', data), ('wait', None) or ('memory', None)
def forward_check_from_sd(ld_sd_queue, index):
    for i in reversed(range(index)):
        if (ld_sd_queue[i].op=='Sd'):
            # unresolved store address
            if ld_sd_queue[i].ready == 0:
                return 'wait', None
            if (ld_sd_queue[i].address == ld_sd_queue[index].address):
                # nearest matching Sd already has its data
                if (type(ld_sd_queue[i].data)==int)|(type(ld_sd_queue[i].data)==float):
                    return 'forward', ld_sd_queue[i].data
                return 'wait', None
    return 'memory', None

# function: find ROB entry by tag
def find_ROB_entry(ROB, tag):
    for index in range(len(ROB)):
        if ROB[index].ROB_tag == tag:
            break
    return index

# function: put entry into ld_sd_mem
def put_entry_into_ld_sd_mem(ld_sd_mem, entry):
    ld_sd_mem.busy = 1
    ld_sd_mem.cycle = 0
    ld_sd_mem.address = entry.address
    ld_sd_mem.dest_tag = entry.dest_tag
    ld_sd_mem.op = entry.op
    if ld_sd_mem.op == 'Sd':
        ld_sd_mem.data = entry.data

# function: mem 
def mem(ld_sd_queue, ld_sd_mem, time_ld_sd_mem, results_buffer, 
        memory, ROB, cycle):
    '''look forward check for all Ld instructions'''
    remove_list = []
    for index in range(len(ld_sd_queue)):
        element = ld_sd_queue[index]
        if (element.op=='Ld')&(element.ready==1):
            status, data = forward_check_from_sd(ld_sd_queue, index)
            if status == 'forward':
                # Ld gets data 
                results_buffer.append(fu_result())
                results_buffer[-1].value = data
                results_buffer[-1].dest_tag = element.dest_tag
                # remove the Ld instruction
                remove_list.append(element)
                # write mem cylce in ROB
                ROB[find_ROB_entry(ROB, element.dest_tag)].mem.append(cycle)
    # remove lookforwared Ld
    for element in remove_list:
        ld_sd_queue.remove(element)

    '''fetch new Ld instruction into ld_sd_mem'''
    if ld_sd_mem.busy==0:
        for index in range(len(ld_sd_queue)):
            # ready Ld, all older Sd addresses known and none matching
            if (ld_sd_queue[index].op=='Ld')&(ld_sd_queue[index].ready==1):
                if forward_check_from_sd(ld_sd_queue, index)[0] == 'memory':
                    put_entry_into_ld_sd_mem(ld_sd_mem, ld_sd_queue[index])
                    ld_sd_queue.remove(ld_sd_queue[index])
                    break 

    '''ld_sd_mem execution'''
    if ld_sd_mem.busy == 1:
        # write mem starting cycle (Sd cycles are written at commit)
        if (ld_sd_mem.cycle == 0)&(ld_sd_mem.op == 'Ld'):
            index = find_ROB_entry(ROB, ld_sd_mem.dest_tag)
            ROB[index].mem.extend([cycle, cycle+time_ld_sd_mem-1])
        # cycle ++
        ld_sd_mem.cycle +=1
        # get the data for Ld or reach the memory for Sd
        if ld_sd_mem.cycle == time_ld_sd_mem:
            ld_sd_mem.busy = 0
            if ld_sd_mem.op == 'Ld': 
                # put Ld data into results_buffer
                results_buffer.append(fu_result())
                results_buffer[-1].value = memory[ld_sd_mem.address]
                results_buffer[-1].dest_tag = ld_sd_mem.dest_tag
            # put data into memory for Sd
            else:
                memory[ld_sd_mem.address]=ld_sd_mem.data
