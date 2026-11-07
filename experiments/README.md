# Original-code evaluation: latency first

This `experiments/` suite imports **unmodified** `src/parallelQuicksort.c`, renaming only its `main`. The measured calls are the original `quicksort`, `parallelQuicksort` and libc `qsort` implementations. The previous `src/quicksort_bench.c` from an earlier package is NOT used here.

## Experiments

1. **Correctness**: compare each output to independently sorted copy (exact equality) and log failures/timeouts. Smoke covers zero, singleton, small arrays, distributions and seeds.
2. **Latency vs size**: 1K–2M elements, `seq`, `par`, `libc`. Monotonic wall time in milliseconds, seeds and repetitions, shuffled run order. Core experimental question: is parallel faster?
3. **Parallel latency scaling**: restrict affinity to 1,2,4,8,16 logical CPUs; vary parallel recursion depth 0–4. Note the original parallel program still creates many threads even if cores restricted.
4. **Workload sensitivity**: random, sorted, reversed, equal, few unique, nearly sorted, organ pipe. Restrict especially pathological distributions to <=100K elements.
5. **Resource overhead**: each measurement includes user+system CPU time, peak process RSS and voluntary/involuntary context switches from `getrusage`. Peak RSS may include input generation/oracle memory, so compare like-sized workloads; it does not isolate algorithm-only allocation.
6. **Compiler and reproducibility**: use `--optimization=-O0` or `-O2` or `-O3`; controlled input seeds and original pivot RNG initialization. Original `rand()` from multiple threads means results need not be bitwise deterministic under scheduling. Record host, compiler, affinity, Slurm allocation, configs.

### Commands

On the project directory:

```bash
sbatch experiments/jubail_smoke.sbatch
sbatch experiments/jubail_latency.sbatch
sbatch experiments/jubail_workloads.sbatch
```

Or manually (no batch system needed):

```bash
python3 experiments/runner.py --mode smoke
python3 experiments/runner.py --mode latency --cores 4 --reps 3
python3 experiments/runner.py --mode scaling --cores 1,2,4 --levels 0,1,2,3
python3 experiments/runner.py --mode resources --cores 1,2,4
python3 experiments/runner.py --mode smoke --optimization=-O0
python3 experiments/runner.py --mode smoke --sanitizer asan --cores 1 --levels 0,1
```

Use **separate submissions for optimization comparisons**, do not overlap heavy CPU experiments on the same node. Optionally increase `--reps 30` and/or `--seeds` for final studies but estimate run count first and avoid massive job arrays. `full` has many thousands of configurations and is not the recommended first job.

### Slurm note

Partition/account are intentionally **not hardcoded**: site allocation varies. Check `sinfo` and `sacctmgr show assoc user=$USER` if `sbatch` rejects default allocation; add the correct `#SBATCH --partition=...` and `--account=...` directives **only after checking your own account**. This is a single-node pthread workload, not MPI. The available CPUs are restricted within Slurm's allocation using `taskset`, so execution on different core counts remains within assigned CPUs. Hardware comparisons need separate allocations/nodes and collected metadata: changing affinity alone does **not** test a different CPU model.

### Data and interpretation

Raw CSV + metadata JSON generated in `results/`. Summary is calculated by `experiments/analyze.py`. Median latency and p95 are descriptive; the mean 95% intervals use a normal approximation and should not be interpreted as rigorous paired confidence intervals (for final results, use bootstrapping by paired seed and repetition). CPU cost, memory and context switch counts provide mechanisms behind observed latency behavior. Parallel safety: the original source's use of libc `rand()` concurrently may be unsafe/non-reproducible; a clean ThreadSanitizer check on supported hardware is an extension and should be interpreted carefully, not proof of safety.

The original 2014 journal records an incorrect parallel sorting result and past segfaults, important motivations for correctness and stress tests. Never silently discard failures or compare only successful results.
