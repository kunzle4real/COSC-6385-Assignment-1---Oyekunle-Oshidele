# Assignment 1: Pentium M Branch Predictor
# Oyekunle Oshidele(2143251)

This repository implements the branch outcome (direction) part of the Pentium M branch
predictor in the CBP2 branch prediction simulation infrastructure. The predictor combines:

- a **bimodal table** of 4096 2-bit counters indexed by `IP[11:0]`
- a **global predictor** with 512 sets × 4 ways. Each entry holds a valid bit, a 6-bit tag
  and a 2-bit counter, and the sets use LRU replacement. It is indexed by
  `HASH[14:6]` and tagged by `HASH[5:0]`, where `HASH = IP[14:0] XOR GHR[14:0]`.

The final prediction comes from the global predictor when it hits and from the bimodal
table when it misses. The loop predictor, PIR hashing and branch target prediction are not implemented, as the assignment allows.


## Build

Requirements: `g++`, `make` and `bzip2` (the traces are `.bz2`). On Windows, use WSL.

```sh
cd src
make            # builds ./predict (and ./predict_extra_credit)
```

## Run

From the top-level directory:

```sh
./run traces        # original csh script (needs csh and dc)
./run.sh traces     # bash version, same output format
```

To run a single trace:

```sh
./src/predict traces/164.gzip/gzip.trace.bz2
# 12.436 MPKI
```

Expected result with the default configuration (4-way global predictor):
`average MPKI: 5.848`.

## Configuration

The predictor parameters are macros in `src/my_predictor.h`. 


To reproduce every result in the report:

```sh
./experiments.sh traces > results.csv
```

## References

- V. Uzelac and A. Milenković, "Experiment Flows and Microbenchmarks for Reverse Engineering
  of Branch Predictor Structures," ISPASS 2009.
- CBP2 (2nd Championship Branch Prediction) simulation infrastructure, `cbp2-infrastructure-v2`.
- No external cache code was used. The set-associative table and its LRU replacement are
  written from scratch in `my_predictor.h`.
