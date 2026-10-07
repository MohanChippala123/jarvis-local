"""Fresh Windows accessibility observations, scoped to one task and window."""
import secrets
import time

def desktop_bounds():
    import win32api
    x,y,width,height=[win32api.GetSystemMetrics(i) for i in (76,77,78,79)]
    return x,y,x+width,y+height

def on_desktop(x,y):
    left,top,right,bottom=desktop_bounds()
    return left<=x<right and top<=y<bottom

def capture_image():
    from PIL import ImageGrab
    return ImageGrab.grab(all_screens=True)


def windows():
    import win32gui
    result=[]
    def visit(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title=win32gui.GetWindowText(hwnd)
            if title:
                result.append({'title':title,'handle':hwnd,'rectangle':list(win32gui.GetWindowRect(hwnd)),
                               'foreground':hwnd==win32gui.GetForegroundWindow()})
    win32gui.EnumWindows(visit,None)
    return result[:40]


def window(title):
    from pywinauto import Desktop
    title=str(title).strip()
    if not title:raise ValueError('Choose a window title from list_windows first.')
    candidates=windows()
    exact=[w for w in candidates if w['title'].casefold()==title.casefold()]
    matches=exact or [w for w in candidates if title.casefold() in w['title'].casefold()]
    if len(matches)!=1:raise ValueError('Target must match one visible window. List windows again.')
    return Desktop(backend='uia').window(handle=matches[0]['handle']).wrapper_object()


def observe(title,job,emit,capture=True,query=''):
    started=time.perf_counter()
    w=window(title)
    controls=[];targets={}
    observation=secrets.token_hex(4)
    # Bounding depth and returned text prevents a browser's complete DOM filling context.
    for c in w.descendants(depth=10):
        if len(controls)>=60:break
        try:
            if not c.is_visible():continue
            info=c.element_info
            if info.element.CurrentIsPassword:continue
            r=c.rectangle()
            if r.width()<=0 or r.height()<=0:continue
            kind=info.control_type
            text=c.window_text()[:180]
            if query and query.casefold() not in text.casefold():continue
            if not text and kind not in ('Edit','Button','ComboBox','CheckBox','RadioButton','Slider','TabItem'):continue
            cid=observation+':'+str(len(controls)+1)
            runtime=tuple(info.runtime_id)
            controls.append({'id':cid,'text':text,'type':kind,'automation_id':info.automation_id,'enabled':c.is_enabled(),
                             'rectangle':[r.left,r.top,r.right,r.bottom]})
            if kind=='Edit':
                try:controls[-1]['value']=c.iface_value.CurrentValue[:300]
                except Exception:pass
            # COM wrappers cannot survive CoUninitialize between tool calls.
            # Retain identities only and resolve a live wrapper at action time.
            targets[cid]={'runtime':runtime,'handle':w.handle}
        except Exception:continue
    job['screen_targets']=targets
    job['screen_observed_at']=time.monotonic()
    rect=w.rectangle()
    result={'window_title':w.window_text(),'handle':w.handle,'rectangle':[rect.left,rect.top,rect.right,rect.bottom],
            'controls':controls,'query':query,'limit':60,'observation':observation,'elapsed_ms':round((time.perf_counter()-started)*1000),
            'note':'IDs expire after one control action or 45 seconds. Use fresh returned IDs. If a control is missing, inspect_screen for vision.'}
    if capture:
        import io,base64
        import win32gui
        shot=capture_image();scope='All monitors'
        if win32gui.GetForegroundWindow()==w.handle:
            left,top,right,bottom=desktop_bounds()
            crop=(max(0,rect.left-left),max(0,rect.top-top),min(right-left,rect.right-left),min(bottom-top,rect.bottom-top))
            if crop[2]>crop[0] and crop[3]>crop[1]:
                shot=shot.crop(crop);scope='Target window'
        shot.thumbnail((1100,700))
        buf=io.BytesIO();shot.save(buf,format='PNG',optimize=False)
        emit(job,'screen_frame',image=base64.b64encode(buf.getvalue()).decode(),window=result['window_title'],scope=scope)
    emit(job,'screen_state',window=result['window_title'],controls=len(controls),elapsed_ms=result['elapsed_ms'])
    return result


def resolve(item):
    from pywinauto import Desktop
    w=Desktop(backend='uia').window(handle=item['handle']).wrapper_object()
    for c in w.descendants(depth=10):
        try:
            if tuple(c.element_info.runtime_id)==item['runtime']:return c
        except Exception:continue
    raise ValueError('Control no longer exists. Inspect again.')

def target(job,cid):
    item=job.get('screen_targets',{}).get(cid)
    if not item or time.monotonic()-job.get('screen_observed_at',0)>45:
        raise ValueError('Stale control ID. Call inspect_window again.')
    try:
        c=resolve(item)
        if tuple(c.element_info.runtime_id)!=item['runtime'] or not c.is_visible() or not c.is_enabled():
            raise ValueError('Control changed or is unavailable. Inspect again.')
        if c.element_info.element.CurrentIsPassword:raise ValueError('Password controls are not supported.')
        if c.top_level_parent().handle!=item['handle']:raise ValueError('Control moved to another window. Inspect again.')
        r=c.rectangle()
        if r.width()<=0 or r.height()<=0:raise ValueError('Control has no visible rectangle.')
    except ValueError:raise
    except Exception as e:raise ValueError('Control no longer exists. Inspect again.') from e
    return c,item['handle'],r

def named_target(title,text,kind,job,emit):
    """Resolve a unique observed label freshly, avoiding brittle generated IDs."""
    if not str(text).strip():raise ValueError('Supply control_id or an exact control_text label.')
    view=observe(title,job,emit,capture=False,query=str(text))
    matches=[c for c in view['controls'] if c['text'].casefold()==str(text).casefold() and (not kind or c['type'].casefold()==kind.casefold())]
    if len(matches)!=1:raise ValueError('Control label is missing or ambiguous. Inspect with a query and choose a fresh ID and control type.')
    return target(job,matches[0]['id'])
