"""Regression: sampled zero I/O is a valid observation, not missing data."""
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from experiments.final_benchmark import run_trial
from experiments.workloads import WorkloadSpec, build_workload

class TelemetryZeroTests(unittest.TestCase):
    def sample(self, available):
        import psutil
        process_type=psutil.Process
        class Process:
            def __init__(self,pid):self.real=process_type(pid);self.pid=pid
            def children(self,recursive=True):return []
            def memory_info(self):return self.real.memory_info()
            def cpu_times(self):return self.real.cpu_times()
            def io_counters(self):
                if not available:raise NotImplementedError('unavailable')
                return SimpleNamespace(read_bytes=0,write_bytes=0)
        with TemporaryDirectory() as folder, patch('psutil.Process',Process):
            return run_trial(run_id='zero-regression',phase='test',
                workload=build_workload(WorkloadSpec('zero-test',100,2,10,1)),
                model_key='revon-h',trial_kind='measured',trial=1,threshold=4096,
                scratch_root=Path(folder),timeout_seconds=30)

    def test_observed_zero_is_retained(self):
        row=self.sample(True)
        self.assertEqual(row.status,'ok',row.notes)
        self.assertTrue(row.correctness)
        self.assertEqual(row.process_tree_read_bytes,0)
        self.assertEqual(row.process_tree_write_bytes,0)

    def test_unavailable_remains_missing(self):
        row=self.sample(False)
        self.assertEqual(row.status,'ok',row.notes)
        self.assertIsNone(row.process_tree_read_bytes)
        self.assertIsNone(row.process_tree_write_bytes)

if __name__=='__main__':unittest.main()
