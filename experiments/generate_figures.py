#!/usr/bin/env python3
"""SMPE Parallel Quicksort figures from the existing Jubail raw CSV files.
Run from project root: python3 experiments/generate_smpe_figures.py
"""
import csv, math, statistics
from collections import defaultdict
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
RESULTS=ROOT/'results'
OUT=RESULTS/'figures'
OUT.mkdir(parents=True,exist_ok=True)
DATASETS={
 'latency':'extended_19277497.csv',
 'scaling':'scaling_O2_19348428.csv',
 'workloads':'workloads_O2_19348429.csv',
 'resources':'resources_O2_19348430.csv',
 'O0':'optimizer_O0_19348431.csv',
 'O2':'optimizer_O2_19348432.csv',
 'O3':'optimizer_O3_19348433.csv',
}
def load(name):
 path=RESULTS/DATASETS[name]
 if not path.exists(): raise FileNotFoundError(f'Missing {path}; copy all results before running')
 with path.open(newline='') as f: rows=list(csv.DictReader(f))
 rows=[r for r in rows if r['correct']=='1' and r['returncode']=='0']
 for r in rows:
  for k in ('n','cores','level','seed','rep'):r[k]=int(r[k])
  for k in ('wall_ms','user_cpu_ms','sys_cpu_ms','peak_rss_kb','voluntary_ctx','involuntary_ctx'):r[k]=float(r[k])
 return rows
D={k:load(k) for k in DATASETS}
def med(rows,key='wall_ms'):return statistics.median(r[key] for r in rows)
def group(rows,keys):
 d=defaultdict(list)
 for r in rows:d[tuple(r[k] for k in keys)].append(r)
 return d
def save(fig,name):
 fig.tight_layout()
 for ext in ('png','pdf'):fig.savefig(OUT/f'{name}.{ext}',dpi=220)
 plt.close(fig)
 print('Created',name)
def setup(ax,xlabel,ylabel,title,logx=False,logy=False):
 ax.set(xlabel=xlabel,ylabel=ylabel,title=title)
 if logx:ax.set_xscale('log')
 if logy:ax.set_yscale('log')
 ax.grid(alpha=.25)

# Use a single host for each comparison; report hosts in a text file.
hosts={k:sorted(set(r['host'] for r in rows)) for k,rows in D.items()}
(OUT/'dataset_hosts.txt').write_text('\n'.join(f'{k}: {", ".join(v)}' for k,v in hosts.items())+'\n')

# 1. Latency vs size (fixed cores, random, -O2, parallel depth 3)
rows=D['latency']; host=hosts['latency'][0]
g=group([r for r in rows if r['host']==host and r['distribution']=='random' and r['cores']==4],('algo','level','n'))
fig,ax=plt.subplots(figsize=(8,5))
for algo,level,label in [('seq',0,'Sequential'),('libc',0,'libc qsort'),('par',3,'Parallel (depth 3)')]:
 pts=sorted((n,med(rs)) for (a,l,n),rs in g.items() if a==algo and l==level)
 if pts:ax.plot(*zip(*pts),marker='o',label=label)
setup(ax,'Array size (elements)','Median latency (ms)',f'Latency vs array size ({host}, 4 CPUs, -O2)',True,True);ax.legend();save(fig,'01_latency_vs_size')

# 2. Speedup vs size, comparing within same size, host and core allocation
fig,ax=plt.subplots(figsize=(8,5))
base={(n):med(rs) for (a,l,n),rs in g.items() if a=='seq' and l==0}
for level in [0,1,2,3,4]:
 pts=sorted((n,base[n]/med(rs)) for (a,l,n),rs in g.items() if a=='par' and l==level and n in base and med(rs)>0)
 if pts:ax.plot(*zip(*pts),marker='o',label=f'Depth {level}')
ax.axhline(1,ls='--',color='gray',lw=1)
setup(ax,'Array size (elements)','Speedup: sequential / parallel',f'Speedup vs size ({host}, 4 CPUs)',True);ax.legend(ncol=2);save(fig,'02_speedup_vs_size')

# 3. Scaling speedup vs available cores at n=2M, depth 3
rows=D['scaling'];host=hosts['scaling'][0];n=2000000;depth=3
g=group([r for r in rows if r['host']==host and r['n']==n and r['distribution']=='random'],('algo','level','cores'))
fig,ax=plt.subplots(figsize=(8,5));pts=[]
for c in [1,2,4,8,16]:
 if ('seq',0,c) in g and ('par',depth,c) in g:
  pts.append((c,med(g['seq',0,c])/med(g['par',depth,c])))
if pts:
 ax.plot(*zip(*pts),marker='o',label='Observed speedup')
 ax.plot([x for x,y in pts],[x for x,y in pts],ls='--',label='Ideal linear scaling')
setup(ax,'Available CPU cores','Speedup vs sequential (same affinity)',f'CPU scalability (N={n:,}, depth {depth}, {host})');ax.legend();save(fig,'03_scalability_speedup')
fig,ax=plt.subplots(figsize=(8,5))
if pts:ax.plot([x for x,y in pts],[100*y/x for x,y in pts],marker='o')
setup(ax,'Available CPU cores','Nominal efficiency (%)',f'Nominal speedup / allocated cores ({host})');save(fig,'04_parallel_efficiency')

# 4. Workload sensitivity, compare fixed size and depth
rows=D['workloads'];host=hosts['workloads'][0];n=10000;cores=4;depth=3
g=group([r for r in rows if r['host']==host and r['n']==n and r['cores']==cores],('distribution','algo','level'))
dists=['random','sorted','reverse','equal','few_unique','nearly_sorted','organ_pipe']
fig,ax=plt.subplots(figsize=(10,5));labels=[];se=[];pa=[]
for dist in dists:
 if (dist,'seq',0) in g and (dist,'par',depth) in g:
  labels.append(dist);se.append(med(g[dist,'seq',0]));pa.append(med(g[dist,'par',depth]))
if labels:
 x=list(range(len(labels)));ax.bar([i-.2 for i in x],se,width=.4,label='Sequential');ax.bar([i+.2 for i in x],pa,width=.4,label=f'Parallel depth {depth}');ax.set_xticks(x,labels,rotation=25,ha='right')
setup(ax,'Input distribution','Median latency (ms)',f'Input sensitivity (N={n:,}, {host})');ax.legend();save(fig,'05_input_sensitivity')

# 5. Compiler optimization, paired within each compiler dataset (no cross-node latency claims)
fig,ax=plt.subplots(figsize=(8,5));sizes=[100,1000,10000,100000,1000000,2000000]
for opt in ['O0','O2','O3']:
 rows=D[opt];host=hosts[opt][0]
 g=group([r for r in rows if r['host']==host and r['cores']==4 and r['distribution']=='random'],('algo','level','n'))
 pts=[]
 for n in sizes:
  if ('seq',0,n) in g and ('par',3,n) in g:pts.append((n,med(g['seq',0,n])/med(g['par',3,n])))
 if pts:ax.plot(*zip(*pts),marker='o',label=f'-{opt} ({host})')
ax.axhline(1,color='gray',ls='--',lw=1)
setup(ax,'Array size (elements)','Speedup vs same-optimization sequential', 'Compiler optimization: within-run speedup',True);ax.legend();save(fig,'06_compiler_effects')

# 6. Resource use, fixed size and depth across core allocations
rows=D['resources'];host=hosts['resources'][0];n=1000000;depth=3
g=group([r for r in rows if r['host']==host and r['n']==n and r['distribution']=='random' and r['algo']=='par' and r['level']==depth],('cores',))
fig,axes=plt.subplots(2,2,figsize=(11,8));metrics=[('wall_ms','Wall latency (ms)'),('user_cpu_ms','User CPU time (ms)'),('peak_rss_kb','Peak RSS (KB)'),('voluntary_ctx','Voluntary context switches')]
for ax,(metric,label) in zip(axes.flat,metrics):
 pts=sorted((c,med(rs,metric)) for (c,),rs in g.items());
 if pts:ax.plot(*zip(*pts),marker='o')
 setup(ax,'Available CPUs',label,f'{label} vs CPU count')
fig.suptitle(f'Resource trade-offs (N={n:,}, parallel depth {depth}, {host})');save(fig,'07_resource_consumption')

# Machine-readable descriptive summaries for all raw datasets
with (OUT/'descriptive_summary.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['dataset','host','optimization','algo','n','distribution','level','cores','samples','median_wall_ms','mean_wall_ms','stdev_wall_ms','median_user_cpu_ms','median_sys_cpu_ms','median_peak_rss_kb','median_voluntary_ctx','median_involuntary_ctx'])
 for dataset,rows in D.items():
  gg=group(rows,('host','optimization','algo','n','distribution','level','cores'))
  for key,rr in sorted(gg.items()):
   wall=[r['wall_ms'] for r in rr]
   w.writerow([dataset,*key,len(rr),statistics.median(wall),statistics.mean(wall),statistics.stdev(wall) if len(wall)>1 else 0,*[med(rr,k) for k in ('user_cpu_ms','sys_cpu_ms','peak_rss_kb','voluntary_ctx','involuntary_ctx')]])
print('DONE: figures and summary saved in',OUT)
