"""Bounded, observable command execution and committed file changes."""
import codecs,difflib,queue,secrets,threading,time

def file_change(path,before,after,emit):
    diff=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before/'+str(path),tofile='after/'+str(path)))
    emit('file_changed',path=str(path),content=after[:24000],diff=diff[:40000],truncated=len(after)>24000 or len(diff)>40000)

def command(process,script,cwd,timeout,job,emit,terminate):
    identifier=secrets.token_hex(6);chunks=queue.Queue(maxsize=128)
    emit('terminal_start',command_id=identifier,command=script,cwd=str(cwd),shell='PowerShell')
    def reader(pipe,stream):
        decoder=codecs.getincrementaldecoder('utf-8')('replace')
        try:
            while True:
                data=pipe.read1(4096)
                if not data:break
                text=decoder.decode(data)
                if text:chunks.put((stream,text))
            remaining=decoder.decode(b'',final=True)
            if remaining:chunks.put((stream,remaining))
        finally:
            pipe.close();chunks.put((stream,None))
    for stream in ('stdout','stderr'):threading.Thread(target=reader,args=(getattr(process,stream),stream),daemon=True).start()
    ends=0;captured={'stdout':'','stderr':''};shown=0;clipped=False;timed_out=False;stopped=False
    deadline=time.monotonic()+timeout
    while ends<2 or process.poll() is None:
        if not (timed_out or stopped):
            stopped=job['cancel'].is_set();timed_out=not stopped and time.monotonic()>=deadline
            if stopped or timed_out:terminate(process)
        try:stream,text=chunks.get(timeout=.05)
        except queue.Empty:continue
        if text is None:ends+=1;continue
        captured[stream]=(captured[stream]+text)[-20000:]
        if shown<200000:
            visible=text[:200000-shown];shown+=len(visible)
            emit('terminal_output',command_id=identifier,stream=stream,text=visible)
        if shown>=200000 and not clipped:
            clipped=True;emit('terminal_output',command_id=identifier,stream='notice',text='\n[Live output limit reached; command continues. Final result retains the last output.]\n')
    emit('terminal_end',command_id=identifier,exit_code=process.returncode,timed_out=timed_out,stopped=stopped)
    if stopped:raise InterruptedError('Stopped by you.')
    result={'exit_code':process.returncode,**captured}
    if timed_out:result['timed_out']=True
    return result

def preview(process,script,cwd,logpath,emit):
    identifier=secrets.token_hex(6)
    emit('terminal_start',command_id=identifier,command=script,cwd=str(cwd),shell='PowerShell',preview=True)
    def watch():
        shown=0;clipped=False;decoder=codecs.getincrementaldecoder('utf-8')('replace')
        with logpath.open('rb') as f:
            while True:
                data=f.read(4096)
                if data:
                    text=decoder.decode(data)
                    if shown<200000:emit('terminal_output',command_id=identifier,stream='stdout',text=text[:200000-shown]);shown+=len(text)
                    if shown>=200000 and not clipped:
                        clipped=True;emit('terminal_output',command_id=identifier,stream='notice',text='\n[Live preview output limit reached; server continues. Full output is in the local preview log.]\n')
                elif process.poll() is not None:break
                else:time.sleep(.15)
            text=decoder.decode(b'',final=True)
            if text and shown<200000:emit('terminal_output',command_id=identifier,stream='stdout',text=text)
        emit('terminal_end',command_id=identifier,exit_code=process.returncode,preview=True)
    threading.Thread(target=watch,daemon=True).start()
