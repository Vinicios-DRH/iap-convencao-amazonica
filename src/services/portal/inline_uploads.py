from src.controllers.b2_utils import get_b2_file_url
from src.services.portal.photos import track_image
from src.services.portal.uploads import save_image_upload


def upload_inline_image(image_file_storage, description: str, folder: str, album: str, default_caption: str) -> str:
    """
    Comprime, envia ao B2 e registra na Galeria uma imagem inserida no corpo de
    um editor rico (Quill) — usado tanto por artigos quanto por ministérios, cada
    um com sua própria pasta/álbum pra não misturar na Galeria.
    """
    key = save_image_upload(image_file_storage, folder=folder)
    caption = (description or "").strip() or default_caption
    track_image(key, caption=caption, album=album)
    return get_b2_file_url(key)
