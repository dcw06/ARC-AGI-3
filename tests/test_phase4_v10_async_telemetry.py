import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from certification.phase4_v10.async_telemetry import AsyncTelemetry, MAX_PENDING
from certification.phase4_v10.evidence import EvidenceStore
from certification.phase4_v10.telemetry import TelemetryWriter, read_telemetry


def record(index):
    return {'uuid':'GPU-test','used_bytes':1,'rss_bytes':2,'scratch_bytes':3,
            'elapsed_seconds':index*.25,'monotonic_seconds':index*.25}


class AsyncTests(unittest.TestCase):
    def test_slow_write_does_not_block_sampling_and_retains_every_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            store=EvidenceStore(temp,'monitor');writer=TelemetryWriter(store)
            original=writer.save;entered=threading.Event();first=[True]
            def delayed(state):
                if first[0]:
                    first[0]=False;entered.set();time.sleep(1.42)
                original(state)
            writer.save=delayed
            stream=AsyncTelemetry(store,{},writer=writer)
            stream.submit(record(0),{})
            self.assertTrue(entered.wait(1))
            intervals=[];previous=time.monotonic()
            for i in range(1,9):
                time.sleep(.25);stream.submit(record(i),{})
                now=time.monotonic();intervals.append(now-previous);previous=now
            stream.finish({'status':'complete'},time.monotonic()+5)
            self.assertLess(max(intervals),1)
            self.assertEqual(read_telemetry(Path(temp)/'monitor')['samples'],[record(i) for i in range(9)])
            self.assertEqual(stream.health()['pending_samples'],0)
            self.assertIn('fsync_seconds',writer.last_timings['last_store_write'])

    def test_queue_full_fails_without_dropping_samples(self):
        with tempfile.TemporaryDirectory() as temp:
            store=EvidenceStore(temp,'monitor');writer=TelemetryWriter(store)
            original=writer.save;release=threading.Event();entered=threading.Event()
            def blocked(state): entered.set();release.wait(3);original(state)
            writer.save=blocked;stream=AsyncTelemetry(store,{},writer=writer)
            try:
                stream.submit(record(0),{});self.assertTrue(entered.wait(1))
                for i in range(1,MAX_PENDING): stream.submit(record(i),{})
                with self.assertRaises(OverflowError):stream.submit(record(MAX_PENDING),{})
            finally:
                release.set();stream.finish({},time.monotonic()+5)
            self.assertEqual(len(read_telemetry(Path(temp)/'monitor')['samples']),MAX_PENDING)

    def test_writer_error_propagates_and_no_ready_published(self):
        with tempfile.TemporaryDirectory() as temp:
            store=EvidenceStore(temp,'monitor');writer=TelemetryWriter(store)
            def fail(_):raise OSError('disk failed')
            writer.save=fail;stream=AsyncTelemetry(store,{},writer=writer)
            stream.submit(record(0),{});stream.thread.join(1)
            with self.assertRaisesRegex(RuntimeError,'disk failed'):stream.health()
            self.assertFalse((Path(temp)/'monitor/ready.json').exists())

    def test_backlog_age_and_drain_timeout(self):
        with tempfile.TemporaryDirectory() as temp:
            store=EvidenceStore(temp,'monitor');writer=TelemetryWriter(store)
            release=threading.Event();entered=threading.Event();clock=[0]
            def blocked(_):entered.set();release.wait(3)
            writer.save=blocked;stream=AsyncTelemetry(store,{},writer=writer,clock=lambda:clock[0])
            try:
                stream.submit(record(0),{});self.assertTrue(entered.wait(1));clock[0]=6
                with self.assertRaises(TimeoutError):stream.health()
                clock[0]=0
                with self.assertRaisesRegex(TimeoutError,'drain'):stream.finish({},0)
            finally:release.set();stream.thread.join(2)

    def test_readiness_checkpoint_frozen_until_ack(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);store=EvidenceStore(root,'monitor');ack=root/'control/ack.json'
            stream=AsyncTelemetry(store,{'nonce':'test'},acknowledgement=ack)
            stream.submit(record(0),{})
            until=time.monotonic()+2
            while not (root/'monitor/ready.json').exists() and time.monotonic()<until:time.sleep(.01)
            stream.submit(record(1),{})
            self.assertEqual(read_telemetry(root/'monitor')['samples'],[record(0)])
            EvidenceStore(root,'control').save('ack.json',{'ack':True});stream.finish({},time.monotonic()+5)
            self.assertEqual(read_telemetry(root/'monitor')['samples'],[record(0),record(1)])
