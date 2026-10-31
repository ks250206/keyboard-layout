"""Regression tests for NOVA F3 layout optimization, deterministic model reuse."""
from __future__ import annotations
import json,math,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import optimize_v3 as model

class TestFingerRowOptimization(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=model.stored_data()
        cls.counts=model.collect(cls.data)
        cls.candidates=json.loads((ROOT/'data/v3_candidates.json').read_text())['optimized']
        cls.layout=model.read_rows()

    def test_four_candidates_are_real_permutations(self):
        self.assertEqual(len(self.candidates),4)
        for name,item in self.candidates.items():
            rows=item['rows'];s=''.join(rows)
            self.assertEqual(len(rows),3);self.assertEqual([len(x) for x in rows],[10]*3)
            self.assertEqual(set(s),set(model.SYMBOLS));self.assertEqual(len(set(s)),30)
            self.assertAlmostEqual(sum(item['weights'].values()),1.,places=10)
            self.assertLess(item['objective_ms_key'],160)
        self.assertEqual(''.join(self.candidates['Nova-F3-Ctrl']['rows'])[20:24],'zxcv')

    def test_base_model_not_rewritten(self):
        for layout,expected in [('QWERTY',38.40),('大西',76.12),('Nova-JP',76.59)]:
            actual=model.evaluate_one(self.layout[layout],self.counts['JP_original6'])['KLA_approx_unchanged']
            self.assertLess(abs(actual-expected),.015)

    def test_saved_corpus_sizes_and_disjoint_english(self):
        self.assertEqual(self.counts['JP_original6']['n'],2749)
        self.assertEqual(self.counts['JP_loanword6']['n'],2733)
        self.assertEqual(self.counts['EN/test']['n'],1208)
        self.assertEqual(self.counts['CODE/test']['n'],76876)
        self.assertEqual(self.counts['生活文/all']['n'],7605)
        self.assertEqual(self.counts['業務文/all']['n'],7920)
        self.assertEqual(self.counts['技術文/all']['n'],7958)
        self.assertEqual(self.counts['EN/train']['n']+self.counts['EN/test']['n'],self.counts['EN/all']['n'])
        for domain in ['生活文','業務文','技術文']:
            self.assertEqual(self.counts[f'{domain}/all']['n'],
                             self.counts[f'{domain}/development']['n']+self.counts[f'{domain}/holdout']['n'])
        sources=self.data['source']['code_files']
        for lang in model.CODE_FILES:
            group=[v for v in sources if v['language']==lang]
            self.assertEqual(len(group),2)
            self.assertEqual({v['split'] for v in group},{'train','test'})
            self.assertNotEqual(group[0]['sample_sha256'],group[1]['sample_sha256'])

    def test_numba_score_matches_published_v2_function(self):
        counts=self.counts
        canon=model.canon_items(counts);idx={c:i for i,c in enumerate(canon)}
        fallback=np.array([model.v2.EXTRA.get(c,0) for c in canon],dtype=np.int32)
        core=np.array([idx[c] for c in model.SYMBOLS],dtype=np.int32)
        per,trans,hd,fi,_=model.coord_arrays()
        for corpus in ('JP_original6','JP_loanword6','EN/test','CODE/test'):
            gr=model.serializable_groups([model.ngram_arrays(counts[corpus],canon)])
            for name in ('Nova-F3-JP','Nova-F3-Balance','Nova-F3-Code','Nova-F3-Ctrl'):
                rows=self.candidates[name]['rows']
                x=model.fast_score(model.from_existing(rows),core,fallback,per,trans,hd,fi,gr,np.array([1.]),0.)
                y=model.evaluate_one(rows,counts[corpus])['v2_s']/counts[corpus]['n']
                self.assertAlmostEqual(x,y,places=10,msg=f'{corpus} {name}')

    def test_heldout_scores_and_qualifications(self):
        q=model.evaluate_one(self.layout['QWERTY'],self.counts['JP_loanword6'])
        new=model.evaluate_one(self.candidates['Nova-F3-JP']['rows'],self.counts['JP_loanword6'])
        old=model.evaluate_one(self.layout['Nova-JP'],self.counts['JP_loanword6'])
        self.assertLess(new['v2_s'],old['v2_s'])
        self.assertAlmostEqual(100*(q['v2_s']/new['v2_s']-1),17.5052,places=3)
        self.assertLess(new['KLA_approx_unchanged'],
                        model.evaluate_one(self.layout['大西'],self.counts['JP_loanword6'])['KLA_approx_unchanged'])
        qcode=model.evaluate_one(self.layout['QWERTY'],self.counts['CODE/test'])
        ncode=model.evaluate_one(self.candidates['Nova-F3-Code']['rows'],self.counts['CODE/test'])
        self.assertAlmostEqual(100*(qcode['v2_s']/ncode['v2_s']-1),8.8574,places=3)

    def test_sensitivity_is_on_heldout_corpus(self):
        q0=model.evaluate_one(self.layout['QWERTY'],self.counts['JP_original6'],0,0)
        q1=model.evaluate_one(self.layout['QWERTY'],self.counts['JP_original6'],1,1)
        x0=model.evaluate_one(self.candidates['Nova-F3-JP']['rows'],self.counts['JP_original6'],0,0)
        x1=model.evaluate_one(self.candidates['Nova-F3-JP']['rows'],self.counts['JP_original6'],1,1)
        self.assertAlmostEqual(100*(q0['v2_s']/x0['v2_s']-1),17.094,delta=.02)
        self.assertGreater(100*(q1['v2_s']/x1['v2_s']-1),100*(q0['v2_s']/x0['v2_s']-1))

if __name__=='__main__':unittest.main()
