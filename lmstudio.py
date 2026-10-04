"""Loopback-only LM Studio client with native model discovery and cancellable SSE."""
import asyncio
import json
import os
from urllib.parse import urlparse
import requests
import httpx

DEFAULT_URL='http://127.0.0.1:1234'

def local_url(raw):
    u=urlparse(raw.rstrip('/'))
    if u.scheme!='http' or u.hostname not in {'127.0.0.1','localhost','::1'} or u.username or u.password or u.path or u.query or u.fragment:
        raise ValueError('LM Studio must use a local HTTP address, for example http://127.0.0.1:1234.')
    if not 1 <= (u.port or 80) <= 65535:raise ValueError('Invalid LM Studio port.')
    return raw.rstrip('/')

def headers():
    value={'Content-Type':'application/json'}
    token=os.environ.get('JARVIS_LM_STUDIO_TOKEN')
    if token:value['Authorization']='Bearer '+token
    return value

def model_list(url=DEFAULT_URL):
    r=requests.get(local_url(url)+'/api/v1/models',headers=headers(),timeout=8)
    r.raise_for_status()
    models=r.json().get('models',[])
    return [m for m in models if m.get('type')=='llm' and m.get('format') in {'gguf','mlx'}
            and not m.get('device_identifier') and not m.get('deviceIdentifier')
            and not m.get('remote_host')]

def validate_model(model,capability,url=DEFAULT_URL):
    models=model_list(url)
    match=next((m for m in models if m['key']==model or any(i.get('id')==model for i in m.get('loaded_instances',[]))),None)
    if match is None:raise ValueError('Model is not in your local LM Studio library. Download it or choose a local model in Settings.')
    key='trained_for_tool_use' if capability=='tools' else capability
    if not match.get('capabilities',{}).get(key):
        raise ValueError(f'{model} does not support {capability}. Choose a compatible local model in Settings.')
    return match

def merge_delta(calls,fragment):
    idx=fragment.get('index',0)
    current=calls.setdefault(idx,{'id':'','type':'function','function':{'name':'','arguments':''}})
    if fragment.get('id'):current['id']+=fragment['id']
    function=fragment.get('function',{})
    for key in ('name','arguments'):
        if function.get(key) is not None:current['function'][key]+=function[key]

def cancel(job):
    loop,task=job.get('inference_loop'),job.get('inference_task')
    if loop and task:
        try:loop.call_soon_threadsafe(task.cancel)
        except RuntimeError:pass

def stream_chat(model,messages,tools,job,on_token,url=DEFAULT_URL,max_tokens=1800):
    return asyncio.run(_stream_chat(model,messages,tools,job,on_token,local_url(url),max_tokens))

async def _stream_chat(model,messages,tools,job,on_token,url,max_tokens):
    job['inference_loop']=asyncio.get_running_loop()
    job['inference_task']=asyncio.current_task()
    try:
        if job['cancel'].is_set():raise InterruptedError('Stopped.')
        payload={'model':model,'messages':messages,'stream':True,'temperature':.2,'max_tokens':max_tokens}
        if tools:payload['tools']=tools
        content='';calls={}
        async with httpx.AsyncClient(timeout=httpx.Timeout(180,connect=8),trust_env=False) as client:
            async with client.stream('POST',url+'/v1/chat/completions',json=payload,headers=headers()) as response:
                if response.status_code!=200:
                    error=await response.aread()
                    raise RuntimeError(f'LM Studio: {response.status_code} '+error[:5000].decode('utf-8',errors='replace'))
                async for line in response.aiter_lines():
                    if job['cancel'].is_set():raise InterruptedError('Stopped.')
                    if not line.startswith('data:'):continue
                    data=line[5:].strip()
                    if data=='[DONE]':break
                    part=json.loads(data)
                    if 'error' in part:raise RuntimeError(str(part['error']))
                    choices=part.get('choices',[])
                    if not choices:continue
                    delta=choices[0].get('delta',{})
                    chunk=delta.get('content') or ''
                    if chunk:content+=chunk;on_token(chunk)
                    for fragment in delta.get('tool_calls',[]):merge_delta(calls,fragment)
        result={'role':'assistant','content':content}
        if calls:
            result['tool_calls']=[]
            for idx,call in sorted(calls.items()):
                if not call['id']:call['id']='call_'+str(idx)
                json.loads(call['function']['arguments'] or '{}')
                call['function']['arguments']=call['function']['arguments'] or '{}'
                result['tool_calls'].append(call)
        return result
    except asyncio.CancelledError:
        raise InterruptedError('Stopped by you.')
    except Exception:
        if job['cancel'].is_set():raise InterruptedError('Stopped by you.')
        raise
    finally:
        job['inference_loop']=None;job['inference_task']=None

def describe_image(model,png_b64,question,url=DEFAULT_URL):
    validate_model(model,'vision',url)
    messages=[{'role':'user','content':[{'type':'text','text':question},
        {'type':'image_url','image_url':{'url':'data:image/png;base64,'+png_b64}}]}]
    r=requests.post(local_url(url)+'/v1/chat/completions',headers=headers(),json={
        'model':model,'messages':messages,'stream':False,'max_tokens':600,'temperature':.1},timeout=(8,180))
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']
