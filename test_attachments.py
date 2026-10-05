import base64,io,json,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
import app,attachments

def sample(size=(80,60)):
    buffer=io.BytesIO();Image.new('RGBA',size,(255,0,0,128)).save(buffer,'PNG')
    return {'name':'sample.png','data':'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()}

class AttachmentTests(unittest.TestCase):
    def test_decode_flattens_transparency_and_stores_only_pixels(self):
        result=attachments.decode([sample()])[0]
        with Image.open(io.BytesIO(result['bytes'])) as image:
            self.assertEqual(image.format,'JPEG');self.assertEqual(image.size,(80,60));self.assertFalse(image.getexif())
            self.assertGreater(image.getpixel((20,20))[1],100)
    def test_large_image_resizes_without_changing_aspect_ratio(self):
        result=attachments.decode([sample((2400,1200))])[0]
        self.assertEqual((result['width'],result['height']),(1600,800))
    def test_fake_image_rejected(self):
        with self.assertRaises(ValueError):attachments.decode([{'data':'data:image/png;base64,YWJj'}])
    def test_svg_and_invalid_base64_rejected(self):
        for data in ('data:image/svg+xml;base64,YWJj','data:image/png;base64,%%%'):
            with self.assertRaises(ValueError):attachments.decode([{'data':data}])
    def test_image_count_and_payload_limits(self):
        for items in ([sample()]*4,{},[{'data':'x'*(6*1024*1024)}]):
            with self.assertRaises(ValueError):attachments.decode(items)
    def test_filename_does_not_control_storage_path(self):
        image=sample();image['name']='../../evil.png'
        with tempfile.TemporaryDirectory() as folder:
            metadata=attachments.save(attachments.decode([image]),folder)
            self.assertEqual(metadata[0]['name'],'evil.png');self.assertEqual(len(metadata[0]['id']),32)
            self.assertTrue(attachments.path(metadata[0]['id'],folder).is_file())
            with self.assertRaises(ValueError):attachments.path('../settings.json',folder)
    def test_vision_observation_reaches_agent_and_history(self):
        with tempfile.TemporaryDirectory() as folder,patch.object(app,'DATA',Path(folder)),patch.object(app,'HISTORY',[]):
            images=attachments.save(attachments.decode([sample()]),folder)
            job={'id':'image-test','images':images,'events':[],'done':False,'cancel':threading.Event(),'approval':None,'decision':None,'process':None}
            cfg={**app.DEFAULTS,'mode':'assistant'}
            with patch.object(app,'validate_model'),patch.object(app.lmstudio,'describe_image',return_value='A red rectangle.') as vision,patch.object(app.lmstudio,'stream_chat',return_value={'role':'assistant','content':'A red rectangle.'}) as chat:
                app.run_job(job,'What color is the shape?',cfg)
            self.assertTrue(job['done']);self.assertEqual(vision.call_args.kwargs['image_mime'],'image/jpeg')
            self.assertIn('A red rectangle.',chat.call_args.args[1][-1]['content'])
            self.assertEqual(app.HISTORY[0]['images'],images);self.assertIn('A red rectangle.',app.HISTORY[0]['image_context'])
            self.assertNotIn('base64',json.dumps(app.HISTORY))
    def test_cancel_skips_vision_and_agent(self):
        job={'id':'stop-images','images':[{}],'events':[],'done':False,'cancel':threading.Event(),'approval':None};job['cancel'].set()
        with tempfile.TemporaryDirectory() as folder,patch.object(app,'DATA',Path(folder)),patch.object(app.lmstudio,'describe_image') as vision:
            app.run_job(job,'Describe',app.DEFAULTS)
        vision.assert_not_called();self.assertTrue(any(e['type']=='stopped' for e in job['events']))

if __name__=='__main__':unittest.main()
