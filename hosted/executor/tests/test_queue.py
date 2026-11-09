import os
import tempfile
import unittest
from executor.queue import Queue, run_once


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, 'jobs.sqlite')
        self.q = Queue(self.path)

    def tearDown(self):
        self.q.db.close()
        self.tmp.cleanup()

    def test_dedup_and_reopen(self):
        self.q.enqueue('same', 'verify', {})
        self.q.enqueue('same', 'verify', {})
        other = Queue(self.path)
        self.assertEqual(other.counts(), {'READY':1})
        other.db.close()

    def test_exclusive_claim_and_owner(self):
        self.q.enqueue('a', 'verify', {})
        j = self.q.claim('one')
        self.assertIsNone(self.q.claim('two'))
        with self.assertRaises(RuntimeError):
            self.q.finish(j, 'two', {})
        self.q.finish(j, 'one', {})

    def test_send_crash_never_retried(self):
        self.q.enqueue('a', 'send', {})
        self.q.claim('one', seconds=-1)
        self.assertIsNone(self.q.claim('two'))
        self.assertEqual(self.q.counts(), {'UNKNOWN':1})

    def test_safe_task_recovers(self):
        self.q.enqueue('a', 'verify', {})
        self.q.claim('one', seconds=-1)
        self.assertEqual(self.q.claim('two')['attempts'], 2)

    def test_missing_adapter_blocks(self):
        self.q.enqueue('a', 'discover', {})
        run_once(self.q, {})
        self.assertEqual(self.q.counts(), {'BLOCKED':1})

    def test_send_error_unknown(self):
        self.q.enqueue('a', 'send', {})
        def fail(_):
            raise TimeoutError('uncertain response')
        run_once(self.q, {'send':fail})
        self.assertEqual(self.q.counts(), {'UNKNOWN':1})

    def test_completion_only_once(self):
        self.q.enqueue('a', 'verify', {})
        calls = []
        run_once(self.q, {'verify':lambda p: calls.append(p)})
        self.assertFalse(run_once(self.q, {}))
        self.assertEqual(len(calls),1)

if __name__ == '__main__':
    unittest.main()
