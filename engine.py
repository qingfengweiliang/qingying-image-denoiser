"""清影：本地图片降噪。"""
import os
import tempfile
import sys
import subprocess
import threading
import atexit
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

NEURAL_MODE = '二次元降噪 · 推荐'
CUGAN_MODE = 'Real-CUGAN · 线条重建'
REHAB_MODE = 'AI Image Rehab · 杂纹清理'
MODES = [NEURAL_MODE, '精细降噪 · 照片', '快速保边 · 轻噪点', '去除颗粒 · 椒盐噪声', CUGAN_MODE, REHAB_MODE]
SCALES = {NEURAL_MODE:(1,2,4,8,16,32), CUGAN_MODE:(1,2,3,4)}
MAX_OUTPUT_PIXELS = 60_000_000
_processes = set()
_process_lock = threading.Lock()


def native_folder(engine='waifu2x'):
    root = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    return root / 'native' / engine


def supported_scales(mode):
    return SCALES.get(mode, (1,))


def strength_range(mode, scale=1):
    if mode == CUGAN_MODE and scale in (3,4):
        return (3,3)
    return (1,3) if mode in (NEURAL_MODE,CUGAN_MODE,REHAB_MODE) else (1,30)


def strength_label(mode, strength):
    if mode == REHAB_MODE:
        return {1:'轻柔',2:'柔和上色',3:'平涂清理'}.get(strength,str(strength))
    return {1:'低',2:'中',3:'高'}.get(strength,str(strength)) if mode in (NEURAL_MODE,CUGAN_MODE) else str(strength)


def validate_settings(im, mode, strength, scale):
    if mode not in MODES or scale not in supported_scales(mode):
        raise ValueError('当前算法不支持所选放大倍率。')
    low,high = strength_range(mode,scale)
    if not isinstance(strength,int) or not low<=strength<=high:
        raise ValueError('当前算法与倍率不支持所选强度。')
    if im.width*im.height*scale*scale>MAX_OUTPUT_PIXELS:
        raise ValueError('预计输出超过 6000 万像素，请降低倍率或缩小输入图片。')


def cancel_processing():
    with _process_lock:
        processes = list(_processes)
    for process in processes:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


atexit.register(cancel_processing)


def _run_native(args):
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    with _process_lock:
        _processes.add(process)
    try:
        try:
            stdout, stderr = process.communicate(timeout=600)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            raise RuntimeError('神经网络降噪超时，请缩小图片后重试。') from None
        return process.returncode, (stdout + stderr).decode('utf-8', errors='replace')
    finally:
        with _process_lock:
            _processes.discard(process)


def neural_denoise(im, strength, scale=1):
    if strength not in (1, 2, 3):
        raise ValueError('二次元降噪强度应为低、中、高三档（1、2、3）。')
    folder = native_folder()
    executable = folder / 'waifu2x-ncnn-vulkan.exe'
    models = folder / 'models-cunet'
    stem = f'noise{strength}_model' if scale==1 else f'noise{strength}_scale2.0x_model'
    if not executable.is_file() or any(not (models / f'{stem}.{ext}').is_file() for ext in ('bin', 'param')):
        raise FileNotFoundError('内置 Waifu2x 引擎或模型缺失，请保留完整程序文件夹后重试。')
    with tempfile.TemporaryDirectory(prefix='qingying-') as directory:
        original, output = Path(directory) / 'input.png', Path(directory) / 'output.png'
        im.convert('RGB').save(original)
        args = [str(executable), '-i', str(original), '-o', str(output), '-n', str(strength),
                '-s', str(scale), '-t', '256', '-m', str(models), '-j', '1:1:1']
        code, log = _run_native(args)
        if code and any(word in log.lower() for word in ('vulkan', 'vkcreate', 'no gpu', 'no device')):
            raise RuntimeError('二次元降噪需要支持 Vulkan 的显卡及驱动。请更新显卡驱动后重试，或选用传统降噪模式。\n' + log[-1200:])
        if code or not output.is_file():
            raise RuntimeError('Waifu2x 降噪失败，请检查显卡驱动或输入图片。\n' + log[-1800:])
        with Image.open(output) as image:
            result = image.convert('RGB')
        if result.size != (im.width*scale,im.height*scale):
            raise RuntimeError('降噪引擎返回了错误的图片尺寸，已停止导出。')
        if im.mode == 'RGBA':
            result.putalpha(im.getchannel('A').resize(result.size,Image.Resampling.LANCZOS))
        return result


def cugan_denoise(im, strength, scale):
    folder = native_folder('realcugan')
    executable = folder/'realcugan-ncnn-vulkan.exe'
    native_scale = 2 if scale==1 else scale
    models = folder/'models-se'
    stem = f'up{native_scale}x-denoise{strength}x'
    if not executable.is_file() or any(not (models/f'{stem}.{ext}').is_file() for ext in ('bin','param')):
        raise FileNotFoundError('内置 Real-CUGAN 引擎或对应倍率模型缺失。')
    with tempfile.TemporaryDirectory(prefix='qingying-') as directory:
        source,target = Path(directory)/'input.png',Path(directory)/'output.png'
        im.convert('RGB').save(source)
        args=[str(executable),'-i',str(source),'-o',str(target),'-n',str(strength),'-s',str(native_scale),'-t','256','-m',str(models),'-j','1:1:1']
        code,log=_run_native(args)
        if code or not target.is_file():
            raise RuntimeError('Real-CUGAN 处理失败，请检查 Vulkan 显卡驱动。\n'+log[-1600:])
        with Image.open(target) as image:result=image.convert('RGB')
        expected=(im.width*native_scale,im.height*native_scale)
        if result.size!=expected:raise RuntimeError('Real-CUGAN 返回的尺寸异常，已停止导出。')
        if scale==1:result=result.resize(im.size,Image.Resampling.LANCZOS)
        if im.mode=='RGBA':result.putalpha(im.getchannel('A').resize(result.size,Image.Resampling.LANCZOS))
        return result


def rehab_denoise(im,strength):
    from third_party.deripple import clean
    before=np.asarray(im.convert('RGB'))
    after=clean(before,2.,3.) if strength<3 else clean(before,5.,5.5)
    result=Image.fromarray(after)
    if strength==1:result=Image.blend(im.convert('RGB'),result,.5)
    if im.mode=='RGBA':result.putalpha(im.getchannel('A'))
    return result

def load_image(path):
    with Image.open(path) as im:
        if im.width * im.height > 60_000_000:
            raise ValueError('图片超过 6000 万像素，请先缩小后再处理。')
        im = ImageOps.exif_transpose(im)
        return im.convert('RGBA' if 'A' in im.getbands() or 'transparency' in im.info else 'RGB')

def denoise(im, mode, strength, scale=1):
    validate_settings(im,mode,strength,scale)
    if mode == NEURAL_MODE:
        return neural_denoise(im, strength,scale)
    if mode == CUGAN_MODE:
        return cugan_denoise(im,strength,scale)
    if mode == REHAB_MODE:
        return rehab_denoise(im,strength)
    rgb = np.array(im.convert('RGB'))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    if mode == MODES[1]:
        out = cv2.fastNlMeansDenoisingColored(bgr, None, strength, strength, 7, 21)
    elif mode == MODES[2]:
        out = cv2.bilateralFilter(bgr, 9, strength * 4, 9)
    elif mode == MODES[3]:
        out = cv2.medianBlur(bgr, 3 if strength < 10 else 5 if strength < 20 else 7)
    else:
        raise ValueError('未知的降噪模式。')
    result = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
    if im.mode == 'RGBA':
        result.putalpha(im.getchannel('A'))
    return result

def save_image(im, path):
    path = Path(path)
    if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        raise ValueError('请选择 PNG、JPG 或 WebP 输出格式。')
    if path.suffix.lower() in ('.jpg', '.jpeg'):
        if im.mode == 'RGBA':
            background = Image.new('RGB', im.size, 'white')
            background.paste(im, mask=im.getchannel('A'))
            im = background
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.qingying-', suffix=path.suffix, dir=path.parent, delete=False) as f:
            temporary = Path(f.name)
        im.save(temporary, **({'quality': 95, 'subsampling': 0} if path.suffix.lower() in ('.jpg', '.jpeg') else {}))
        os.replace(temporary, path)
    except PermissionError as exc:
        raise PermissionError(f'无法写入：{path}\n请在“输出目录”中选择你有权限的文件夹，再重新导出。\n系统详情：{exc}') from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

def writable_folder(path):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile(dir=path) as f:
        f.write(b'write-check')
    return path

def default_output():
    for base in [Path.home() / 'Pictures', Path.home() / 'Documents', Path(tempfile.gettempdir())]:
        try:
            return writable_folder(base / '清影降噪结果')
        except OSError:
            continue
    raise OSError('无法创建默认输出目录，请检查磁盘空间和文件夹权限。')

