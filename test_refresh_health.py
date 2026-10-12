import unittest

from refresh_health import latest_failures


class RefreshHealthTests(unittest.TestCase):
    def run_row(self, number, conclusion='failure', **changes):
        return dict(workflowName='Refresh', databaseId=number, attempt=1,
                    createdAt=f'2026-10-11T{number:02d}:00:00Z',
                    status='completed', conclusion=conclusion, **changes)

    def test_new_success_suppresses_old_failure(self):
        self.assertEqual(list(latest_failures([
            self.run_row(2, 'success'), self.run_row(1)], set())), [])

    def test_new_pending_run_does_not_alert_old_failure(self):
        pending = self.run_row(2, None)
        pending['status'] = 'in_progress'
        self.assertEqual(list(latest_failures([self.run_row(1), pending], set())), [])

    def test_new_failure_alerts_once(self):
        rows = [self.run_row(1, 'success'), self.run_row(2)]
        self.assertEqual(list(latest_failures(rows, set())), [rows[1]])
        self.assertEqual(list(latest_failures(rows, {'2:1'})), [])

    def test_latest_attempt_and_workflow_are_separate(self):
        first = self.run_row(2)
        retry = dict(first, attempt=2, conclusion='success')
        other = dict(self.run_row(1), workflowName='Other')
        self.assertEqual(list(latest_failures([retry, other, first], set())), [other])


if __name__ == '__main__':
    unittest.main()
