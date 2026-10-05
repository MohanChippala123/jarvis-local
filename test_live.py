import subprocess,sys,threading,time,unittest
import live

class LiveTests(unittest.TestCase):
    def launch(self,source):return subprocess.Popen([sys.executable,'-u','-c',source],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    def test_output_arrives_before_command_exits_and_errors_are_separate(self):
        process=self.launch("import sys,time;print('early',flush=True);time.sleep(.5);print('failure',file=sys.stderr);sys.exit(3)")
        events=[];seen_before_exit=[]
        def emit(kind,**data):
            events.append({'type':kind,**data})
            if kind=='terminal_output' and 'early' in data['text']:seen_before_exit.append(process.poll() is None)
        result=live.command(process,'actual command','test project',3,{'cancel':threading.Event()},emit,lambda p:p.kill())
        self.assertEqual(seen_before_exit,[True]);self.assertEqual(result['exit_code'],3);self.assertIn('failure',result['stderr'])
        self.assertEqual(events[0]['command'],'actual command');self.assertEqual(events[0]['cwd'],'test project');self.assertEqual(events[-1]['exit_code'],3)
    def test_split_utf8_and_large_stdout_stderr_cannot_deadlock(self):
        process=self.launch("import os;os.write(1,b'\\xe2');os.write(1,b'\\x82\\xac');os.write(1,b'x'*220000);os.write(2,b'y'*100000)")
        events=[];result=live.command(process,'large','.',5,{'cancel':threading.Event()},lambda k,**d:events.append({'type':k,**d}),lambda p:p.kill())
        output=''.join(e['text'] for e in events if e['type']=='terminal_output' and e['stream']=='stdout')
        self.assertTrue(output.startswith('€'));self.assertNotIn('�',output);self.assertEqual(result['exit_code'],0)
        self.assertLessEqual(len(result['stdout']),20000);self.assertTrue(any(e.get('stream')=='notice' for e in events))
    def test_timeout_and_stop_have_observable_end_states(self):
        for stop in (False,True):
            process=self.launch('import time;time.sleep(10)');cancel=threading.Event();events=[]
            if stop:cancel.set()
            args=(process,'sleep','.',.15,{'cancel':cancel},lambda k,**d:events.append({'type':k,**d}),lambda p:p.kill())
            if stop:
                with self.assertRaises(InterruptedError):live.command(*args)
            else:self.assertTrue(live.command(*args)['timed_out'])
            self.assertEqual(events[-1]['type'],'terminal_end');self.assertEqual(events[-1]['stopped'],stop)
    def test_diff_is_committed_content_and_display_is_bounded(self):
        events=[];live.file_change('src/main.py','old\n','new\n',lambda k,**d:events.append(d))
        self.assertEqual(events[0]['content'],'new\n');self.assertIn('-old',events[0]['diff']);self.assertIn('+new',events[0]['diff'])
        live.file_change('big.py','',('a\n'*30000),lambda k,**d:events.append(d))
        self.assertTrue(events[-1]['truncated']);self.assertLessEqual(len(events[-1]['diff']),40000)
