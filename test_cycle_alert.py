import json, os, tempfile, unittest
from unittest import mock
from pathlib import Path
import cycle_alert as c

class CycleAlertTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);(self.root/'.git').mkdir()
        self.log=self.root/'.git/watch-tests.log';self.log.write_text('Ran 82 tests\n\nFAILED (failures=1)\n')
        self.sent=[]
    def tearDown(self):self.tmp.cleanup()
    def send(self,text,key):self.sent.append(text)

    def test_one_alert_per_failing_step_until_it_passes(self):
        self.assertEqual(c.fail('tests',str(self.log),'1',False,self.send,self.root),'alerted')
        self.assertIn("stopped at step 'tests' (exit 1)",self.sent[0]);self.assertIn('FAILED (failures=1)',self.sent[0])
        self.assertIn(str(self.log),self.sent[0])
        self.assertEqual(c.fail('tests',str(self.log),'1',False,self.send,self.root),'already alerted')
        c.fail('discord-intake',str(self.log),'1',True,self.send,self.root)
        self.assertIn('the cycle continued',self.sent[1]);self.assertEqual(len(self.sent),2)
        self.assertEqual(c.ok(['tests'],self.send,self.root),'cleared tests')
        self.assertIn('tests passed again',self.sent[2])
        self.assertEqual(set(json.loads((self.root/c.STATE).read_text())),{'discord-intake'})
        self.assertEqual(set(json.loads((self.root/c.LAST_OK).read_text())),{'tests'})
        self.assertEqual(c.ok(['tests'],self.send,self.root),'nothing to clear');self.assertEqual(len(self.sent),3)
        c.fail('tests',str(self.log),'1',False,self.send,self.root);self.assertEqual(len(self.sent),4)

    def test_failed_delivery_is_not_recorded(self):
        def down(*a):raise RuntimeError('office down')
        with self.assertRaises(RuntimeError):c.fail('tests',str(self.log),'1',False,down,self.root)
        self.assertFalse((self.root/c.STATE).exists())
        self.assertEqual(c.fail('tests',str(self.log),'1',False,self.send,self.root),'alerted')

    def test_missing_log_and_control_characters(self):
        c.fail('pivot-watch',str(self.root/'missing.log'),'2',False,self.send,self.root)
        self.assertIn('log unavailable',self.sent[0])
        self.log.write_text('bad \x1b[31mred\x07 '+'x'*400+'\n')
        c.fail('people-watch',str(self.log),'1',False,self.send,self.root)
        self.assertNotIn('\x1b',self.sent[1]);self.assertLess(len(self.sent[1]),600)

class FreshErrorsTests(unittest.TestCase):
    def test_only_new_errors_count_and_volatile_parts_are_ignored(self):
        before=['a/b: compare from abc1234 failed','Mister: cap 300 reached']
        now=['a/b: compare from 9f8e7d6 failed','Mister: cap 301 reached','Budget exhausted after 360 requests','c/d PR #5: boom']
        self.assertEqual(c.fresh_errors(now,before),['Budget exhausted after 360 requests','c/d PR #5: boom'])
        self.assertEqual(c.fresh_errors(now,before,True),['Budget exhausted after 360 requests'])
        self.assertEqual(c.fresh_errors([],before),[])

class LeadNotifyTests(unittest.TestCase):
    # bos-watch-cycle.timer has no office token: the same alert goes through the signed webhook (Lead, 2026-10-24).
    def run_notify(self,token):
        import poll
        office=mock.Mock(return_value={'messageId':'m1'});hook=mock.Mock();send=mock.Mock(return_value=hook)
        env={'TEST_TOKEN':'x'} if token else {}
        with mock.patch.object(poll,'LOCAL_OFFICE',{'self':'a','lead':'l','token_env':'TEST_TOKEN'}),mock.patch.object(poll,'office',office),\
             mock.patch('deadman.webhook_send',send),mock.patch.dict(os.environ,env,clear=False):
            if not token:os.environ.pop('TEST_TOKEN',None)
            poll.lead_notify('\n\n'.join(['a'*900+' <b>']*3),'id-1','watch-cycle')
        return office,send,hook
    def test_parts_over_the_limit_end_with_a_marker(self):
        import poll
        hook=mock.Mock()
        with mock.patch.object(poll,'LOCAL_OFFICE',{'token_env':'NO_SUCH_TOKEN'}),mock.patch('deadman.webhook_send',mock.Mock(return_value=hook)):
            poll.lead_notify('\n\n'.join(['p%d '%i+'x'*1500 for i in range(6)]),'id-2','watch-cycle')
        texts=[c.args[0]['text'] for c in hook.call_args_list]
        self.assertEqual(len(texts),4);self.assertIn('more parts of this message were not sent',texts[-1]);self.assertTrue(texts[2].startswith('p2 '))
    def test_with_the_token_the_office_api_sends(self):
        office,send,hook=self.run_notify(True)
        office.assert_called_once();send.assert_not_called()
    def test_without_the_token_the_webhook_sends_within_the_digest_size(self):
        import digest_size
        office,send,hook=self.run_notify(False)
        office.assert_not_called();self.assertEqual(send.call_args.args[1],'digest')
        payloads=[c.args[0] for c in hook.call_args_list]
        self.assertGreater(len(payloads),1)
        for payload in payloads:
            self.assertEqual((payload['kind'],payload['channel']),('bos-digest','watch-cycle'))
            self.assertLessEqual(digest_size.escaped(payload['text']),digest_size.LIMIT)
        self.assertEqual(sum(p['text'].count('<b>') for p in payloads),3)

if __name__=='__main__':unittest.main()
