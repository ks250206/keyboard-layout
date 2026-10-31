#!/usr/bin/env python3
"""Check README and merged KLA table against both frozen score datasets."""
from build_kla_tables import ROOT, MARKER_START, MARKER_END, render
expected,csv_data=render()
text=(ROOT/'README.md').read_text(encoding='utf-8')
if text.count(MARKER_START)!=1 or text.count(MARKER_END)!=1:raise AssertionError('Missing or duplicate KLA table markers')
actual=text[text.index(MARKER_START):text.index(MARKER_END)+len(MARKER_END)]
if actual!=expected:raise AssertionError('README KLA tables differ from frozen scores; run tools/build_navigation.py')
if (ROOT/'results/kla_all.csv').read_text(encoding='utf-8')!=csv_data:raise AssertionError('Merged KLA table differs from frozen scores')
print('PASS: README and CSV match all 30 layouts x 14 evaluation groups (420 KLA scores).')
