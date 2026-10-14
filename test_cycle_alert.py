import json, tempfile, unittest
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

if __name__=='__main__':unittest.main()
