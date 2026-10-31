import csv, json, sys, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import benchmark_finger_rows as m
import generate_corpus as gen

class ModelTests(unittest.TestCase):
    def test_finger_row_user_hypotheses(self):
        for idx,finger,row,ms in [(0,'L-pinky',0,18),(21,'L-ring',2,18),(22,'L-middle',2,12),
                                   (27,'R-middle',2,9),(28,'R-ring',2,9),(9,'R-pinky',0,7)]:
            self.assertEqual(m.FINGER_NAMES[m.FINGERS[idx]],finger)
            self.assertEqual(m.row(idx),row)
            self.assertEqual(m.key_penalty(idx,1,0),ms)
    def test_inner_and_neutral(self):
        self.assertEqual(m.zone(14),'inward') # QWERTY G
        self.assertEqual(m.zone(15),'inward') # QWERTY H
        self.assertEqual(m.zone(13),'neutral')
        self.assertEqual(m.key_penalty(14,0,1),7)
        self.assertEqual(m.key_penalty(15,0,1),7)
    def test_zero_cost_recovers_legacy(self):
        layouts=m.legacy.read_layouts()
        rom=json.loads((ROOT/'data/synthetic_three_domains.json').read_text())['documents'][0]['romaji']
        c=m.aggregate([dict(id='one',romaji=rom)],'\t\n'+''.join(chr(i)for i in range(32,127)))
        for name in layouts:
            result=m.evaluate(name,layouts,c,'\t\n'+''.join(chr(i)for i in range(32,127)),0,0)
            self.assertAlmostEqual(result['legacy_s'],result['v2_s'])
    def test_no_cross_document_bigrams(self):
        a='ab';b='bc';alpha='\t\n'+''.join(chr(i) for i in range(32,127))
        c=m.aggregate([dict(id='1',romaji=a),dict(id='2',romaji=b)],alpha)
        ab=next(v for i,j,v in c['bigrams'] if alpha[i]=='a' and alpha[j]=='b')
        bc=next(v for i,j,v in c['bigrams'] if alpha[i]=='b' and alpha[j]=='c')
        self.assertEqual((ab,bc),(1,1))
        self.assertEqual(sum(v for *_,v in c['bigrams']),2)
    def test_corpus_checks_and_reproducibility(self):
        d=gen.build(); saved=json.loads((ROOT/'data/synthetic_three_domains.json').read_text(encoding='utf-8'))
        self.assertEqual(d,saved)
        self.assertEqual(len(saved['documents']),48)
        self.assertEqual(sum(x['keystrokes'] for x in saved['documents']),23483)
        self.assertEqual(sum(x['long_marks'] for x in saved['documents']),343)
        for doc in saved['documents']:
            self.assertEqual(doc['romaji'],gen.romanize(doc['reading_hiragana']))
    def test_generated_results(self):
        path=ROOT/'results/finger_rows_v2/summary.csv'
        with path.open(encoding='utf-8') as f: rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),3*3*9)
        for category in ['生活文','業務文','技術文']:
            e=[r for r in rows if r['domain']==category and r['split']=='all']
            self.assertEqual(len(e),9)
            self.assertEqual(max(e,key=lambda r:float(r['v2_gain_pct']))['layout'],'Nova-JP')

if __name__=='__main__': unittest.main()
