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
    """history: (sha, README text, committer date, touches README). One minute between commits."""
    def __init__(self):
        self.head='a'*40;self.readme=README;self.files=list(BASE);self.fetches=0;self.gets=[]
        self.history=[(self.head,README,self.date(0),True)]
    @staticmethod
    def date(n):return f'2026-11-23T{n//60:02d}:{n%60:02d}:00Z'
    def get(self,path,params=None):
        self.gets.append((path,params))
        if path.endswith('/commits'):
            # Newest first, like GitHub; the filters are inclusive.
            rows=[h for h in reversed(self.history) if (h[3] or params.get('path')!='README.md') and params['since']<=h[2]<=params['until']]
            start=(params['page']-1)*params['per_page'];return [{'sha':h[0]} for h in rows[start:start+params['per_page']]]
        sha=self.head if path.endswith('/HEAD') else path.rsplit('/',1)[1]
        row=next(h for h in self.history if h[0]==sha)
        return {'sha':sha,'commit':{'committer':{'date':row[2]}}}
    def readme_at(self,sha):return next(h[1] for h in self.history if h[0]==sha)
    def fetch(self,sha):self.fetches+=1;return self.readme,self.files
    def commit(self,n,readme=None,files=None):
        self.head=str(n)*40 if n<10 else f'{n:040x}'
        if readme is not None:self.readme=readme
        if files is not None:self.files=list(BASE)+files
        self.history.append((self.head,self.readme,self.date(len(self.history)),readme is not None))

class LeanTargetTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'.git').mkdir()
        self.repo=Repo();self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def run_once(self,dry=False):return w.run(self.repo.get,self.repo.fetch,lambda t,k:self.sent.append(t),self.root,dry,lambda sha:self.repo.readme_at(sha))

    def test_a_kappa_between_two_cycles_is_reported_with_its_commit(self):
        # 2026-10-17: 36261/2^48 -> 3213/2^44 (a80551f) -> 14229/2^46 within one 3-hour gap.
        self.run_once()
        self.repo.commit(2,README.replace('2^-37','3213/2^44'));self.repo.commit(3);self.repo.commit(4,README.replace('2^-37','14229/2^46'))
        self.run_once()
        self.assertEqual(len(self.sent),1)
        self.assertIn('from 2^-37 to 3213/2^44 at '+'2'*10,self.sent[0])
        self.assertIn('from 3213/2^44 to 14229/2^46',self.sent[0])
        self.repo.commit(5);self.run_once();self.assertEqual(len(self.sent),1)

    def test_walk_survives_bad_reads_and_names_skipped_commits(self):
        self.run_once()
        self.repo.commit(2,README.replace('2^-37','2^-36'));self.repo.commit(3,README.replace('2^-37','2^-35'))
        real=self.repo.readme_at
        def flaky(sha):
            if sha=='2'*40:raise RuntimeError('GitHub GET failed (HTTP 404)')
            return real(sha)
        self.repo.readme_at=flaky;self.repo.commit(4,README.replace('2^-37','2^-34'))
        self.run_once()
        self.assertIn('from 2^-37 to 2^-35 at '+'3'*10,self.sent[-1]);self.assertIn('from 2^-35 to 2^-34',self.sent[-1])
        old=w.MAX_WALK;w.MAX_WALK=1
        try:
            self.repo.readme_at=real;self.repo.commit(5,README.replace('2^-37','2^-32'));self.repo.commit(6,README.replace('2^-37','2^-31'));self.repo.commit(7,README.replace('2^-37','2^-33'))
            self.run_once()
            self.assertIn('1 earlier README commits since the last cycle were not read',self.sent[-1])
        finally:w.MAX_WALK=old

    def readme_gets(self):return [g for g in self.repo.gets if g[0].endswith('/commits') and g[1]]

    def test_commits_that_leave_the_readme_alone_are_never_read(self):
        # 2026-11-23: 149 commits in one gap on a repo that commits every 4 minutes; no README change.
        self.run_once()
        for n in range(10,160):self.repo.commit(n)
        self.repo.commit(7,README.replace('2^-37','2^-36'))
        self.repo.commit(8)
        reads=[]
        real=self.repo.readme_at;self.repo.readme_at=lambda sha:reads.append(sha) or real(sha)
        self.repo.gets.clear();self.run_once()
        self.assertEqual(len(reads),1);self.assertEqual(reads[0],self.repo.history[-2][0])
        self.assertEqual(len(self.sent),1);self.assertNotIn('not read',self.sent[0])
        self.assertIn('from 2^-37 to 2^-36',self.sent[0])
        self.assertEqual(len(self.repo.gets),2)  # HEAD + one listing page; no per-commit GET

    def test_skip_alert_needs_more_readme_commits_than_the_cap(self):
        self.run_once()
        old=w.MAX_WALK;w.MAX_WALK=2
        try:
            for n in range(2,5):self.repo.commit(n,README.replace('2^-37',f'2^-{n}'))   # 3 README commits + head
            for n in range(10,35):self.repo.commit(n)                                    # 25 commits that leave it alone
            self.repo.commit(9)
            self.run_once()
            self.assertIn('1 earlier README commits since the last cycle were not read',self.sent[-1])
            self.assertIn('from 2^-3 to 2^-4 at '+'4'*10,self.sent[-1])
            self.assertNotIn('at '+'2'*10,self.sent[-1])  # the oldest README commit is the one not read
        finally:w.MAX_WALK=old

    def test_listing_pages_and_stops_at_the_last_short_page(self):
        self.run_once()
        for n in range(2,6):self.repo.commit(n,README.replace('2^-37',f'2^-{n}'))
        self.repo.commit(7)
        old=w.PER_PAGE;w.PER_PAGE=2
        try:
            self.repo.gets.clear();self.run_once()
        finally:w.PER_PAGE=old
        pages=[g[1]['page'] for g in self.readme_gets()]
        self.assertEqual(pages,[1,2,3])  # the old head and 4 README commits: two full pages, then a short one
        self.assertIn('from 2^-37 to 2^-2 at '+'2'*10,self.sent[-1])
        self.assertIn('from 2^-4 to 2^-5',self.sent[-1])

    def test_the_cycle_state_keeps_the_head_date_and_the_next_cycle_uses_it(self):
        self.run_once()
        state=json.loads((self.root/w.STATE).read_text());self.assertEqual(state['head_date'],Repo.date(0))
        self.repo.commit(2);self.repo.gets.clear();self.run_once()
        self.assertEqual([g[0].rsplit('/',1)[1] for g in self.repo.gets if '/commits/' in g[0]],['HEAD'])  # no extra GET for the old head
        self.assertEqual(self.readme_gets()[0][1]['since'],Repo.date(0))
        self.assertEqual(self.readme_gets()[0][1]['until'],Repo.date(1))

    def test_a_state_without_head_date_reads_the_old_head_date_once(self):
        self.run_once();path=self.root/w.STATE
        state=json.loads(path.read_text());state.pop('head_date');path.write_text(json.dumps(state))
        self.repo.commit(2,README.replace('2^-37','2^-36'));self.repo.commit(3)
        self.repo.gets.clear();self.run_once()
        self.assertIn('from 2^-37 to 2^-36 at '+'2'*10,self.sent[-1])
        self.assertIn('/commits/'+'a'*40,[g[0] for g in self.repo.gets][1])

    def test_a_failed_listing_or_old_head_gives_no_walk_and_the_cycle_still_runs(self):
        self.run_once();self.repo.commit(2,README.replace('2^-37','2^-36'));self.repo.commit(3)
        real=self.repo.get
        def broken(path,params=None):
            if path.endswith('/commits'):raise RuntimeError('GitHub GET failed')
            return real(path,params)
        self.assertEqual(w.run(broken,self.repo.fetch,lambda t,k:self.sent.append(t),self.root,False,self.repo.readme_at)['changed'],True)
        # The tarball README still reports the value, as a change from the stored kappa, not as a walk value.
        self.assertIn('2^-37',' '.join(self.sent))

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
