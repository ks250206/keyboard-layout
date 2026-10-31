#!/usr/bin/env python3
"""Optional independent validation against eight pinned public GitHub file blobs.

Requires network access to api.github.com; GitHub's anonymous REST rate limit applies.
No OSS source text is stored by this project. Output is reproducible if blobs remain available.
"""
from __future__ import annotations
import argparse
import base64
import csv
import json
import urllib.request
from pathlib import Path
from benchmark import document_counts, metrics, read_layouts, ROOT


def load_source(repo, blob_sha):
    url=f'https://api.github.com/repos/{repo}/git/blobs/{blob_sha}'
    request=urllib.request.Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'keyboard-layout-benchmark/1.0'})
    with urllib.request.urlopen(request,timeout=30) as res: blob=json.load(res)
    if blob.get('encoding')!='base64':raise ValueError('Expected base64 text blob')
    return base64.b64decode(blob['content']).decode('utf-8',errors='replace')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--only',help='Filter by language label, e.g. Rust')
    args=ap.parse_args()
    manifest=json.loads((ROOT/'data/external_oss_sources.json').read_text(encoding='utf-8'))
    archive=json.loads((ROOT/'data/aggregates.json').read_text(encoding='utf-8'))
    with (ROOT/'data/external_oss.csv').open(encoding='utf-8-sig',newline='') as f:
        published={(r['language'],r['layout']):r for r in csv.DictReader(f)}
    layouts=read_layouts();n=0
    for item in manifest:
        lang=item['language']
        if args.only and lang.lower()!=args.only.lower():continue
        text=load_source(item['repo'],item['blob_sha'])
        part=''.join(text.splitlines(keepends=True)[item['start']-1:item['end']])
        counts=document_counts(part,archive['alphabet'])
        q=metrics('QWERTY',layouts,counts,archive['alphabet'])
        print(f"{lang:12} {item['repo']}/{item['path']}  keys={counts['n']}")
        if counts['n']!=item['keystrokes']:
            raise AssertionError(f"Unexpected length {counts['n']} != {item['keystrokes']}; verify line selection")
        for name in layouts:
            r=metrics(name,layouts,counts,archive['alphabet'])
            gain=100*(q['estimated_seconds']/r['estimated_seconds']-1)
            original=published[(lang,name)]
            if abs(gain-float(original['predicted_gain_vs_qwerty_pct']))>0.04:
                raise AssertionError(f'{lang}, {name}: predicted gain {gain:.2f}, published {original["predicted_gain_vs_qwerty_pct"]}')
        n+=1
    print(f'PASS: {n} external files compared to benchmark snapshot')

if __name__=='__main__':main()
