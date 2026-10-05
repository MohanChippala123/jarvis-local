import unittest,tempfile,threading,json,sys
from pathlib import Path
from unittest.mock import patch
import app,coding,lmstudio

class CodingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.data=self.root/'state';self.data.mkdir()
        self.project=self.root/'project'
        self.old=dict(app.CONFIG);app.CONFIG.update(app.DEFAULTS,roots=[str(self.root)],project_dir=str(self.project))
        self.config={**app.CONFIG,'mode':'code'}
        self.state=patch.object(app,'DATA',self.data);self.state.start()
        self.job={'id':'coding-test','events':[],'cancel':threading.Event(),'approval':None,'decision':None,'process':None,'done':False}
        self.approvals=[]
        def approve(job,name,args):self.approvals.append(name)
        self.approve=patch.object(app,'approve',side_effect=approve);self.approve.start()
    def tearDown(self):
        for p in list(coding.PREVIEWS):coding.stop_preview(p,app.coding_hooks())
        self.approve.stop();self.state.stop();app.CONFIG.clear();app.CONFIG.update(self.old);self.tmp.cleanup()
    def execute(self,name,args):return app.execute(name,args,self.job,self.config)
    def test_new_project_and_single_task_edit_grant(self):
        self.execute('create_project_folder',{'path':'.'})
        self.execute('write_project_file',{'path':'src/main.py','content':'answer = 42'})
        self.assertEqual((self.project/'src/main.py').read_text(),'answer = 42')
        self.assertEqual(self.approvals,['coding_session'])
    def test_paths_cannot_escape_project_or_use_absolute_paths(self):
        for path in ('../outside.py',str(self.root/'outside.py')):
            with self.assertRaises((PermissionError,ValueError)):self.execute('write_project_file',{'path':path,'content':'no'})
        self.assertEqual(self.approvals,[])
    def test_git_and_secrets_excluded(self):
        for path in ('.git/config','.env','.env.local','private.key'):
            with self.assertRaises(PermissionError):self.execute('write_project_file',{'path':path,'content':'no'})
    def test_exact_edit_has_backup(self):
        self.project.mkdir();p=self.project/'main.py';p.write_text('return_value = 1\n')
        result=self.execute('edit_project_file',{'path':'main.py','old_text':'return_value = 1','new_text':'return_value = 2'})
        self.assertEqual(p.read_text(),'return_value = 2\n');self.assertEqual(Path(result['backup']).read_text(),'return_value = 1\n')
    def test_ambiguous_edit_does_not_change_file(self):
        self.project.mkdir();p=self.project/'main.py';p.write_text('a\na\n')
        with self.assertRaises(ValueError):self.execute('edit_project_file',{'path':'main.py','old_text':'a','new_text':'b'})
        self.assertEqual(p.read_text(),'a\na\n')
    def test_declined_edit_grant_cannot_be_retried(self):
        with patch.object(app,'approve',side_effect=PermissionError('User declined')) as approval:
            for _ in range(2):
                with self.assertRaises(PermissionError):self.execute('write_project_file',{'path':'x','content':'no'})
            self.assertEqual(approval.call_count,1)
        self.assertFalse(self.project.exists())
    def test_revocation_after_grant_blocks_write(self):
        def revoke(*args):app.CONFIG['coding']=False
        with patch.object(app,'approve',side_effect=revoke):
            with self.assertRaises(PermissionError):self.execute('write_project_file',{'path':'x','content':'no'})
        self.assertFalse(self.project.exists())
    def test_read_and_search_return_real_line_numbers(self):
        self.project.mkdir();(self.project/'main.py').write_text('first\nimportant line\nlast\n')
        self.assertEqual(self.execute('search_project',{'query':'important'})['matches'][0]['line'],2)
        self.assertEqual(self.execute('read_project_file',{'path':'main.py','start_line':2,'line_count':1})['text'],'2: important line')
    def test_command_failure_is_observable(self):
        self.project.mkdir()
        result=self.execute('run_project_command',{'command':f'& "{sys.executable}" -c "print(123); raise SystemExit(3)"'})
        self.assertEqual(result['exit_code'],3);self.assertIn('123',result['stdout']);self.assertEqual(self.approvals,['run_project_command'])
    def test_command_denial_never_launches(self):
        self.project.mkdir()
        with patch.object(app,'approve',side_effect=PermissionError('Declined')),patch.object(app,'launch_project_command') as launch:
            with self.assertRaises(PermissionError):self.execute('run_project_command',{'command':'echo no'})
            launch.assert_not_called()
    def test_committed_edit_event_and_no_event_after_rejected_edit(self):
        self.execute('write_project_file',{'path':'main.py','content':'old\n'})
        self.execute('edit_project_file',{'path':'main.py','old_text':'old','new_text':'new'})
        changes=[e for e in self.job['events'] if e['type']=='file_changed']
        self.assertEqual(changes[-1]['content'],(self.project/'main.py').read_text())
        self.assertEqual(changes[-1]['path'],'main.py');self.assertIn('-old',changes[-1]['diff'])
        with self.assertRaises(ValueError):self.execute('edit_project_file',{'path':'main.py','old_text':'missing','new_text':'no'})
        self.assertEqual(len([e for e in self.job['events'] if e['type']=='file_changed']),2)
    def test_coding_disabled_and_files_disabled_hide_tools(self):
        for toggle in ('coding','files'):
            config={**self.config,toggle:False}
            self.assertNotIn('write_project_file',[t['function']['name'] for t in app.available_tools(config)])

class ModelLoadTests(unittest.TestCase):
    def test_compaction_keeps_tool_responses_paired(self):
        messages=[{'role':'system','content':'Policy'},{'role':'user','content':'Build a project'}]
        for i in range(8):
            messages.extend([{'role':'assistant','content':'','tool_calls':[{'id':str(i),'type':'function','function':{'name':'write_project_file','arguments':json.dumps({'path':'main.py','content':'x'*20000})}}]}, {'role':'tool','tool_call_id':str(i),'content':'done '+('x'*12000)}])
        result=coding.compact_messages(messages,budget=12000)
        self.assertLess(len(json.dumps(result)),13000)
        for i,m in enumerate(result):
            if m.get('tool_calls'):self.assertEqual(result[i+1]['tool_call_id'],m['tool_calls'][0]['id'])
        self.assertEqual(messages[2]['tool_calls'][0]['function']['arguments'],json.dumps({'path':'main.py','content':'x'*20000}))
    def test_loaded_model_does_not_reload(self):
        with patch.object(lmstudio,'validate_model',return_value={'key':'local-code','loaded_instances':[{'id':'local-code'}]}),patch.object(lmstudio.requests,'post') as post:
            self.assertEqual(lmstudio.load_model('local-code')['status'],'loaded');post.assert_not_called()
    def test_unloaded_model_uses_native_loopback_load(self):
        with patch.object(lmstudio,'validate_model',return_value={'key':'local-code'}),patch.object(lmstudio.requests,'post') as post:
            post.return_value.json.return_value={'status':'loaded'}
            self.assertEqual(lmstudio.load_model('local-code')['status'],'loaded')
            self.assertEqual(post.call_args.args[0],'http://127.0.0.1:1234/api/v1/models/load')
            self.assertEqual(post.call_args.kwargs['json']['model'],'local-code')

if __name__=='__main__':unittest.main()
