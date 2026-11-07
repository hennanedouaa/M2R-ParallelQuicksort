#!/usr/bin/env python3
"""Reproducible experiments for ORIGINAL Parallel Quicksort (Python stdlib only)."""
import argparse, csv, datetime, json, os, pathlib, platform, random, shutil, subprocess, sys, time

FIELDS=['run_id','timestamp_utc','host','compiler','optimization','algo','n','distribution','seed','level','cores','rep','wall_ms','correct','user_cpu_ms','sys_cpu_ms','peak_rss_kb','voluntary_ctx','involuntary_ctx','returncode','error']
OUTFIELDS=['algo','n','distribution','seed','level','wall_ms','correct','user_cpu_ms','sys_cpu_ms','peak_rss_kb','voluntary_ctx','involuntary_ctx']
ROOT=pathlib.Path(__file__).resolve().parents[1]

def execute(cmd, timeout=60, check=True):
    return subprocess.run(cmd, text=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=check)

def compile_binary(optimization, sanitizer='none'):
    build=ROOT/'experiments'/'build';build.mkdir(exist_ok=True)
    cc=os.environ.get('CC','gcc')
    suffix=optimization.replace('-','') + ('_'+sanitizer if sanitizer!='none' else '')
    binary=build/f'original_{suffix}'
    flags=['-std=c99','-g','-pthread','-Wall','-Wextra',optimization]
    if sanitizer!='none':
        flags+=['-fno-omit-frame-pointer', '-fsanitize='+('address,undefined' if sanitizer=='asan' else 'thread')]
    cmd=[cc,*flags,str(ROOT/'experiments'/'original_harness.c'),'-o',str(binary)]
    proc=execute(cmd,60)
    if proc.stderr:print(proc.stderr,file=sys.stderr)
    return binary,execute([cc,'--version']).stdout.splitlines()[0]

def matrix(args):
    sizes=[int(s) for s in args.sizes.split(',')]; dist=args.distributions.split(','); cores=[int(x) for x in args.cores.split(',')]
    levels=[int(x) for x in args.levels.split(',')]; seeds=[int(x) for x in args.seeds.split(',')]
    if min(sizes)<0 or min(cores)<1 or min(levels)<0 or args.reps<1:raise ValueError('invalid matrix')
    for n in sizes:
      for distribution in dist:
       for seed in seeds:
        for rep in range(args.reps):
         for c in cores:
          for algo in ['seq','libc']:
           yield (algo,n,distribution,seed,0,c,rep)
          for level in levels:
           yield ('par',n,distribution,seed,level,c,rep)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['smoke','latency','scaling','workloads','resources','full'],default='smoke')
    p.add_argument('--sizes');p.add_argument('--distributions');p.add_argument('--cores');p.add_argument('--levels');p.add_argument('--seeds');p.add_argument('--reps',type=int)
    p.add_argument('--optimization',choices=['-O0','-O2','-O3'],default='-O2')
    p.add_argument('--sanitizer',choices=['none','asan','tsan'],default='none')
    p.add_argument('--timeout',type=float,default=40)
    p.add_argument('--max-runs',type=int,default=0,help='0=all')
    p.add_argument('--output',default=None)
    a=p.parse_args()
    allowed=sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else list(range(os.cpu_count() or 1))
    available=len(allowed)
    DEFAULT={
     'smoke': ('0,1,2,100,1000','random,sorted,reverse,equal,few_unique','1,2','0,1,2','1,2','1'),
     'latency':('1000,10000,100000,1000000,2000000','random','4','0,2,3,4','1,2,3,4,5,6,7,8,9,10','3'),
     'scaling':('100000,1000000,2000000','random','1,2,4,8,16','0,1,2,3,4','1,2,3,4,5','3'),
     'workloads':('1000,10000,100000','random,sorted,reverse,equal,few_unique,nearly_sorted,organ_pipe','4','0,2,3','1,2,3,4,5','3'),
     'resources':('10000,100000,1000000','random','1,2,4,8,16','0,2,3,4','1,2,3,4,5','3'),
     'full':('1000,10000,100000,1000000,2000000','random,sorted,reverse,few_unique','1,2,4,8,16','0,2,3,4','1,2,3,4,5,6,7,8,9,10','3')}
    default=DEFAULT[a.mode]
    for key,value in zip(['sizes','distributions','cores','levels','seeds','reps'],default):
        if getattr(a,key) is None:setattr(a,key,int(value) if key=='reps' else value)
    requested=[int(x) for x in a.cores.split(',')]
    usable=[x for x in requested if x<=available]
    if not usable:raise RuntimeError(f'No requested core counts <= CPU affinity allowance {available}')
    if len(usable)!=len(requested):print(f'Skipping core counts > current affinity count {available}: {requested}',file=sys.stderr)
    a.cores=','.join(map(str,usable))
    # Cap pathological equal/low-cardinality cases to avoid quadratic blow-up.
    runs=[t for t in matrix(a) if not (t[2] in ('equal','few_unique','organ_pipe') and t[1]>100000)]
    random.Random(20261107).shuffle(runs)
    if a.max_runs:runs=runs[:a.max_runs]
    binary,cc=compile_binary(a.optimization,a.sanitizer)
    out=pathlib.Path(a.output or str(ROOT/'results'/f'{a.mode}_{datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")}.csv'))
    out.parent.mkdir(parents=True,exist_ok=True)
    metadata=dict(mode=a.mode,host=platform.node(),date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),compiler=cc,optimization=a.optimization,sanitizer=a.sanitizer,affinity_allowed=allowed,platform=platform.platform(),uname=platform.uname()._asdict(),slurm={k:v for k,v in os.environ.items() if k.startswith('SLURM_') and k in ('SLURM_JOB_ID','SLURM_JOB_PARTITION','SLURM_CPUS_PER_TASK','SLURM_JOB_NODELIST')},settings=vars(a),binary=str(binary),total_runs=len(runs))
    (out.with_suffix('.metadata.json')).write_text(json.dumps(metadata,indent=2,default=str))
    print(f'Running {len(runs)} configurations (available CPUs: {available}); saving {out}',flush=True)
    failures=0
    with out.open('w',newline='') as f:
      writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
      for i,(algo,n,distr,seed,level,cores,rep) in enumerate(runs,1):
        # taskset forces a core limit for seq, libc and par consistently.
        cpulist=','.join(map(str,allowed[:cores]))
        cmd=([shutil.which('taskset') or 'taskset','-c',cpulist] if sys.platform=='linux' else [])+[str(binary),algo,str(n),distr,str(seed),str(level)]
        output={k:'' for k in OUTFIELDS};rc=0;err=''
        try:
            proc=execute(cmd,a.timeout,check=False);rc=proc.returncode;err=proc.stderr.strip()[:300]
            values=proc.stdout.strip().splitlines()
            if values and len(values[-1].split(','))==len(OUTFIELDS):output=dict(zip(OUTFIELDS,values[-1].split(',')))
            else:rc=rc or 5;err+=' missing CSV output'
        except subprocess.TimeoutExpired:rc=124;err='timeout'
        except OSError as e:rc=125;err=str(e)
        failed=rc!=0 or output.get('correct')!='1'
        failures+=int(failed)
        row={'run_id':i,'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'host':platform.node(),'compiler':cc,'optimization':a.optimization,'algo':algo,'n':n,'distribution':distr,'seed':seed,'level':level,'cores':cores,'rep':rep,'returncode':rc,'error':err}
        row.update({k:v for k,v in output.items() if k not in row})
        writer.writerow(row);f.flush()
        if i%50==0 or failed or i==len(runs):print(f'{i}/{len(runs)}  failures={failures}  last={algo} n={n} c={cores} level={level} wall_ms={output.get("wall_ms")}',flush=True)
    print(f'DONE: {len(runs)} runs, {failures} failed. Output: {out}',flush=True)
    return 1 if failures else 0

if __name__=='__main__':sys.exit(main())
