#!/usr/bin/env python3
"""Latency figures from summary CSV. Requires matplotlib (optional)."""
import argparse,csv,collections,pathlib
import matplotlib.pyplot as plt
p=argparse.ArgumentParser();p.add_argument('summary');p.add_argument('--outdir',default='results/figures');args=p.parse_args()
rows=list(csv.DictReader(open(args.summary,newline='')))
out=pathlib.Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
# Avoid mixing hosts/optimizations/workloads in the same plot.
settings=collections.defaultdict(list)
for r in rows:
 if r['distribution']=='random':settings[(r['host'],r['optimization'],r['cores'],r['algo'],r['level'])].append(r)
if not settings:raise SystemExit('No random-input latency summaries found')
fig,ax=plt.subplots(figsize=(9,5))
for key,group in sorted(settings.items()):
 group.sort(key=lambda r:int(r['n']))
 label=f'{key[0]} {key[1]} {key[3]} level={key[4]} cores={key[2]}'
 ax.plot([int(r['n']) for r in group],[float(r['median_ms']) for r in group],marker='o',label=label)
ax.set_xlabel('Input size (elements)');ax.set_ylabel('Median sorting latency (ms)')
ax.set_title('Original implementations: latency vs input size')
ax.grid(alpha=.25);ax.legend(fontsize=7);fig.tight_layout()
fig.savefig(out/'latency_vs_size.png',dpi=160);plt.close(fig)
print('Saved',out/'latency_vs_size.png')
