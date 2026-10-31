#!/usr/bin/env python3
"""Compare reconstructed layouts and scores with the original local publication."""
from pathlib import Path
import csv, hashlib, json
ROOT=Path(__file__).resolve().parents[1]
def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,separators=(',',':'),sort_keys=True).encode()).hexdigest()
expected=json.loads((ROOT/'publication/expected.json').read_text())
for version in (4,5):
    rows=list(csv.DictReader((ROOT/f'results/v{version}/scores.csv').open(encoding='utf-8')))
    normalized=[]
    for row in sorted(rows,key=lambda r:(r['layout'],r['group'])):
        normalized.append({k:(value if k in ('layout','group') else f'{float(value):.5f}') for k,value in row.items()})
    winners=json.loads((ROOT/f'data/v{version}/candidates.json').read_text())['winners']
    maps={k:{field:d[field] for field in ('base','shift')} for k,d in winners.items()}
    actual={'cases':len(rows),'scores_sha256':digest(normalized),'maps_sha256':digest(maps)}
    print('F'+str(version),actual,flush=True)
    if actual!=expected[str(version)]:raise AssertionError(f'F{version} differs from original frozen publication')
print('PASS: all 1504 cases and all winning key maps match the original publication snapshot.')
