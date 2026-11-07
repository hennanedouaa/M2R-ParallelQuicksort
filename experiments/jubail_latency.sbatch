#!/bin/bash
#SBATCH --job-name=qs-latency
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=04:00:00
#SBATCH --output=qs-latency-%j.out
#SBATCH --error=qs-latency-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
python3 experiments/runner.py --mode latency --cores 16 --reps 3 --output "results/latency_${SLURM_JOB_ID}.csv"
python3 experiments/runner.py --mode scaling --output "results/scaling_${SLURM_JOB_ID}.csv"
python3 experiments/analyze.py "results/latency_${SLURM_JOB_ID}.csv" "results/scaling_${SLURM_JOB_ID}.csv" --output "results/latency_scaling_summary_${SLURM_JOB_ID}.csv"
echo 'LATENCY EXPERIMENT SUCCESS'
