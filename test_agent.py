import unittest,threading
from unittest.mock import patch
import app

class AgentTests(unittest.TestCase):
    def test_followup_retains_tool_evidence(self):
        history=[{'role':'user','content':'Open my notes'}, {'role':'assistant','content':'Opened.',
          'observations':[{'tool':'open_app','arguments':{'target':'notepad'},'result':'Opened notepad'}]}]
        self.assertIn('notepad',app.model_history(history)[1]['content'])
        self.assertEqual(set(app.model_history(history)[1]),{'role','content'})
    def test_idle_clarification_is_retried_once(self):
        self.assertTrue(app.needs_action_retry('control my screen then open chrome and reddit','I cannot interpret control my screen. Please clarify.',[]))
        self.assertFalse(app.needs_action_retry('open chrome','I will open Chrome',[{'result':'declined'}]))
        self.assertFalse(app.needs_action_retry('What is a browser?','I can explain it',[]))
    def test_browser_requires_both_capabilities(self):
        config={**app.DEFAULTS,'internet':False}
        self.assertNotIn('browser_open',[t['function']['name'] for t in app.available_tools(config)])
        config={**app.DEFAULTS,'desktop':False}
        self.assertNotIn('browser_open',[t['function']['name'] for t in app.available_tools(config)])
    def test_research_finishes_with_sources(self):
        observations=[{'tool':'web_search','result':'[{"href":"https://reddit.com/test"}]'}]
        self.assertTrue(app.needs_completion_retry('find AI project ideas','Would you like a summary?',observations))
        self.assertFalse(app.needs_completion_retry('find AI project ideas','An idea. https://reddit.com/test',observations))
        observations.append({'tool':'browser_open','result':'User declined this action'})
        self.assertFalse(app.needs_completion_retry('find ideas','Would you like more?',observations))
    def test_browser_names_cannot_inject_arguments(self):
        with self.assertRaises(ValueError):app.browser_executable('chrome --disable-web-security')
    def test_search_recovers_when_first_provider_fails(self):
        calls=[]
        class Search:
            def __init__(self,**kw):pass
            def text(self,query,**kw):
                calls.append(kw['backend'])
                if len(calls)==1:raise RuntimeError('connection reset')
                return [{'href':'https://example.com','title':'Real result'}]
        with patch('ddgs.DDGS',Search):
            result=app.search_web('ideas',{'cancel':threading.Event()})
        self.assertEqual(calls,['bing','duckduckgo'])
        self.assertEqual(result[0]['href'],'https://example.com')
    def test_search_stops_before_retry(self):
        cancel=threading.Event();cancel.set()
        with self.assertRaises(InterruptedError):app.search_web('ideas',{'cancel':cancel})
    def test_blank_search_hits_are_not_evidence(self):
        calls=[]
        class Search:
            def __init__(self,**kw):pass
            def text(self,query,**kw):
                calls.append(query)
                return [{'title':'','href':'','body':''}] if len(calls)==1 else [{'title':'Ideas','href':'https://example.com','body':'Examples'}]
        with patch('ddgs.DDGS',Search):
            result=app.search_web('site:reddit.com "AI project ideas"',{'cancel':threading.Event()})
        self.assertEqual(len(calls),2);self.assertNotIn('"',calls[0])
        self.assertEqual(result[0]['title'],'Ideas')

if __name__=='__main__':unittest.main()
