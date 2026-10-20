
// my_predictor.h
// This file contains a sample gshare_predictor class.
// It is a simple 32,768-entry gshare with a history length of 15.

class gshare_update : public branch_update {
public:
	unsigned int index;
};

class gshare_predictor : public branch_predictor {
public:
#define HISTORY_LENGTH	15
#define TABLE_BITS	15
	gshare_update u;
	branch_info bi;
	unsigned int history;
	unsigned char tab[1<<TABLE_BITS];

	gshare_predictor (void) : history(0) { 
		memset (tab, 0, sizeof (tab));
	}

	branch_update *predict (branch_info & b) {
		bi = b;
		if (b.br_flags & BR_CONDITIONAL) {
			u.index = 
				  (history << (TABLE_BITS - HISTORY_LENGTH)) 
				^ (b.address & ((1<<TABLE_BITS)-1));
			u.direction_prediction (tab[u.index] >> 1);
		} else {
			u.direction_prediction (true);
		}
		u.target_prediction (0);
		return &u;
	}

	void update (branch_update *u, bool taken, unsigned int target) {
		if (bi.br_flags & BR_CONDITIONAL) {
			unsigned char *c = &tab[((gshare_update*)u)->index];
			if (taken) {
				if (*c < 3) (*c)++;
			} else {
				if (*c > 0) (*c)--;
			}
			history <<= 1;
			history |= taken;
			history &= (1<<HISTORY_LENGTH)-1;
		}
	}
};

//
// Pentium M hybrid branch predictors
// This class implements a simple hybrid branch predictor based on the Pentium M branch outcome prediction units.
// Instead of implementing the complete Pentium M branch outcome predictors, the class below implements a hybrid
// predictor that combines a bimodal predictor and a global predictor.
//
// Structure (after Uzelac & Milenkovic, "Experiment Flows and Microbenchmarks for
// Reverse Engineering of Branch Predictor Structures", ISPASS 2009):
//
//   Bimodal table   : 4096 x 2-bit counters, index = IP[11:0]
//   Global predictor: 512 sets x PM_GLOBAL_WAYS ways (4 by default, 2 allowed),
//                     each entry = {valid, 6-bit tag, 2-bit counter}, LRU replacement
//                     HASH  = IP[14:0] XOR GHR[14:0]
//                     index = HASH[14:6], tag = HASH[5:0]
//   Final outcome   : global prediction on a global hit, bimodal prediction otherwise
//
// The path information register (PIR) is replaced by a plain global history
// register of conditional branch outcomes, as permitted by the assignment.
// The loop predictor and all target prediction (BTB/iBTB) are not modelled.
//
// Every PM_* parameter can be overridden on the compiler command line
// (e.g. -DPM_GLOBAL_WAYS=2) to reproduce the experiments in the report.

#ifndef PM_BIMODAL_BITS
#define PM_BIMODAL_BITS         12      // 4096 bimodal counters
#endif
#ifndef PM_SET_BITS
#define PM_SET_BITS             9       // 512 sets in the global predictor
#endif
#ifndef PM_TAG_BITS
#define PM_TAG_BITS             6       // 6-bit partial tag
#endif
#ifndef PM_GLOBAL_WAYS
#define PM_GLOBAL_WAYS          4       // 4-way (Pentium M); 2-way also allowed
#endif
#ifndef PM_HIST_BITS
#define PM_HIST_BITS            (PM_SET_BITS + PM_TAG_BITS)     // 15-bit hash / history
#endif
#ifndef PM_ALLOC_ON_MISPREDICT
#define PM_ALLOC_ON_MISPREDICT  1       // allocate global entry only when bimodal was wrong
#endif
#ifndef PM_USE_GLOBAL
#define PM_USE_GLOBAL           1       // 0 = bimodal-only predictor (for comparison)
#endif

#define PM_BIMODAL_SIZE         (1 << PM_BIMODAL_BITS)
#define PM_NUM_SETS             (1 << PM_SET_BITS)
#define PM_HASH_MASK            ((1u << PM_HIST_BITS) - 1)

class pm_update : public branch_update {
public:
        unsigned int index;             // bimodal table index
        unsigned int set;               // global predictor set index
        unsigned int tag;               // global predictor tag
        int way;                        // way that hit in the global predictor, -1 on miss
        bool bimodal_pred;              // bimodal outcome prediction
};

class pm_predictor : public branch_predictor {
public:
        struct global_entry {
                bool valid;
                unsigned char tag;
                unsigned char ctr;      // 2-bit saturating counter
                unsigned char lru;      // recency rank: 0 = MRU, PM_GLOBAL_WAYS-1 = LRU
        };

        pm_update u;
        branch_info bi;
        unsigned int ghr;                                       // global history register
        unsigned char bimodal[PM_BIMODAL_SIZE];                 // 2-bit counters
        global_entry global[PM_NUM_SETS][PM_GLOBAL_WAYS];       // set-associative global predictor

        pm_predictor (void) : ghr(0) {
                // weakly not-taken
                memset (bimodal, 1, sizeof (bimodal));
                for (int s = 0; s < PM_NUM_SETS; s++)
                        for (int w = 0; w < PM_GLOBAL_WAYS; w++) {
                                global[s][w].valid = false;
                                global[s][w].tag = 0;
                                global[s][w].ctr = 1;
                                global[s][w].lru = w;
                        }
        }

        static void update_counter (unsigned char *c, bool taken) {
                if (taken) {
                        if (*c < 3) (*c)++;
                } else {
                        if (*c > 0) (*c)--;
                }
        }

        // make 'way' the most recently used way of 'set'
        void touch (unsigned int set, int way) {
                unsigned char old = global[set][way].lru;
                for (int w = 0; w < PM_GLOBAL_WAYS; w++)
                        if (global[set][w].lru < old) global[set][w].lru++;
                global[set][way].lru = 0;
        }

        // invalid way if there is one, otherwise the least recently used way
        int victim (unsigned int set) {
                int lru_way = 0;
                for (int w = 0; w < PM_GLOBAL_WAYS; w++) {
                        if (!global[set][w].valid) return w;
                        if (global[set][w].lru > global[set][lru_way].lru) lru_way = w;
                }
                return lru_way;
        }

        branch_update *predict (branch_info & b) {
                bi = b;
                if (b.br_flags & BR_CONDITIONAL) {
                        // bimodal outcome prediction
                        u.index = b.address & (PM_BIMODAL_SIZE - 1);
                        u.bimodal_pred = bimodal[u.index] >> 1;

                        // global predictor lookup
                        unsigned int hash = (b.address ^ ghr) & PM_HASH_MASK;
                        u.set = hash >> PM_TAG_BITS;
                        u.tag = hash & ((1 << PM_TAG_BITS) - 1);
                        u.way = -1;
#if PM_USE_GLOBAL
                        for (int w = 0; w < PM_GLOBAL_WAYS; w++)
                                if (global[u.set][w].valid && global[u.set][w].tag == u.tag) {
                                        u.way = w;
                                        break;
                                }
#endif

                        // final prediction: global on a hit, bimodal otherwise
                        if (u.way >= 0)
                                u.direction_prediction (global[u.set][u.way].ctr >> 1);
                        else
                                u.direction_prediction (u.bimodal_pred);
                } else {
                        // unconditional branches are always taken
                        u.direction_prediction (true);
                }

                // branch target prediction is not implemented
                u.target_prediction (0);
                return &u;
        }

        void update (branch_update *bu, bool taken, unsigned int target) {
                if (!(bi.br_flags & BR_CONDITIONAL)) return;
                pm_update *p = (pm_update *) bu;

                // the bimodal table is always trained
                update_counter (&bimodal[p->index], taken);

#if PM_USE_GLOBAL
                if (p->way >= 0) {
                        // global hit: train the hitting entry
                        update_counter (&global[p->set][p->way].ctr, taken);
                        touch (p->set, p->way);
                } else if (!PM_ALLOC_ON_MISPREDICT || p->bimodal_pred != taken) {
                        // global miss: allocate a new entry in the LRU way
                        int w = victim (p->set);
                        global[p->set][w].valid = true;
                        global[p->set][w].tag = p->tag;
                        global[p->set][w].ctr = taken ? 2 : 1;  // weakly toward the outcome
                        touch (p->set, w);
                }
#endif

                // shift the outcome into the global history register
                ghr = ((ghr << 1) | taken) & PM_HASH_MASK;
        }

};
/*
//
// Complete Pentium M branch predictors for extra credit
// This class implements the complete Pentium M branch prediction units. 
// It implements both branch target prediction and branch outcome predicton. 
class cpm_update : public branch_update {
public:
        unsigned int index;
};

class cpm_predictor : public branch_predictor {
public:
        cpm_update u;

        cpm_predictor (void) {
        }

        branch_update *predict (branch_info & b) {
            u.direction_prediction (true);
            u.target_prediction (0);
            return &u;
        }

        void update (branch_update *u, bool taken, unsigned int target) {
        }

};
*/
