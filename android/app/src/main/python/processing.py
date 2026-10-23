from PIL import Image, ImageOps, UnidentifiedImageError, features
import numpy as np
import cv2
from deripple import clean

def _android_bitmap(source):
    # Pillow's Android wheel omits WebP; use the platform codec for those inputs.
    from java import jclass
    factory = jclass('android.graphics.BitmapFactory')
    options = jclass('android.graphics.BitmapFactory$Options')()
    options.inJustDecodeBounds = True
    factory.decodeFile(source, options)
    if options.outWidth <= 0 or options.outHeight <= 0:
        raise ValueError('无法解码此图片格式。')
    if options.outWidth * options.outHeight > 16000000:
        raise ValueError('图片超过 1600 万像素，请先缩小图片。')
    options.inJustDecodeBounds = False
    bitmap = factory.decodeFile(source, options)
    if bitmap is None:
        raise ValueError('无法解码图片，或设备内存不足。')
    return bitmap

def _android_save(source, target, fmt):
    from java import jclass
    bitmap = _android_bitmap(source)
    stream = jclass('java.io.FileOutputStream')(target)
    try:
        codec = jclass('android.graphics.Bitmap$CompressFormat')
        if not bitmap.compress(codec.WEBP if fmt == 'WEBP' else codec.PNG, 95, stream):
            raise ValueError('图片编码失败。')
    finally:
        stream.close()
        bitmap.recycle()

def prepare(source, target):
    try:
        image = Image.open(source)
    except UnidentifiedImageError:
        _android_save(source, target, 'PNG')
        return
    with image:
        if image.width * image.height > 16000000:
            raise ValueError('图片超过 1600 万像素，请先缩小图片。')
        ImageOps.exif_transpose(image).convert('RGBA').save(target)

def process(source, target, mode, strength, progress=None):
    def report(stage):
        if progress is not None:
            progress.onPythonStage(stage)

    report('步骤 1/4 · 读取像素（CPU）')
    with Image.open(source) as image:
        rgba = image.convert('RGBA')
    rgb = np.array(rgba.convert('RGB'))
    report('步骤 2/4 · 执行降噪（CPU）')
    if mode == 2:
        out = clean(rgb, 2., 3.) if strength < 3 else clean(rgb, 5., 5.5)
        if strength == 1:
            out = np.round(rgb * .5 + out * .5).astype(np.uint8)
    else:
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        if mode == 3:
            out = cv2.fastNlMeansDenoisingColored(bgr, None, strength, strength, 7, 21)
        elif mode == 4:
            out = cv2.bilateralFilter(bgr, 9, strength * 4, 9)
        else:
            out = cv2.medianBlur(bgr, 3 if strength < 10 else 5 if strength < 20 else 7)
        out = cv2.cvtColor(out, cv2.COLOR_BGR2RGB)
    report('步骤 3/4 · 合成颜色与透明度（CPU）')
    result = Image.fromarray(out)
    result.putalpha(rgba.getchannel('A'))
    report('步骤 4/4 · 编码并保存结果（CPU）')
    result.save(target)

def export(source, target, fmt):
    if fmt == 'WEBP' and not features.check('webp'):
        _android_save(source, target, fmt)
        return
    with Image.open(source) as im:
        if fmt == 'JPEG':
            bg = Image.new('RGB', im.size, 'white')
            bg.paste(im, mask=im.getchannel('A') if 'A' in im.getbands() else None)
            im = bg
        im.save(target, format=fmt, quality=95)
