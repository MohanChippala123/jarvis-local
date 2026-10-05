import tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
import app

class AutoApproveTests(unittest.TestCase):
    def setUp(self):
        self.original=dict(app.CONFIG);self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.state=self.root/'state';self.state.mkdir()
        self.data_patch=patch.object(app,'DATA',self.state);self.data_patch.start()
        app.CONFIG.update(roots=[str(self.root)],files=True,auto_approve=True)
        self.job={'id':'auto-test','events':[],'cancel':threading.Event(),'approval':None,'decision':None,'process':None,'done':False}
    def tearDown(self):
        app.CONFIG.clear();app.CONFIG.update(self.original);self.data_patch.stop();self.tmp.cleanup()
    def test_write_without_dialog_preserves_backup(self):
        p=self.root/'file.txt';p.write_text('original')
        result=app.execute('write_file',{'path':str(p),'content':'updated'},self.job,dict(app.CONFIG))
        self.assertEqual(p.read_text(),'updated');self.assertEqual(Path(result['backup']).read_text(),'original')
        self.assertIsNone(self.job['approval']);self.assertTrue(any(e['type']=='auto_approved' for e in self.job['events']))
    def test_stop_still_blocks_auto_approved_action(self):
        self.job['cancel'].set()
        with self.assertRaises(InterruptedError):app.approve(self.job,'write_file',{})
        self.assertFalse(self.job['events'])
    def test_scope_and_disabled_capabilities_still_apply(self):
        config=dict(app.CONFIG)
        with self.assertRaises(PermissionError):app.execute('write_file',{'path':str(self.root.parent/'outside.txt'),'content':'x'},self.job,config)
        app.CONFIG['files']=False
        with self.assertRaises(PermissionError):app.execute('write_file',{'path':str(self.root/'x'),'content':'x'},self.job,config)
        self.assertFalse((self.root/'x').exists())
    def test_switch_can_release_pending_action_and_restore_manual_review(self):
        app.CONFIG['auto_approve']=False
        worker=threading.Thread(target=app.approve,args=(self.job,'write_file',{}));worker.start()
        deadline=time.monotonic()+2
        while self.job['approval'] is None and time.monotonic()<deadline:time.sleep(.01)
        self.assertIsNotNone(self.job['approval'])
        app.CONFIG['auto_approve']=True;worker.join(2);self.assertFalse(worker.is_alive());self.assertIsNone(self.job['approval'])
        app.CONFIG['auto_approve']=False;self.job['decision']=None
        worker=threading.Thread(target=app.approve,args=(self.job,'write_file',{}));worker.start()
        deadline=time.monotonic()+2
        while self.job['approval'] is None and time.monotonic()<deadline:time.sleep(.01)
        self.assertIsNotNone(self.job['approval']);self.job['decision']=True;worker.join(2);self.assertFalse(worker.is_alive())
