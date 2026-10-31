"""Frozen-result integrity always runs; optimizer tests need numpy/numba."""
import gzip,itertools,json,math,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
try:
    import numpy as np
    import optimize_v4 as v
except ImportError:v=None
class FrozenV4Tests(unittest.TestCase):
    def test_frozen_raw_statistics(self):
        b=json.loads(gzip.decompress((ROOT/'data/v4/raw_ngrams.json.gz').read_bytes()))
        for name,d in b['groups'].items():
            self.assertEqual(d['n'],sum(n for _,n in d['u']),name)
            self.assertEqual(sum(n for _,_,n in d['g']),d['n']-sum(n for _,n in d['first']),name)
        self.assertEqual(b['groups']['JP/train']['n'],5104);self.assertEqual(b['groups']['CODE/test']['n'],76876)
        self.assertGreater(dict(b['groups']['CODE/train']['u']).get('(',0),0)
        self.assertGreater(sum(n for c,n in b['groups']['CODE/train']['u'] if c.isupper()),0)
    def test_every_frozen_layout_is_complete(self):
        alpha='\t\n'+''.join(map(chr,range(32,127)))
        d=json.loads((ROOT/'data/v4/candidates.json').read_text())
        for name,entry in d['winners'].items():
            b,s=entry['base'],entry['shift']
            self.assertEqual(len(b),48);self.assertEqual(len(s),48)
            self.assertEqual(''.join(alpha[x] for x in b[:10]),'1234567890',name)
            both=[x for x in b+s if x>=0]
            self.assertEqual(len(both),94,name);self.assertEqual(len(set(both)),94,name)
            self.assertEqual(set(both),set(range(3,97)),name)
            for k,x in enumerate(b):
                if x>=0 and alpha[x].islower():self.assertEqual(alpha[s[k]],alpha[x].upper(),name)
            self.assertIn(alpha.index('-'),b,name)
@unittest.skipIf(v is None,'Install requirements-v4.txt for numerical tests')
class NumericalV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle=v.read_data();cls.A,cls.C,cls.u,cls.g=v.objective_arrays(cls.bundle,'Balance')
    def test_all_reference_layouts(self):
        for b,s in v.references().values():v.validate(b,s)
    def test_incremental_matches_direct_for_every_move_type(self):
        b,s=v.references()['Nova-F3-Balance'];p=v.mapped(b,s)
        val,fl=v.evaluate_fast(p,self.A,self.C,self.u,self.g);rng=np.random.default_rng(82);seen=set()
        for _ in range(900):
            kind=int(rng.integers(3));x,y=map(int,rng.integers(48,size=2))
            ids,news,m=v.propose(b,s,p,kind,x,y,0,True)
            if not m:continue
            seen.add(kind);dv,fn=v.delta(p,ids,news,m,self.A,self.C,self.u,self.g,fl)
            b2,s2,p2=b.copy(),s.copy(),p.copy();v.apply_move(b2,s2,p2,kind,x,y,ids,news,m);v.validate(b2,s2,True)
            direct,load=v.evaluate_fast(p2,self.A,self.C,self.u,self.g)
            self.assertAlmostEqual(direct,val+dv,places=8);self.assertTrue(np.allclose(load,fn))
        self.assertEqual(seen,{0,1,2})
    def test_shift_only_and_symbols_only_freeze_the_required_faces(self):
        b,s=v.references()['Nova-F3-Balance'];p=v.mapped(b,s)
        for stage in (1,3):
            bb,ss,*_=v.anneal(b,s,p,self.A,self.C,self.u,self.g,901+stage,1000,0,True,True,stage)
            if stage==1:self.assertTrue(np.array_equal(bb,b))
            pp=v.mapped(bb,ss)
            for i in v.ALPHA_IDS:self.assertEqual(pp[i],p[i])
    def test_small_exhaustive_search_agrees_with_bruteforce(self):
        b,s=v.jis();p=v.mapped(b,s)
        ss,value,visited=v.enumerate_number_row(b,s,p,self.A,self.C,self.u,self.g,4);brute=[]
        for perm in itertools.permutations(s[:4]):
            z=s.copy();z[:4]=perm;q,_=v.evaluate_fast(v.mapped(b,z),self.A,self.C,self.u,self.g);brute.append(q)
        self.assertEqual(visited,24);self.assertAlmostEqual(value,min(brute),places=8);self.assertTrue(np.array_equal(ss[4:],s[4:]))
    def test_shift_is_held_on_same_side(self):
        b,s=v.jis();a=v.metrics(b,s,v.counts(['AA']));b2=v.metrics(b,s,v.counts(['AJ']))
        self.assertAlmostEqual(a['shift_entries_per_100'],50);self.assertAlmostEqual(b2['shift_entries_per_100'],100)
    def test_main_only_KLA_is_not_modified_by_shift_time_coefficients(self):
        b,s=v.jis();c=self.bundle['groups']['CODE/test'];m1=v.metrics(b,s,c,shift_scale=.5);m2=v.metrics(b,s,c,shift_scale=2)
        self.assertEqual(m1['KLA_main_approx'],m2['KLA_main_approx']);self.assertLess(m1['seconds'],m2['seconds'])
    def test_empty_text_is_rejected(self):
        with self.assertRaises(ValueError):v.metrics(*v.jis(),v.counts(['']))
    def test_candidate_side_constraints(self):
        d=json.loads((ROOT/'data/v4/candidates.json').read_text())
        for entry in d['winners'].values():v.validate(np.array(entry['base'],np.int32),np.array(entry['shift'],np.int32),entry['vowels_left'],entry['hyphen_constraint'])
    def test_simple_home_key_time(self):
        b,s=v.jis();self.assertAlmostEqual(v.metrics(b,s,v.counts(['a']))['ms_per_char'],118);self.assertAlmostEqual(v.metrics(b,s,v.counts(['as']))['ms_per_char'],122)
if __name__=='__main__':unittest.main()
