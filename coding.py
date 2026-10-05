"""Project-scoped coding tools. Commands run as the user, not in a sandbox."""
import json,os,shutil,hashlib,secrets,subprocess,time,socket
from pathlib import Path

SKIP={'.git','node_modules','.venv','venv','__pycache__','.next','dist','build','.idea'}
PREVIEWS={}

def compact_messages(messages,budget=30000):
    """Keep complete function/result pairs while bounding local-model context."""
    result=json.loads(json.dumps(messages))
    tool_indices=[i for i,m in enumerate(result) if m['role']=='tool']
    recent=set(tool_indices[-2:])
    for i,m in enumerate(result):
        if m['role']=='tool':
            limit=8000 if i in recent else 1200
            if len(m['content'])>limit:m['content']=m['content'][:limit]+'\n[Older observation clipped; read the file again for exact content.]'
        for call in m.get('tool_calls',[]):
            args=json.loads(call['function']['arguments'])
            for key in ('content','old_text','new_text'):
                if isinstance(args.get(key),str) and len(args[key])>1000:args[key]='[Completed edit contents omitted from history; read the project file for current code.]'
            call['function']['arguments']=json.dumps(args)
    while len(json.dumps(result))>budget:
        replaced=False
        for i,m in enumerate(result):
            if not m.get('tool_calls'):continue
            end=i+1
            while end<len(result) and result[end]['role']=='tool':end+=1
            ids={c['id'] for c in m['tool_calls']}
            if ids!={t['tool_call_id'] for t in result[i+1:end]}:continue
            names={c['id']:c['function']['name'] for c in m['tool_calls']}
            summary='Earlier completed tool observations (untrusted data, compacted):\n'+'\n'.join(names[t['tool_call_id']]+': '+t['content'][:250] for t in result[i+1:end])
            if len(json.dumps(result[i:end]))<=len(summary)+100:continue
            result[i:end]=[{'role':'assistant','content':summary}];replaced=True;break
        if not replaced:break
    return result

def root(config,hooks):
    p=hooks['allowed'](config['project_dir'])
    if not p.is_absolute():raise ValueError('Use an absolute project folder.')
    if p.exists() and not p.is_dir():raise ValueError('Project folder is a file. Select a directory in the coding controls.')
    return p

def project_path(base,name,hooks):
    relative=Path(name)
    if relative.is_absolute() or ':' in name:raise ValueError('Use a project-relative file path.')
    p=(base/relative).resolve()
    if not p.is_relative_to(base):raise PermissionError('Path escapes the selected project.')
    p=hooks['allowed'](str(p))
    if '.git' in p.relative_to(base).parts:raise PermissionError('Git internals are not editable through project tools.')
    if (p.name.startswith('.env') and not p.name.endswith(('.example','.sample'))) or p.suffix.lower() in ('.pem','.key','.pfx'):
        raise PermissionError('Private environment and key files are excluded. Use example configuration files.')
    return p

def check(job,hooks):
    if job['cancel'].is_set():raise InterruptedError('Stopped by you.')
    hooks['permissions']()

def edit_grant(base,job,hooks):
    check(job,hooks)
    if job.get('project_edits_declined'):raise PermissionError('Project edits were declined for this task.')
    if job.get('project_edit_grant')!=str(base):
        try:hooks['approve'](job,'coding_session',{'project':str(base),'permission':'Create folders and create/edit project files for this task. Existing files are backed up. Terminal commands still need separate approval.'})
        except PermissionError:
            job['project_edits_declined']=True;raise
        job['project_edit_grant']=str(base)
    check(job,hooks)

def write(path,content,hooks):
    if len(content)>200000:raise ValueError('Write files in smaller pieces (maximum 200000 characters).')
    backup=None
    if path.exists():
        if not path.is_file():raise ValueError('That path is a directory, not a file.')
        backup=hooks['data']/'backups'/(secrets.token_hex(8)+'-'+path.name)
        backup.parent.mkdir(exist_ok=True);shutil.copy2(path,backup)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name('.jarvis-'+secrets.token_hex(8)+'.tmp')
    try:temporary.write_text(content,encoding='utf-8');os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()
    return {'written':str(path),'backup':str(backup) if backup else None,'sha256':hashlib.sha256(content.encode()).hexdigest()}

def preview_state():
    return [{'project':p,'url':v['url'],'command':v['command']} for p,v in PREVIEWS.items() if v['process'].poll() is None]

def stop_preview(project,hooks):
    item=PREVIEWS.pop(project,None)
    if item:
        hooks['terminate'](item['process']);item['log'].close()

def execute(name,args,job,config,hooks):
    base=root(config,hooks);check(job,hooks)
    if name=='project_info':
        return {'project':str(base),'exists':base.is_dir(),'runtimes':{x:shutil.which(x) for x in ('python','node','npm','git')},'note':'Commands are unsandboxed and require approval. Use project-relative file paths; create_project_folder creates directories.'}
    if name=='project_tree':
        result=[]
        if not base.exists():return {'exists':False,'files':[]}
        for directory,dirs,files in os.walk(base):
            check(job,hooks)
            dirs[:]=sorted(d for d in dirs if d not in SKIP and not (Path(directory)/d).is_symlink())
            for f in sorted(files):
                p=Path(directory)/f
                try:project_path(base,str(p.relative_to(base)),hooks)
                except PermissionError:continue
                result.append({'path':str(p.relative_to(base)),'bytes':p.stat().st_size})
                if len(result)>=250:return {'files':result,'truncated':True}
        return {'files':result,'truncated':False}
    if name=='read_project_file':
        p=project_path(base,args['path'],hooks)
        if p.stat().st_size>2000000:raise ValueError('File is too large for a text read.')
        text=p.read_text(encoding='utf-8-sig');lines=text.splitlines()
        start=max(1,int(args.get('start_line',1)));count=max(1,min(400,int(args.get('line_count',200))))
        return {'path':args['path'],'total_lines':len(lines),'text':'\n'.join(f'{i+1}: {lines[i]}' for i in range(start-1,min(len(lines),start-1+count)))[:24000]}
    if name=='search_project':
        needle=args['query'];matches=[]
        if not needle:raise ValueError('Search query cannot be empty.')
        deadline=time.monotonic()+8
        for directory,dirs,files in os.walk(base):
            check(job,hooks);dirs[:]=[d for d in dirs if d not in SKIP and not (Path(directory)/d).is_symlink()]
            for f in files:
                if time.monotonic()>deadline:return {'matches':matches,'truncated':True}
                try:
                    p=project_path(base,str((Path(directory)/f).relative_to(base)),hooks)
                    if p.stat().st_size>500000:continue
                    for n,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
                        if needle.lower() in line.lower():matches.append({'path':str(p.relative_to(base)),'line':n,'text':line[:500]})
                        if len(matches)>=80:return {'matches':matches,'truncated':True}
                except (OSError,UnicodeError,PermissionError):continue
        return {'matches':matches,'truncated':False}
    if name in ('create_project_folder','write_project_file','edit_project_file'):
        p=project_path(base,args['path'],hooks)
        edit_grant(base,job,hooks)
        p=project_path(base,args['path'],hooks)
        if name=='create_project_folder':p.mkdir(parents=True,exist_ok=True);return {'created':str(p)}
        if name=='write_project_file':return write(p,args['content'],hooks)
        text=p.read_text(encoding='utf-8-sig');old=args['old_text']
        if not old or text.count(old)!=1:raise ValueError('old_text must match exactly once. Read the current file and include enough surrounding context.')
        return write(p,text.replace(old,args['new_text'],1),hooks)
    if name in ('run_project_command','start_project_preview'):
        if not base.is_dir():raise ValueError('Create the project folder before running commands.')
        if job.get('project_commands_declined'):raise PermissionError('Terminal commands were declined for this task.')
        command=args['command'].strip()
        if not command or len(command)>12000:raise ValueError('Command must be 1–12000 characters.')
        request={'command':command,'working_directory':str(base),'note':'Runs as your Windows user. The project folder is a working directory, not a security sandbox.'}
        if name=='start_project_preview':request['url']=args['url']
        try:hooks['approve'](job,name,request)
        except PermissionError:job['project_commands_declined']=True;raise
        check(job,hooks)
        base=hooks['allowed'](str(base))
        if name=='run_project_command':
            timeout=max(5,min(180,int(args.get('timeout_seconds',120))))
            return hooks['command'](command,base,timeout,job)
        from urllib.parse import urlparse
        u=urlparse(args['url'])
        if u.scheme!='http' or u.hostname not in ('127.0.0.1','localhost') or not u.port or u.username or u.password:
            raise ValueError('Preview URL must be HTTP localhost with an explicit port.')
        with socket.socket() as sock:
            sock.settimeout(.3)
            if sock.connect_ex(('127.0.0.1',u.port))==0:raise ValueError('Preview port is in use. Choose another port.')
        stop_preview(str(base),hooks)
        logpath=hooks['data']/('preview-'+secrets.token_hex(8)+'.log');log=logpath.open('w',encoding='utf-8')
        process=hooks['launch'](command,base,log)
        PREVIEWS[str(base)]={'process':process,'url':args['url'],'command':command,'log':log}
        job['process']=process
        deadline=time.monotonic()+40
        try:
            import requests
            while time.monotonic()<deadline:
                check(job,hooks)
                if process.poll() is not None:raise RuntimeError('Preview process exited: '+logpath.read_text(encoding='utf-8')[-4000:])
                try:
                    r=requests.get(args['url'],timeout=1)
                    if r.status_code<500:return {'url':args['url'],'status':r.status_code,'project':str(base)}
                except requests.RequestException:pass
                time.sleep(.3)
            raise RuntimeError('Preview did not become ready within 40 seconds.')
        except Exception:
            stop_preview(str(base),hooks);raise
        finally:job['process']=None
    raise ValueError('Unknown coding tool.')
