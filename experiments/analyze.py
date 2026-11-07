#!/usr/bin/env python3
"""Summarize raw latency measurements (standard library only)."""
import argparse,csv,collections,math,statistics,pathlib,sys
p=argparse.ArgumentParser();p.add_argument('files',nargs='+');p.add_argument('--output',default='results/summary.csv');args=p.parse_args()
groups=collections.defaultdict(list);fails=0;total=0
for file in args.files:
 for row in csv.DictReader(open(file,newline='')):
  total+=1
  if row['returncode']!='0' or row['correct']!='1':fails+=1;continue
  key=tuple(row[k] for k in ('host','optimization','algo','n','distribution','level','cores'))
  groups[key].append(float(row['wall_ms']))
path=pathlib.Path(args.output);path.parent.mkdir(exist_ok=True,parents=True)
fields=['host','optimization','algo','n','distribution','level','cores','samples','median_ms','mean_ms','stdev_ms','p95_ms','mean_ci95_low','mean_ci95_high']
with path.open('w',newline='') as f:
 w=csv.writer(f);w.writerow(fields)
 for key,vals in sorted(groups.items()):
  vals.sort();cnt=len(vals);avg=statistics.mean(vals);sd=statistics.stdev(vals) if cnt>1 else 0.0
  p95=vals[min(cnt-1,math.ceil(.95*cnt)-1)]
  # Normal approximation appropriate as descriptive CI for moderate n; use bootstrap for final inference.
  margin=1.96*sd/math.sqrt(cnt) if cnt>1 else float('nan')
  w.writerow([*key,cnt,statistics.median(vals),avg,sd,p95,avg-margin,avg+margin])
print(f'{total} rows, {fails} failed, {len(groups)} grouped configurations => {path}')
