"""Fresh targets, screen scoping, and action lifecycle regression checks."""
import tempfile,time,threading,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch,Mock
import app,screen

class ScreenTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=dict(app.CONFIG)
        app.CONFIG.update(app.DEFAULTS,auto_approve=True)
        self.cfg={**app.CONFIG,'mode':'screen'}
        self.job={'id':'screen-test','events':[],'cancel':threading.Event(),'approval':None,'decision':None}
        self.data=patch.object(app,'DATA',Path(self.tmp.name));self.data.start()
    def tearDown(self):
        self.data.stop();app.CONFIG.clear();app.CONFIG.update(self.old);self.tmp.cleanup()
    def test_screen_mode_excludes_shell_and_file_mutation(self):
        names={t['function']['name'] for t in app.available_tools(self.cfg)}
        self.assertIn('inspect_window',names);self.assertIn('control_action',names)
        self.assertFalse(names&{'powershell','write_file','run_project_command'})
    def test_disabled_control_blocks_inspection_and_input(self):
        app.CONFIG['desktop']=False
        for name in ('inspect_window','control_action'):
            with self.assertRaises(PermissionError):app._execute(name,{},self.job,self.cfg)
    def test_cancel_stops_before_action(self):
        self.job['cancel'].set()
        with self.assertRaises(InterruptedError):app._execute('control_action',{},self.job,self.cfg)
    def test_expired_or_fabricated_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'Stale'):screen.target(self.job,'made-up')
        self.job.update(screen_targets={'a':{}},screen_observed_at=time.monotonic()-46)
        with self.assertRaisesRegex(ValueError,'Stale'):screen.target(self.job,'a')
    def test_changed_runtime_and_password_rejected(self):
        c=Mock();c.element_info=SimpleNamespace(runtime_id=[2],element=SimpleNamespace(CurrentIsPassword=False))
        self.job.update(screen_targets={'a':{'runtime':(1,),'handle':9}},screen_observed_at=time.monotonic())
        with patch.object(screen,'resolve',return_value=c):
            with self.assertRaisesRegex(ValueError,'changed'):screen.target(self.job,'a')
            self.job['screen_targets']['a']['runtime']=(2,);c.element_info.element.CurrentIsPassword=True
            with self.assertRaisesRegex(ValueError,'Password'):screen.target(self.job,'a')
    def test_action_returns_fresh_state_and_invalidates_old_ids(self):
        w=Mock(handle=9);w.window_text.return_value='Scratch'
        rect=SimpleNamespace(left=10,right=30,top=20,bottom=40)
        self.job['screen_targets']={'old':1}
        with patch.object(screen,'target',return_value=(Mock(),9,rect)),patch.object(screen,'window',return_value=w),patch.object(app,'desktop_input',return_value='Completed click') as input_call,patch.object(screen,'observe',return_value={'observation':'new'}) as observe:
            result=app._execute('control_action',{'control_id':'old','window_title':'Scratch','action':'click'},self.job,self.cfg)
        self.assertEqual(result['next']['observation'],'new');self.assertEqual(self.job['screen_targets'],{})
        self.assertEqual(input_call.call_args.args[0]['x'],20);self.assertEqual(observe.call_count,1)
        self.assertTrue(any(e['type']=='auto_approved' for e in self.job['events']))
    def test_wrong_window_never_receives_input(self):
        with patch.object(screen,'target',return_value=(Mock(),9,Mock())),patch.object(screen,'window',return_value=Mock(handle=10)),patch.object(app,'desktop_input') as inp:
            with self.assertRaisesRegex(ValueError,'different window'):app._execute('control_action',{'control_id':'a','window_title':'Wrong','action':'click'},self.job,self.cfg)
        inp.assert_not_called()
    def test_secondary_monitor_negative_coordinates(self):
        with patch.object(screen,'desktop_bounds',return_value=(-1920,0,1920,1080)):
            self.assertTrue(screen.on_desktop(-1500,300));self.assertFalse(screen.on_desktop(-1921,0));self.assertFalse(screen.on_desktop(1920,100))
    def test_screen_prompt_uses_controls_first(self):
        prompt=app.system_prompt(self.cfg)
        self.assertIn('inspect_window',prompt);self.assertIn('WITHOUT a vision',prompt);self.assertIn('Verify',prompt)
    def test_vision_uses_same_cancellable_job(self):
        with patch.object(app.lmstudio,'validate_model'),patch.object(app.lmstudio,'stream_chat',return_value={'content':'Visible button'}) as stream:
            result=app.lmstudio.describe_image('local','png','question',job=self.job)
        self.assertEqual(result,'Visible button');self.assertIs(stream.call_args.args[3],self.job)
    def test_recent_screen_tree_survives_compaction(self):
        text='x'*15000
        messages=[{'role':'tool','content':text,'tool_call_id':'a'}]
        self.assertEqual(app.coding.compact_messages(messages,budget=44000,recent_limit=24000)[0]['content'],text)
    def test_declined_control_never_resolves_or_inputs(self):
        with patch.object(app,'approve',side_effect=PermissionError('Declined')),patch.object(screen,'target') as target:
            with self.assertRaises(PermissionError):app._execute('control_action',{'control_id':'a'},self.job,self.cfg)
        target.assert_not_called()
    def test_named_target_rejects_ambiguous_controls(self):
        view={'controls':[{'id':'a','text':'Search','type':'Edit'},{'id':'b','text':'Search','type':'Button'}]}
        with patch.object(screen,'observe',return_value=view),patch.object(screen,'target',return_value='edit') as target:
            self.assertEqual(screen.named_target('App','Search','Edit',self.job,Mock()),'edit')
            target.assert_called_once_with(self.job,'a')
            with self.assertRaisesRegex(ValueError,'ambiguous'):screen.named_target('App','Search','',self.job,Mock())
    def test_replace_text_is_one_scoped_action_with_readback(self):
        c=Mock();c.element_info.control_type='Edit';w=Mock(handle=9);w.window_text.return_value='Scratch'
        rect=SimpleNamespace(left=10,right=30,top=20,bottom=40)
        with patch.object(screen,'named_target',return_value=(c,9,rect)),patch.object(screen,'window',return_value=w),patch.object(app,'desktop_input') as inp,patch.object(screen,'observe',return_value={'controls':[{'value':'new text'}]}):
            result=app._execute('control_action',{'window_title':'Scratch','control_text':'Input','control_type':'Edit','action':'replace_text','text':'new text'},self.job,self.cfg)
        self.assertEqual([call.args[0]['action'] for call in inp.call_args_list],['hotkey','type'])
        self.assertEqual(inp.call_args_list[0].args[0]['text'],'ctrl+a');self.assertEqual(result['next']['controls'][0]['value'],'new text')
    def test_replace_text_rejects_noneditable_target(self):
        c=Mock();c.element_info.control_type='Button'
        with patch.object(screen,'target',return_value=(c,9,Mock())),patch.object(screen,'window',return_value=Mock(handle=9)),patch.object(app,'desktop_input') as inp:
            with self.assertRaisesRegex(ValueError,'editable'):app._execute('control_action',{'window_title':'Scratch','control_id':'a','action':'replace_text'},self.job,self.cfg)
        inp.assert_not_called()
    def test_screen_batch_performs_only_one_mutation(self):
        calls=[{'id':str(i),'type':'function','function':{'name':'control_action','arguments':'{"window_title":"Scratch","control_id":"a","action":"click"}'}} for i in range(2)]
        responses=[{'role':'assistant','content':'','tool_calls':calls},{'role':'assistant','content':'One button clicked; the second action needs a fresh observation.'}]
        with patch.object(app,'HISTORY',[]),patch.object(app,'validate_model'),patch.object(app.lmstudio,'stream_chat',side_effect=responses),patch.object(app,'execute',return_value={'completed':'click','next':{'controls':[]}}) as execute:
            app.run_job(self.job,'Click the observed button.',self.cfg)
        execute.assert_called_once()
        results=[e['text'] for e in self.job['events'] if e['type']=='result']
        self.assertIn('new turn',results[1]);self.assertTrue(self.job['done'])

if __name__=='__main__':unittest.main()
