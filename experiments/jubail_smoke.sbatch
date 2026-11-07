#!/bin/bash
#SBATCH --job-name=qs-smoke
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:15:00
#SBATCH --output=qs-smoke-%j.out
#SBATCH --error=qs-smoke-%j.err
set -euo pipefail
cd "${SLURM_SUBMIT_DIR}"
python3 experiments/runner.py --mode smoke --output "results/smoke_${SLURM_JOB_ID}.csv"
python3 experiments/analyze.py "results/smoke_${SLURM_JOB_ID}.csv" --output "results/smoke_summary_${SLURM_JOB_ID}.csv"
echo 'SMOKE TEST SUCCESS'
