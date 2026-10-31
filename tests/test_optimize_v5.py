"""Structural and numerical regression tests for semantic symbol constraints."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
try:
    import numpy as np
    import optimize_v4 as v
    import optimize_v5 as f
except ImportError:np=None;v=None;f=None
@unittest.skipIf(f is None,'Install requirements-v4.txt for numerical F5 tests')
class PairOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=v.read_data();cls.f4=json.loads((ROOT/'data/v4/candidates.json').read_text())['winners'];d=cls.f4['F4-Balance-left']
        cls.origin=(np.array(d['base'],np.int32),np.array(d['shift'],np.int32));cls.obj=v.objective_arrays(cls.data,'Balance')
    def test_seed_constraints_all_modes(self):
        for mode in (1,2,3):
            b,s=f.make_seed(*self.origin,mode);self.assertTrue(f.valid_mapping(v.validate(b,s,True),mode));self.assertEqual(sum(x['constraint_pass'] for x in f.pair_details(b,s)),9)
    def test_original_free_layout_is_not_pair_layout(self):self.assertFalse(f.valid_mapping(v.validate(*self.origin,True),1))
    def test_digits_and_uppercase_unchanged(self):
        for mode in (1,2,3):
            b,s=f.make_seed(*self.origin,mode);p=v.validate(b,s,True)
            for i,ch in enumerate('1234567890'):self.assertEqual(p[v.CI[ch]],2*i)
            for ch in 'abcdefghijklmnopqrstuvwxyz':self.assertEqual(p[v.CI[ch.upper()]],p[v.CI[ch]]+1)
    def test_shift_orientation_is_canonical(self):
        b,s=f.make_seed(*self.origin,2);p=v.mapped(b,s)
        for pair in f.PAIR_STRINGS:self.assertEqual(p[v.CI[pair[0]]]%2,0);self.assertEqual(p[v.CI[pair[1]]],p[v.CI[pair[0]]]+1)
    def test_reversed_semicolon_pair_rejected(self):
        b,s=f.make_seed(*self.origin,2);p=v.mapped(b,s);p[v.CI[';']],p[v.CI[':']]=p[v.CI[':']],p[v.CI[';']];self.assertFalse(f.valid_mapping(p,2))
    def test_horizontal_cannot_wrap_to_next_row(self):
        b,s=f.make_seed(*self.origin,1);p=v.mapped(b,s);p[v.CI['[']]=2*24+1;p[v.CI[']']]=2*25+1;self.assertFalse(f.valid_mapping(p,1))
    def test_grid_bracket_families(self):
        b,s=f.make_seed(*self.origin,3);p=v.mapped(b,s)
        for base,shift in [('()','<>'),('[]','{}')]:
            a,bx=[int(p[v.CI[c]]) for c in base];self.assertEqual(a%2,0);self.assertEqual(bx,a+2);self.assertEqual(p[v.CI[shift[0]]],a+1);self.assertEqual(p[v.CI[shift[1]]],bx+1)
    def test_random_moves_preserve_permutation_and_delta(self):
        rng=np.random.default_rng(998831);A,C,u,g=self.obj;accepted=0
        for mode in (1,2,3):
            b,s=f.make_seed(*self.origin,mode);board=np.empty(96,np.int32);board[::2]=b;board[1::2]=s;p=v.mapped(b,s)
            initial=sorted(board.tolist());gi,gl,gp,gn=f.structure(mode);score,fl=v.evaluate_fast(p,A,C,u,g)
            for _ in range(1000):
                kind=int(rng.integers(4));x=int(rng.integers(len(gi) if kind==3 else 48));y=int(rng.integers(gn[x] if kind==3 else 48));rev=int(rng.integers(2))
                nb,pp,m,ids,news=f.proposal(board,p,kind,x,y,rev,mode,gi,gl,gp)
                if not m:continue
                dv,fn=v.delta(p,ids,news,m,A,C,u,g,fl);fresh,ff=v.evaluate_fast(pp,A,C,u,g);self.assertAlmostEqual(fresh,score+dv,places=8)
                np.testing.assert_allclose(fn,ff,atol=1e-12);self.assertEqual(initial,sorted(nb.tolist()));np.testing.assert_array_equal(pp,v.validate(nb[::2],nb[1::2],True));self.assertTrue(f.valid_mapping(pp,mode))
                board=nb;p=pp;score=fresh;fl=ff;accepted+=1
        self.assertGreater(accepted,100)
    def test_seeded_search_is_reproducible(self):
        A,C,u,g=self.obj;b,s=f.make_seed(*self.origin,1);args=f.structure(1)
        x=f.search_one(b,s,A,C,u,g,32,100,1,*args,True);y=f.search_one(b,s,A,C,u,g,32,100,1,*args,True)
        np.testing.assert_array_equal(x[0],y[0]);np.testing.assert_array_equal(x[1],y[1]);self.assertEqual(x[2],y[2])
    def test_saved_winners_meet_constraints_and_objectives(self):
        paths=list((ROOT/'results/v5/search').glob('*_winner.json'));self.assertEqual(len(paths),6)
        for path in paths:
            d=json.loads(path.read_text());b=np.array(d['base'],np.int32);s=np.array(d['shift'],np.int32);p=v.validate(b,s,True);self.assertTrue(f.valid_mapping(p,f.MODES[d['mode']]))
            obj,_=v.evaluate_fast(p,*v.objective_arrays(self.data,d['profile']));self.assertAlmostEqual(obj,d['objective_ms'],places=8);self.assertEqual(d['restarts'],64);self.assertEqual(d['iterations'],100000)
    def test_group_targets_have_no_repeated_or_fixed_faces(self):
        for mode in (1,2,3):
            gi,gl,gp,gn=f.structure(mode)
            for i,nn in enumerate(gn):
                for target in gp[i,:nn,:gl[i]]:
                    self.assertEqual(len(set(target)),len(target));self.assertNotIn(24,target);self.assertFalse(any(k%2==0 and k//2<10 for k in target))
if __name__=='__main__':unittest.main()
