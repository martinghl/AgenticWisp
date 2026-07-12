import os
import tempfile
import unittest

from agenticwisp import demo, protocol
from agenticwisp.wispd import SessionStore


class DemoSceneTest(unittest.TestCase):
    def test_seed_writes_roster_and_usage(self):
        roster, proj = tempfile.mkdtemp(), tempfile.mkdtemp()
        demo.seed(roster, proj)
        for row in demo.SESSIONS:
            sid = row[0]
            self.assertTrue(os.path.exists(os.path.join(roster, sid + ".json")))
            self.assertTrue(os.path.exists(os.path.join(proj, "proj", sid + ".jsonl")))

    def test_every_stage_aggregates_to_its_target(self):
        for target in demo.STATE_CYCLE:
            sess, subs = demo.STAGE[target]
            self.assertEqual(protocol.aggregate(sess + subs), target)

    def test_cycle_covers_all_five_states(self):
        self.assertEqual(set(demo.STATE_CYCLE),
                         {"idle", "thinking", "tool", "waiting", "error"})

    def test_apply_stage_runs_against_a_real_store(self):
        store = SessionStore()
        demo.apply_stage(store, "tool")  # must not raise; store now populated
        self.assertTrue(store.snapshot())

    def test_grow_usage_appends_one_line_per_session(self):
        proj = tempfile.mkdtemp()
        demo.seed(tempfile.mkdtemp(), proj)
        p = os.path.join(proj, "proj", demo.SESSIONS[0][0] + ".jsonl")
        with open(p) as f:
            before = sum(1 for _ in f)
        demo.grow_usage(proj, 1)
        with open(p) as f:
            after = sum(1 for _ in f)
        self.assertEqual(after, before + 1)
