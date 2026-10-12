"""Offline checks for score safety and repeatable snapshot import."""
import contextlib, io, json, shutil, subprocess, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import refresh

class RefreshTests(unittest.TestCase):
    def test_claim_filter(self):
        self.assertIsNone(refresh.title_score('A κ ceiling of 2.5592e-3 (no new κ)'))
        self.assertIsNone(refresh.title_score('effective bit saving 6.7734e-4'))
        self.assertIsNone(refresh.title_score('κ = 8.032517e-5 complex-only / 8.800233e-5 joint'))
        self.assertEqual(refresh.title_score('conditional κ = 6.61885549259598e-4'),'330942774629799/500000000000000000')
        self.assertEqual(refresh.title_score('conditional kappa = 0.000472154791'),'472154791/1000000000000')
        self.assertEqual(refresh.title_score('Conditional κ = 7.44714499357628·10⁻⁴: new construction'),'186178624839407/250000000000000000')
        self.assertEqual(refresh.title_score('Conditional κ = 7.44714499357628 × 10^-4'),'186178624839407/250000000000000000')
        self.assertIsNone(refresh.title_score('Conditional κ = 8.339545889388e-4 (B1 open, not a witness)'))

    def test_snapshot_idempotence_and_selected_record(self):
        root=refresh.ROOT
        with tempfile.TemporaryDirectory(dir=refresh.git_state_dir()) as temp:
            stage=Path(temp)
            for pattern in ('*.json','sources/*','manifests/*'):
                for p in root.glob(pattern):
                    if p.is_file():
                        q=stage/p.relative_to(root);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(p.read_bytes())
            def api(path):
                repo='/'.join(path.split('/')[1:3]);suffix='__head.json' if '/commits/' in path else '__repo.json'
                result=refresh.load(stage,'sources/'+repo.replace('/','__')+suffix)
                if '/commits/' in path:
                    result.setdefault('files', []).append({'filename':'fixture.txt','patch':'unused diff text'})
                return result
            def content(repo,path,sha):
                if path=='README.md':return (stage/('sources/'+repo.replace('/','__')+'__README.md')).read_bytes()
                if path=='certificates/selected-result.json':return (stage/f'sources/crocswap-selected-{sha}.json').read_bytes()
                return (stage/f'sources/crocswap-certificate-{sha}.json').read_bytes()
            intake=refresh.load(stage,'sources/intake.json');intake.pop('fingerprint',None);refresh.dump(stage,'sources/intake.json',intake)
            pulls=refresh.load(stage,'sources/crocswap-pulls.json')
            with patch.object(refresh,'api',api),patch.object(refresh,'content',content),patch.object(refresh,'pages',lambda *a:pulls):
                first=refresh.refresh(stage,'2026-10-09T15:00:00Z')
                for head_path in (stage/'sources').glob('*__head.json'):
                    self.assertTrue(all('patch' not in f for f in json.loads(head_path.read_text()).get('files', [])))
                snapshot={p.relative_to(stage):p.read_bytes() for p in stage.rglob('*') if p.is_file()}
                second=refresh.refresh(stage,'2026-10-09T18:00:00Z')
                self.assertEqual(snapshot,{p.relative_to(stage):p.read_bytes() for p in stage.rglob('*') if p.is_file()})
                self.assertFalse(second['new_current_record'])
                problem=refresh.load(stage,'integer-multiplication.json')
                self.assertEqual(refresh.best(problem)['score'], first['current_record']['score'])
                for r in problem['records']:
                    if r['upstream_status'] in ('open','closed-unmerged'):
                        self.assertFalse(problem['record_metadata'][r['id']]['eligible_for_record'])
    def test_refresh_in_standalone_and_nested_repositories(self):
        source=refresh.ROOT
        tracked=subprocess.check_output(['git','ls-files'],cwd=source,text=True).splitlines()
        def api(path):
            repo='/'.join(path.split('/')[1:3]);suffix='__head.json' if '/commits/' in path else '__repo.json'
            return refresh.load(source,'sources/'+repo.replace('/','__')+suffix)
        def content(repo,path,sha):
            if path=='README.md':return (source/('sources/'+repo.replace('/','__')+'__README.md')).read_bytes()
            if path=='certificates/selected-result.json':return (source/f'sources/crocswap-selected-{sha}.json').read_bytes()
            return (source/f'sources/crocswap-certificate-{sha}.json').read_bytes()
        pulls=refresh.load(source,'sources/crocswap-pulls.json')
        for nested in (False,True):
            with self.subTest(nested=nested),tempfile.TemporaryDirectory(dir=refresh.git_state_dir()) as temp:
                repo=Path(temp);data=repo/'data' if nested else repo;data.mkdir(exist_ok=True)
                for rel in tracked:
                    target=data/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/rel,target)
                intake=refresh.load(data,'sources/intake.json');intake.pop('fingerprint',None);refresh.dump(data,'sources/intake.json',intake)
                def git(*args):return subprocess.run(['git',*args],cwd=repo,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
                git('init','-q');git('add','.')
                git('-c','user.name=Test','-c','user.email=test@users.noreply.github.com','commit','-qm','fixture')
                if nested:
                    (repo/'unrelated.json').write_text('preserve me')
                    git('add','unrelated.json')
                with patch.object(refresh,'ROOT',data),patch.object(refresh,'api',api),patch.object(refresh,'content',content),patch.object(refresh,'pages',lambda *a:pulls),contextlib.redirect_stdout(io.StringIO()):
                    refresh.main()
                    summary=json.loads((repo/'.git/refresh-summary.json').read_text())
                    self.assertIn('registry.json',summary['changed_files'])
                    self.assertTrue(refresh.load(data,'registry.json')['updated_at'].endswith('Z'))
                    git('add','.')
                    git('-c','user.name=Test','-c','user.email=test@users.noreply.github.com','commit','-qm','refresh')
                    refresh.main()
                    self.assertEqual(json.loads((repo/'.git/refresh-summary.json').read_text())['changed_files'],[])
                if nested:self.assertEqual((repo/'unrelated.json').read_text(),'preserve me')

if __name__=='__main__':unittest.main()
