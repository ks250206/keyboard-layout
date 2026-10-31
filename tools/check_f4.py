#!/usr/bin/env python3
"""Recompute the frozen F4 scores in a temporary copy; never overwrite results."""
import csv,math,os,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def compare(actual,expected):
    a=list(csv.DictReader(actual.open(encoding='utf-8')));b=list(csv.DictReader(expected.open(encoding='utf-8')))
    if len(a)!=len(b):raise AssertionError(f'Row count: {len(a)} vs {len(b)}')
    ma={(r['layout'],r['group']):r for r in a};mb={(r['layout'],r['group']):r for r in b}
    if ma.keys()!=mb.keys():raise AssertionError('Case keys changed')
    for key,ra in ma.items():
        rb=mb[key]
        if ra.keys()!=rb.keys():raise AssertionError('CSV columns changed')
        for col,x in ra.items():
            y=rb[col]
            try:xf,yf=float(x),float(y)
            except ValueError:
                if x!=y:raise AssertionError((key,col,x,y))
            else:
                if not(math.isfinite(xf) and math.isfinite(yf) and math.isclose(xf,yf,abs_tol=1e-8,rel_tol=1e-11)):raise AssertionError((key,col,x,y))
    return len(a)
def main():
    with tempfile.TemporaryDirectory(prefix='nova-f4-check-') as temp:
        dest=Path(temp)
        for directory in ('src','data','layouts','results'):shutil.copytree(ROOT/directory,dest/directory,ignore=shutil.ignore_patterns('__pycache__','*.nbc','*.nbi'))
        subprocess.run([sys.executable,str(dest/'src/optimize_v4.py'),'--report'],env={**os.environ,'OPENBLAS_NUM_THREADS':'1'},check=True,stdout=subprocess.DEVNULL)
        cases=compare(dest/'results/v4/scores.csv',ROOT/'results/v4/scores.csv')
    print(f'PASS: F4 {cases} cases recomputed; frozen files were not modified.')
if __name__=='__main__':main()
