"""One bounded lossless writer; sampling never waits for filesystem persistence."""
import copy
import json
import queue
import threading
import time
from certification.phase4_transient_v2.telemetry import TelemetryWriter, MAX_SAMPLES

MAX_PENDING=32
MAX_PENDING_SECONDS=5


class AsyncTelemetry:
    def __init__(self, store, ready, *, writer=None, clock=time.monotonic, acknowledgement=None):
        self.store,self.ready,self.clock=store,ready,clock
        self.acknowledgement=acknowledgement
        self.writer=writer or TelemetryWriter(store)
        self.queue=queue.Queue(maxsize=MAX_PENDING+1)
        self.lock=threading.Lock()
        self.pending=[]
        self.error=None
        self.closed=False
        self.persisted=0
        self.timings={}
        self.thread=threading.Thread(target=self._run,daemon=True)
        self.thread.start()

    def health(self):
        with self.lock:
            if self.error: raise RuntimeError('telemetry writer failed: '+self.error)
            if self.pending and self.clock()-self.pending[0]>MAX_PENDING_SECONDS:
                raise TimeoutError('telemetry persistence backlog age exceeded')
            return {'pending_samples':len(self.pending),'persisted_samples':self.persisted,
                    'last_persistence':dict(self.timings)}

    def submit(self, record, metadata):
        self.health()
        # Bound every queued item, not just the number of references.
        item=copy.deepcopy((record,metadata))
        if len(json.dumps(item,allow_nan=False).encode())>8192:
            raise ValueError('telemetry queue item too large')
        with self.lock:
            if self.closed: raise RuntimeError('telemetry writer closed')
            if len(self.pending)>=MAX_PENDING: raise OverflowError('telemetry persistence backlog full')
            self.pending.append(self.clock())
        self.queue.put_nowait(item)

    def finish(self, metadata, deadline):
        self.health()
        self.closed=True
        self.queue.put_nowait((None,copy.deepcopy(metadata)))
        self.thread.join(max(0,min(MAX_PENDING_SECONDS,deadline-self.clock())))
        if self.thread.is_alive(): raise TimeoutError('telemetry writer drain deadline')
        self.health()
        if self.pending: raise RuntimeError('telemetry loss at finalization')

    def _run(self):
        samples=[]
        ready=False
        try:
            while True:
                record,meta=self.queue.get()
                batch=[]
                done=record is None
                if not done: batch.append(record)
                while not done:
                    try: record,new_meta=self.queue.get_nowait()
                    except queue.Empty: break
                    meta=new_meta
                    if record is None: done=True
                    else: batch.append(record)
                samples.extend(batch)
                if len(samples)>MAX_SAMPLES: raise ValueError('telemetry sample count exhausted')
                state={**meta,'samples':samples}
                begin=self.clock()
                self.writer.save(state)
                if not ready:
                    self.store.save('ready.json',{**self.ready,'sample':samples[0]})
                    ready=True
                    # Freeze the initial checkpoint while the supervisor verifies
                    # it. Sampling continues into the bounded queue meanwhile.
                    if self.acknowledgement is not None:
                        until=self.clock()+MAX_PENDING_SECONDS
                        while not self.acknowledgement.exists():
                            if self.clock()>=until: raise TimeoutError('ready acknowledgement timeout')
                            time.sleep(.01)
                duration=self.clock()-begin
                with self.lock:
                    if self.pending and self.clock()-self.pending[0]>MAX_PENDING_SECONDS:
                        raise TimeoutError('telemetry persistence backlog age exceeded')
                    del self.pending[:len(batch)]
                    self.persisted=len(samples)
                    self.timings={'total_seconds':duration,
                        **getattr(self.writer,'last_timings',{})}
                if done: return
        except Exception as exc:
            with self.lock: self.error=type(exc).__name__+': '+str(exc)[:256]
