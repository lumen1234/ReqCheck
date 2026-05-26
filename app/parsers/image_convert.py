"""将 Word 嵌入的 EMF/WMF 转为浏览器可显示的 PNG。"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional, Tuple

# EMF 文件头
_EMF_MAGIC = b'\x01\x00\x00\x00'
# WMF placeable header
_WMF_MAGIC = b'\xd7\xcd\xc6\xa9'


def sniff_image_format(data: bytes) -> Optional[str]:
    if len(data) < 4:
        return None
    if data[:4] == b'\x89PNG':
        return 'png'
    if data[:3] == b'\xff\xd8\xff':
        return 'jpeg'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    if data[:4] == _EMF_MAGIC:
        return 'emf'
    if data[:4] == _WMF_MAGIC:
        return 'wmf'
    return None


def _convert_with_pillow(data: bytes) -> Optional[bytes]:
    if sys.platform != 'win32':
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        with Image.open(io.BytesIO(data)) as im:
            try:
                im.load(dpi=144)
            except Exception:
                im.load()
            if im.mode not in ('RGB', 'RGBA'):
                im = im.convert('RGB')
            out = io.BytesIO()
            im.save(out, format='PNG', optimize=True)
            return out.getvalue()
    except Exception:
        return None


def _convert_with_libreoffice(data: bytes, src_ext: str) -> Optional[bytes]:
    soffice = shutil.which('soffice') or shutil.which('libreoffice')
    if not soffice:
        return None
    src_ext = src_ext if src_ext.startswith('.') else f'.{src_ext}'
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, f'image{src_ext}')
        with open(src, 'wb') as f:
            f.write(data)
        try:
            subprocess.run(
                [soffice, '--headless', '--convert-to', 'png', '--outdir', tmp, src],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        for name in os.listdir(tmp):
            if name.lower().endswith('.png'):
                with open(os.path.join(tmp, name), 'rb') as f:
                    return f.read()
    return None


def _convert_with_imagemagick(data: bytes, src_ext: str) -> Optional[bytes]:
    magick = shutil.which('magick') or shutil.which('convert')
    if not magick:
        return None
    src_ext = src_ext if src_ext.startswith('.') else f'.{src_ext}'
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, f'image{src_ext}')
        dst = os.path.join(tmp, 'image.png')
        with open(src, 'wb') as f:
            f.write(data)
        try:
            subprocess.run(
                [magick, src, dst],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if os.path.isfile(dst):
            with open(dst, 'rb') as f:
                return f.read()
    return None


def ensure_browser_image(data: bytes, ext: str = '.png') -> Tuple[bytes, str]:
    """
    返回可在浏览器 <img> 中显示的栅格图字节与扩展名。
    已是 PNG/JPEG/GIF 则原样返回；EMF/WMF 尝试转为 PNG。
    """
    ext = (ext or '.png').lower()
    if not ext.startswith('.'):
        ext = f'.{ext}'

    fmt = sniff_image_format(data)
    if fmt in ('png', 'jpeg', 'gif'):
        out_ext = '.png' if fmt == 'png' else ('.jpg' if fmt == 'jpeg' else '.gif')
        return data, out_ext

    is_vector = fmt in ('emf', 'wmf') or ext in ('.emf', '.wmf')
    if not is_vector:
        return data, ext

    src_ext = ext if ext in ('.emf', '.wmf') else f'.{fmt or "emf"}'
    for converter in (
        lambda: _convert_with_pillow(data),
        lambda: _convert_with_libreoffice(data, src_ext),
        lambda: _convert_with_imagemagick(data, src_ext),
    ):
        png = converter()
        if png and png[:4] == b'\x89PNG':
            return png, '.png'

    return data, ext


def load_browser_image_file(filepath: str) -> Tuple[bytes, str]:
    """读取磁盘图片；若为 EMF/WMF 则尝试转为 PNG 并回写。"""
    with open(filepath, 'rb') as f:
        data = f.read()
    ext = os.path.splitext(filepath)[1] or '.png'
    png_data, out_ext = ensure_browser_image(data, ext)
    if png_data[:4] == b'\x89PNG' and data[:4] != b'\x89PNG':
        try:
            with open(filepath, 'wb') as f:
                f.write(png_data)
        except OSError:
            pass
    return png_data, out_ext
