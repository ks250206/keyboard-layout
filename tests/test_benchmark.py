"""Run: python -m unittest discover -s tests -v"""
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmark import make_map, metrics, read_layouts, summary_rows, document_counts

class BenchmarkTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.layouts=read_layouts()
  cls.archive=json.loads((ROOT/'data/aggregates.json').read_text(encoding='utf-8'))

 def test_unique_complete_core_layouts(self):
  self.assertEqual(len(self.layouts),9)
  for name,rows in self.layouts.items():
   with self.subTest(layout=name):
    core=''.join(rows)
    self.assertEqual(len(core),30)
    self.assertEqual(len(set(core)),30)
    self.assertTrue(set('abcdefghijklmnopqrstuvwxyz') <= set(core))
    self.assertEqual(len(make_map(name,self.layouts))>=30,True)

 def test_summary_regeneration(self):
  import csv
  with (ROOT/'data/local_summary.csv').open(encoding='utf-8-sig',newline='') as f:
   published={(r['task'],r['layout']):r for r in csv.DictReader(f)}
  for row in summary_rows(self.archive):
   pub=published[(row['category'],row['layout'])]
   for k in ('estimated_seconds','home_pct','distance_m','same_finger_pct','KLA_approx','gain_vs_qwerty_pct'):
    with self.subTest(category=row['category'],layout=row['layout'],metric=k):
     self.assertAlmostEqual(row[k],float(pub[k]),delta=.015)

 def test_simple_text_input(self):
  alphabet=self.archive['alphabet'];counts=document_counts('hello, Python!',alphabet)
  self.assertEqual(counts['n'],14)
  for name in self.layouts:
   result=metrics(name,self.layouts,counts,alphabet)
   self.assertGreater(result['estimated_seconds'],0)

 def test_diagrams_labels(self):
  for name,rows in self.layouts.items():
   slug='onishi' if name=='大西' else name.lower()
   svg=(ROOT/'diagrams'/f'{slug}.svg').read_text()
   import xml.etree.ElementTree as ET
   root=ET.fromstring(svg)
   self.assertEqual(root.tag,'{http://www.w3.org/2000/svg}svg')
   # Compare exact 30 keycap labels, including XML-escaped punctuation.
   from collections import Counter
   ns = {"s":"http://www.w3.org/2000/svg"}
   keycaps = [node.text for node in root.findall(".//s:text",ns) if node.attrib.get("font-size")=="31"]
   self.assertEqual(Counter(keycaps), Counter(c.upper() for c in "".join(rows)))

if __name__=='__main__':unittest.main()
