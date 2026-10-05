import json,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
import app,coding

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.data=self.root/'state';self.data.mkdir()
        self.original=dict(app.CONFIG);self.history=list(app.HISTORY)
        app.CONFIG.update(app.DEFAULTS,roots=[str(self.root)],auto_approve=True)
        self.data_patch=patch.object(app,'DATA',self.data);self.data_patch.start()
        self.job={'id':'audit','cancel':threading.Event(),'events':[],'approval':None,'decision':None,'process':None,'done':False}
    def tearDown(self):
        self.data_patch.stop();app.CONFIG.clear();app.CONFIG.update(self.original);app.HISTORY[:]=self.history;self.temp.cleanup()
    def test_malformed_tool_call_returns_error_then_recovers_with_actual_write(self):
        target=self.root/'answer.txt'
        def call(args,identifier):return {'role':'assistant','content':'','tool_calls':[{'id':identifier,'type':'function','function':{'name':'write_file','arguments':args}}]}
        responses=[call('{"path":','bad'),call(json.dumps({'path':str(target),'content':'recovered'}),'good'),{'role':'assistant','content':'Saved the file.'}]
        app.HISTORY.clear()
        with patch.object(app,'validate_model'),patch.object(app.lmstudio,'stream_chat',side_effect=responses):app.run_job(self.job,'Write answer.txt',dict(app.CONFIG))
        self.assertEqual(target.read_text(),'recovered');self.assertTrue(self.job['done'])
        results=[json.loads(e['text']) for e in self.job['events'] if e['type']=='result']
        self.assertIn('error',results[0]);self.assertIn('written',results[1]);self.assertFalse(any(e['type']=='error' for e in self.job['events']))
    def test_compaction_tolerates_malformed_and_nonobject_tool_arguments(self):
        for args in ('{bad','[]','null'):
            messages=[{'role':'assistant','content':'','tool_calls':[{'id':'a','function':{'name':'write_project_file','arguments':args}}]},{'role':'tool','tool_call_id':'a','content':'invalid arguments'}]
            self.assertEqual(len(coding.compact_messages(messages)),2)
    def test_browser_revocation_during_approval_prevents_launch(self):
        config=dict(app.CONFIG)
        def revoke(*args):app.CONFIG['internet']=False
        with patch.object(app,'approve',side_effect=revoke),patch.object(app.subprocess,'Popen') as launch:
            with self.assertRaisesRegex(PermissionError,'Internet'):app.execute('browser_open',{'url':'https://example.com'},self.job,config)
            launch.assert_not_called()
    def test_failed_atomic_replace_preserves_original_general_file(self):
        target=self.root/'answer.txt';target.write_text('original')
        with patch.object(coding.os,'replace',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):app.execute('write_file',{'path':str(target),'content':'updated'},self.job,dict(app.CONFIG))
        self.assertEqual(target.read_text(),'original');self.assertFalse(list(self.root.glob('.jarvis-*.tmp')))
    def test_general_powershell_propagates_native_failure_and_exit_event(self):
        with self.assertRaisesRegex(RuntimeError,'code 7'):app.ps(f'& "{sys.executable}" -c "raise SystemExit(7)"',job=self.job)
        self.assertEqual([e['exit_code'] for e in self.job['events'] if e['type']=='terminal_end'],[7])
    def test_missing_edit_target_is_not_created_and_no_file_change_is_reported(self):
        app.CONFIG.update(project_dir=str(self.root),coding=True,files=True)
        with self.assertRaises(FileNotFoundError):app.execute('edit_project_file',{'path':'missing.py','old_text':'old','new_text':'new'},self.job,{**app.CONFIG,'mode':'code'})
        self.assertFalse((self.root/'missing.py').exists());self.assertFalse(any(e['type']=='file_changed' for e in self.job['events']))
    def test_read_only_requests_and_verified_edits_do_not_trigger_false_repair(self):
        self.assertIsNone(app.coding_gap('Explain how to build the app',[]))
        self.assertIsNone(app.coding_gap('Review the code without edit changes',[]))
        self.assertIsNone(app.coding_gap('Fix the bug',[{'tool':'edit_project_file','result':'{"written":"app.py"}'}]))
        self.assertIsNone(app.coding_gap('Fix it',[{'tool':'edit_project_file','result':'{"error":"User declined"}'}]))
    def test_reading_source_is_not_proof_of_performing_changes_or_running_tests(self):
        reads=[{'tool':'read_project_file','result':'{"text":"original"}'}]
        self.assertIn('source edit',app.coding_gap('Fix the bug',reads))
        self.assertIn('command',app.coding_gap('Run the tests',reads))
    def test_stale_completed_history_cannot_end_new_coding_action(self):
        app.CONFIG.update(project_dir=str(self.root));config={**app.CONFIG,'mode':'code'}
        app.HISTORY[:]=[{'role':'assistant','content':'Already fixed.','mode':'code','project_dir':str(self.root),'observations':[{'tool':'edit_project_file','result':'old success'}]}]
        responses=iter([{'role':'assistant','content':'Already fixed.'},{'role':'assistant','content':'','tool_calls':[{'id':'fresh','type':'function','function':{'name':'write_project_file','arguments':json.dumps({'path':'fresh.py','content':'fresh = True\n'})}}]},{'role':'assistant','content':'Saved fresh.py.'}])
        requested=[];snapshots=[]
        def infer(model,messages,tools,job,*args,**kwargs):
            requested.append(job.get('require_tools'));snapshots.append(json.loads(json.dumps(messages)));return next(responses)
        with patch.object(app,'validate_model'),patch.object(app.lmstudio,'stream_chat',side_effect=infer):app.run_job(self.job,'Fix the source code',config)
        self.assertEqual((self.root/'fresh.py').read_text(),'fresh = True\n');self.assertTrue(requested[0])
        self.assertIn('Previous task context',snapshots[0][1]['content']);self.assertNotIn('old success',snapshots[0][1]['content'])
