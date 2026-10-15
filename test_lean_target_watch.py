import json, tempfile, unittest
from pathlib import Path
import lean_target_watch as w

README='''# Integer multiplication in Lean

## Main result

The construction proves the positive saving
`kappa = 2^-37`, exposed by `MathlibTM2.mulInTime`.

## Mathlib statement

`MathlibTM2.statement_of_endToEnd` proves `EndToEnd → MathlibTM2.Statement`.

## Status

The end-to-end Mathlib proof is complete. The stronger `83/10^12` exponent saving remains open.

## Building
'''
BASE=[('IntegerMultBounds/MathlibTM2/Bridge.lean','theorem statement_of_endToEnd (h : Machine.EndToEnd) : MathlibTM2.Statement := by\n  exact foo h\n'),
      ('IntegerMultBounds/Machine.lean','def EndToEnd : Prop :=\n  True\n')]

class Repo:
    def __init__(self):self.head='a'*40;self.readme=README;self.files=list(BASE);self.fetches=0
    def get(self,path,params=None):return {'sha':self.head}
    def fetch(self,sha):self.fetches+=1;return self.readme,self.files
    def commit(self,n,readme=None,files=None):
        self.head=str(n)*40
        if readme is not None:self.readme=readme
        if files is not None:self.files=list(BASE)+files

class LeanTargetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'.git').mkdir()
        self.repo=Repo();self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def run_once(self,dry=False):return w.run(self.repo.get,self.repo.fetch,lambda t,k:self.sent.append(t),self.root,dry)

    def test_baseline_is_silent_and_unchanged_head_is_not_fetched(self):
        self.assertEqual(self.run_once()['alerts'],0)
        self.assertEqual(self.run_once(),{'status':'ok','changed':False,'alerts':0});self.assertEqual(self.repo.fetches,1)
        self.assertEqual(self.sent,[])

    def test_kappa_change_alerts_once_with_commit(self):
        self.run_once()
        self.repo.commit(2,README.replace('2^-37','2^-36'));self.run_once()
        self.repo.commit(3);self.run_once()
        self.assertEqual(len(self.sent),1)
        self.assertIn('README kappa changed from 2^-37 to 2^-36',self.sent[0])
        self.assertIn('https://github.com/platypii/integer-mult-bounds-lean/commit/'+'2'*40,self.sent[0])

    def test_target_proved_signals(self):
        self.run_once()
        proved=README.replace('The stronger `83/10^12` exponent saving remains open.','The native multitape EndToEnd target with saving `83/10^12` is proved.')
        self.repo.commit(2,proved,[('IntegerMultBounds/Machine/Final.lean','-- uses no sorry\ntheorem endToEnd : IntegerMultBounds.Machine.EndToEnd := by\n  exact final\n')])
        self.run_once()
        text=self.sent[0]
        self.assertIn('no longer calls the 83/10^12 EndToEnd target open',text)
        self.assertIn('Status section changed and names the target',text)
        self.assertIn('Lean declaration of type EndToEnd in IntegerMultBounds/Machine/Final.lean (no sorry in the file)',text)

    def test_sorry_is_reported_and_comments_ignored(self):
        self.run_once()
        self.repo.commit(2,files=[('X.lean','/- theorem fake : Machine.EndToEnd := proof -/\ntheorem real (n : Nat) :\n    Machine.EndToEnd := by\n  sorry\n')])
        self.run_once()
        self.assertEqual(self.sent[0].count('type EndToEnd'),1);self.assertIn('(file contains sorry): theorem real (n : Nat) : Machine.EndToEnd :=',self.sent[0])

    def test_simulation_signals(self):
        self.run_once()
        self.repo.commit(2,files=[('IntegerMultBounds/FinTM2ToMultitape.lean','theorem endToEnd_of_statement (h : MathlibTM2.Statement) : Machine.EndToEnd := by\n  sorry\n')])
        self.run_once()
        self.assertIn('file named for the FinTM2-to-multitape simulation',self.sent[0])
        self.assertIn('possible FinTM2-to-multitape simulation in IntegerMultBounds/FinTM2ToMultitape.lean',self.sent[0])

    def test_dry_run_writes_and_sends_nothing(self):
        self.repo.readme=README.replace('2^-37','2^-36')
        self.assertEqual(self.run_once(True)['alerts'],1)
        self.assertEqual(self.sent,[]);self.assertFalse((self.root/w.STATE).exists())

    def test_failed_delivery_keeps_state_for_retry(self):
        self.repo.readme=README.replace('2^-37','2^-36')
        def down(*a):raise RuntimeError('office down')
        with self.assertRaises(RuntimeError):w.run(self.repo.get,self.repo.fetch,down,self.root)
        self.assertFalse((self.root/w.STATE).exists())
        self.run_once();self.assertEqual(len(self.sent),1)

    def test_empty_tarball_is_an_error(self):
        self.repo.files=[]
        with self.assertRaises(ValueError):self.run_once()

if __name__=='__main__':unittest.main()
