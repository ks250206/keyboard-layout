#!/usr/bin/env python3
"""Recompute F5 in an isolated temporary copy, then compare all frozen scores."""
import os,shutil,subprocess,sys,tempfile
from pathlib import Path
from check_f4 import compare
ROOT=Path(__file__).resolve().parents[1]
def main():
    with tempfile.TemporaryDirectory(prefix='nova-f5-check-') as temp:
        dest=Path(temp)
        for directory in ('src','data','layouts','results'):shutil.copytree(ROOT/directory,dest/directory,ignore=shutil.ignore_patterns('__pycache__','*.nbc','*.nbi'))
        subprocess.run([sys.executable,str(dest/'src/optimize_v5.py'),'--evaluate'],env={**os.environ,'OPENBLAS_NUM_THREADS':'1'},check=True)
        cases=compare(dest/'results/v5/scores.csv',ROOT/'results/v5/scores.csv')
    print(f'PASS: F5 {cases} cases recomputed; frozen files were not modified.')
if __name__=='__main__':main()
