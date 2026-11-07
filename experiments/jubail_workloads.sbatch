#!/bin/bash
#SBATCH --job-name=qs-workloads
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=04:00:00
#SBATCH --output=qs-workloads-%j.out
#SBATCH --error=qs-workloads-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
python3 experiments/runner.py --mode workloads --output "results/workloads_${SLURM_JOB_ID}.csv"
python3 experiments/analyze.py "results/workloads_${SLURM_JOB_ID}.csv" --output "results/workloads_summary_${SLURM_JOB_ID}.csv"
echo 'WORKLOAD EXPERIMENT SUCCESS'
