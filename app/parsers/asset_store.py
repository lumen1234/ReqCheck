import os
import shutil
from typing import Optional

from app.parsers.image_convert import ensure_browser_image, sniff_image_format
from app.parsers.models import ImageData


class AssetStore:
    def __init__(self, doc_id: str, base_folder: str):
        self.doc_id = doc_id
        self.folder = os.path.join(base_folder, doc_id, 'assets')
        os.makedirs(self.folder, exist_ok=True)
        self._counter = 0

    def save_bytes(self, data: bytes, ext: str, alt: str = '', caption: Optional[str] = None) -> ImageData:
        self._counter += 1
        data, ext = ensure_browser_image(data, ext)
        ext = ext if ext.startswith('.') else f'.{ext}'
        if sniff_image_format(data) not in ('png', 'jpeg', 'gif'):
            # 转换失败时保留原始扩展名，避免 EMF 冒充 PNG
            if sniff_image_format(data) in ('emf', 'wmf'):
                ext = '.emf'
        if ext.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg', '.emf'):
            ext = '.png'
        asset_id = f'img_{self._counter:03d}'
        filename = f'{asset_id}{ext}'
        path = os.path.join(self.folder, filename)
        with open(path, 'wb') as f:
            f.write(data)
        return ImageData(asset_id=asset_id, filename=filename, alt=alt, caption=caption)

    def copy_file(self, src_path: str, alt: str = '', caption: Optional[str] = None) -> Optional[ImageData]:
        if not src_path or not os.path.isfile(src_path):
            return None
        ext = os.path.splitext(src_path)[1] or '.png'
        with open(src_path, 'rb') as f:
            return self.save_bytes(f.read(), ext, alt=alt, caption=caption)

    def resolve_md_image(self, src: str, md_filepath: str) -> Optional[ImageData]:
        if not src:
            return None
        if src.startswith(('http://', 'https://', 'data:')):
            return None
        base = os.path.dirname(os.path.abspath(md_filepath))
        candidate = os.path.normpath(os.path.join(base, src))
        return self.copy_file(candidate, alt=os.path.basename(src))

    @staticmethod
    def remove_doc_assets(doc_id: str, base_folder: str) -> None:
        folder = os.path.join(base_folder, doc_id)
        if os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
