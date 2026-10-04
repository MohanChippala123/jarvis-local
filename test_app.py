"""Meaningful permission and lifecycle tests, with a temporary data directory."""
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import requests
import app

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.state=self.root/'state'; self.state.mkdir()
        self.patch=patch.object(app,'DATA',self.state);self.patch.start()
        self.original=dict(app.CONFIG)
        app.CONFIG.update(app.DEFAULTS, roots=[str(self.root)])
        self.config=dict(app.CONFIG)
        self.job={'id':'test','events':[],'cancel':threading.Event(),'approval':None,'decision':None,'process':None,'done':False}
    def tearDown(self):
        app.CONFIG.clear();app.CONFIG.update(self.original)
        self.patch.stop();self.tmp.cleanup()
    def test_paths_cannot_escape(self):
        self.assertEqual(app.path_allowed(str(self.root/'a.txt'),self.config),self.root/'a.txt')
        with self.assertRaises(PermissionError):app.path_allowed(str(self.root/'..'/'outside.txt'),self.config)
        with self.assertRaises(PermissionError):app.path_allowed(str(self.state/'settings.json'),self.config)
    def test_disabled_shell_never_runs(self):
        with self.assertRaises(PermissionError):app.execute('powershell',{'script':'echo nope'},self.job,self.config)
        self.assertIsNone(self.job['approval'])
    def test_cloud_model_rejected_before_inference(self):
        with patch.object(app.lmstudio,'model_list',return_value=[]):
            with self.assertRaises(ValueError):app.validate_model('test-cloud','tools')
    def test_incompatible_model_has_actionable_error(self):
        with patch.object(app.lmstudio,'model_list',return_value=[{'key':'test-vision','capabilities':{'vision':True}}]):
            with self.assertRaisesRegex(ValueError,'does not support tools'):app.validate_model('test-vision','tools')
    def test_cancel_prevents_mutation(self):
        self.job['cancel'].set()
        with self.assertRaises(InterruptedError):app.execute('write_file',{'path':str(self.root/'x'),'content':'x'},self.job,self.config)
        self.assertFalse((self.root/'x').exists())
    def run_approved(self,name,args,decision=True):
        result=[]
        def worker():
            try:result.append(app.execute(name,args,self.job,self.config))
            except Exception as e:result.append(e)
        thread=threading.Thread(target=worker);thread.start()
        deadline=time.monotonic()+3
        while self.job['approval'] is None and thread.is_alive() and time.monotonic()<deadline:time.sleep(.01)
        self.assertIsNotNone(self.job['approval'])
        self.job['decision']=decision;thread.join(3)
        self.assertFalse(thread.is_alive())
        return result[0]
    def test_declined_write_creates_nothing(self):
        result=self.run_approved('write_file',{'path':str(self.root/'x.txt'),'content':'no'},False)
        self.assertIsInstance(result,PermissionError)
        self.assertFalse((self.root/'x.txt').exists())
    def test_approved_write_has_recoverable_backup(self):
        target=self.root/'x.txt';target.write_text('original')
        result=self.run_approved('write_file',{'path':str(target),'content':'updated'})
        self.assertEqual(target.read_text(),'updated')
        self.assertEqual(Path(result['backup']).read_text(),'original')
    def test_recycling_preserves_contents(self):
        target=self.root/'x.txt';target.write_text('keep')
        result=self.run_approved('recycle_file',{'path':str(target)})
        self.assertFalse(target.exists());self.assertEqual(Path(result['recover_from']).read_text(),'keep')
    def test_access_revocation_during_approval(self):
        target=self.root/'x.txt'
        result=[]
        def worker():
            try:result.append(app.execute('write_file',{'path':str(target),'content':'no'},self.job,self.config))
            except Exception as e:result.append(e)
        thread=threading.Thread(target=worker);thread.start()
        deadline=time.monotonic()+3
        while not self.job['approval'] and time.monotonic()<deadline:time.sleep(.01)
        app.CONFIG['files']=False;self.job['decision']=True;thread.join(3)
        self.assertFalse(thread.is_alive());self.assertIsInstance(result[0],PermissionError);self.assertFalse(target.exists())

class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url=f'http://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
    def test_api_requires_token(self):
        self.assertEqual(requests.get(self.url+'/api/state').status_code,403)
    def test_cross_origin_cannot_use_token(self):
        r=requests.post(self.url+'/api/clear',json={},headers={'X-Jarvis-Token':app.TOKEN,'Origin':'https://evil.example'})
        self.assertEqual(r.status_code,403)
    def test_dns_rebinding_host_rejected(self):
        self.assertEqual(requests.get(self.url,headers={'Host':'evil.example'}).status_code,403)
    def test_html_has_session_token(self):
        r=requests.get(self.url);self.assertEqual(r.status_code,200)
        self.assertIn(app.TOKEN,r.text);self.assertNotIn('__TOKEN__',r.text)

if __name__=='__main__':unittest.main()
