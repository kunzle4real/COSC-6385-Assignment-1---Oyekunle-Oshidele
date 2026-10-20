# Tomasulo Algorithm Implementation for multi-issue
# Assignment 1

* includes instructions of int_add, fp_add, fp_multi, load, store, branch (Bne/Beq);
* implements ROB, RAT, load-store-queue;
* implements out-of-order processing and memory disambiguation; 
* issues, writes back and commits 1-4 instructions per cycle (in order);


How to run:
```
cd code;
python main.py                                    # runs test_case.txt (Issue width = 3)
python main.py ../tests/test3_branch_loop.txt     # any test case file
python main.py ../tests/test3_branch_loop.txt -w 2  # override the issue width (1-4)
```

Input file format (case insensitive, commas optional):
```
               # of rs         Cycles in EX    Cycles in Mem   # of FUs
Integer adder   4               1                               1
FP adder        3               4                               1
FP multiplier   2               15                              1
Load/store unit 5               1               5               1
ROB entries = 64
Issue width = 3
R1=12, R2=32, F20=3.0
Mem[4]=3.0, Mem[8]=2.0
Ld F2 0(R1)
Add.d F6 F4 F6
...
```


Tests cases:
```
cd tests;
python run_tests.py     # runs every test*.txt with issue width 1, 2, 3 and 4
```
Each run is checked against a sequential reference interpreter (reference.py) for the
final registers, memory and committed instruction stream, and against the pipeline
rules (in-order issue/commit, at most issue-width issues/write-backs/commits per cycle,
ISSUE < EX < MEM < WB < COMMIT). Outputs are written to tests/results/.

Files needed:
```
code/            modified Tomasulo Algorithm
tests/           test cases, reference interpreter, test runner, results
README.md        How to run code
REPORT.pdf/      REPORT.pdf (report as PDF) and its LaTeX source REPORT.tex
```
