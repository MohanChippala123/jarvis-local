import json,threading,time,unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import lmstudio

class ModelTests(unittest.TestCase):
    def test_offline_server_has_actionable_message(self):
        with patch.object(lmstudio.requests,'get',side_effect=lmstudio.requests.ConnectionError('connection refused')):
            with self.assertRaisesRegex(RuntimeError,'Developer tab'):lmstudio.model_list()
    def test_remote_endpoints_rejected(self):
        for url in ['https://api.openai.com','http://example.com','http://127.0.0.1:1234/v1','http://user:pass@localhost:1234']:
            with self.assertRaises(ValueError):lmstudio.local_url(url)
    def test_streamed_tool_arguments_assemble(self):
        calls={}
        lmstudio.merge_delta(calls,{'index':0,'id':'call_1','function':{'name':'read_file','arguments':'{"path":'}})
        lmstudio.merge_delta(calls,{'index':0,'function':{'arguments':'"C:/test.txt"}'}})
        self.assertEqual(calls[0]['id'],'call_1')
        self.assertEqual(json.loads(calls[0]['function']['arguments']),{'path':'C:/test.txt'})
    def test_local_model_metadata_validation(self):
        with patch.object(lmstudio,'model_list',return_value=[{'key':'local','capabilities':{'vision':True,'trained_for_tool_use':True}}]):
            self.assertEqual(lmstudio.validate_model('local','tools')['key'],'local')
            self.assertEqual(lmstudio.validate_model('local','vision')['key'],'local')
            with self.assertRaises(ValueError):lmstudio.validate_model('remote','tools')
    def test_network_stream_can_be_stopped(self):
        ready=threading.Event()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                self.wfile.write(b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n');self.wfile.flush()
                ready.set();time.sleep(2)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        job={'cancel':threading.Event()};out=[]
        def worker():
            try:lmstudio.stream_chat('test',[],[],job,lambda x:None,f'http://127.0.0.1:{server.server_port}')
            except Exception as e:out.append(e)
        thread=threading.Thread(target=worker);thread.start();self.assertTrue(ready.wait(3))
        job['cancel'].set();lmstudio.cancel(job);thread.join(1)
        self.assertFalse(thread.is_alive());self.assertIsInstance(out[0],InterruptedError)
        server.shutdown();server.server_close()

if __name__=='__main__':unittest.main()
