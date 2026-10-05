"""Bounded image decoding and private local attachment storage."""
import base64,io,re,secrets,warnings
from pathlib import Path
from PIL import Image,ImageOps

MAX_IMAGES=3
MAX_BYTES=4*1024*1024

def decode(items):
    if not isinstance(items,list) or len(items)>MAX_IMAGES:raise ValueError('Attach up to 3 images per message.')
    decoded=[]
    for item in items:
        if not isinstance(item,dict):raise ValueError('Invalid image attachment.')
        data=item.get('data','')
        if not isinstance(data,str) or len(data)>MAX_BYTES*4//3+200:raise ValueError('Image is too large. Maximum 4 MB per uploaded image.')
        if not re.match(r'^data:image/(?:png|jpeg|webp|gif);base64,',data):raise ValueError('Use PNG, JPEG, WebP or GIF images.')
        try:
            raw=base64.b64decode(data.split(',',1)[1],validate=True)
            if len(raw)>MAX_BYTES:raise ValueError('Image is too large.')
            with warnings.catch_warnings():
                warnings.simplefilter('error',Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(raw)) as check:
                    if check.format not in ('PNG','JPEG','WEBP','GIF'):raise ValueError('Unsupported image format.')
                    if check.width*check.height>20_000_000:raise ValueError('Image exceeds 20 megapixels.')
                    check.verify()
                with Image.open(io.BytesIO(raw)) as image:
                    image=ImageOps.exif_transpose(image)
                    image.thumbnail((1600,1600),Image.Resampling.LANCZOS)
                    rgba=image.convert('RGBA');background=Image.new('RGB',image.size,'white');background.paste(rgba,mask=rgba.getchannel('A'))
                    buf=io.BytesIO();background.save(buf,format='JPEG',quality=90)
            name=str(item.get('name','image')).replace('\\','/').split('/')[-1][:120]
            decoded.append({'name':name or 'image','bytes':buf.getvalue(),'width':background.width,'height':background.height})
        except ValueError:raise
        except Exception as e:raise ValueError('Cannot read this image. Use a valid PNG, JPEG, WebP or GIF.') from e
    return decoded

def save(decoded,data_dir):
    folder=Path(data_dir)/'attachments';folder.mkdir(exist_ok=True)
    result=[]
    for item in decoded:
        key=secrets.token_hex(16)
        (folder/(key+'.jpg')).write_bytes(item['bytes'])
        result.append({k:item[k] for k in ('name','width','height')}|{'id':key})
    return result

def path(key,data_dir):
    if not re.fullmatch(r'[0-9a-f]{32}',key):raise ValueError('Invalid image ID.')
    return Path(data_dir)/'attachments'/(key+'.jpg')

def encoded(item,data_dir):
    return base64.b64encode(path(item['id'],data_dir).read_bytes()).decode('ascii')
