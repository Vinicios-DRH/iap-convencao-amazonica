import uuid
from io import BytesIO

from PIL import Image, ImageOps

from src.controllers.b2_utils import upload_to_b2

IMAGE_MAX_DIMENSION = 1600
IMAGE_JPEG_QUALITY = 80


def save_upload(file_storage, folder: str) -> str:
    """Envia um FileStorage pro B2 com um nome único e retorna a key salva."""
    ext = ""
    if file_storage.filename and "." in file_storage.filename:
        ext = "." + file_storage.filename.rsplit(".", 1)[1].lower()

    key_name = f"{uuid.uuid4().hex}{ext}"
    return upload_to_b2(key_name, file_storage, folder=folder)


def save_image_upload(file_storage, folder: str, max_dimension: int = IMAGE_MAX_DIMENSION) -> str:
    """
    Como save_upload, mas pra imagens exibidas no site (capa de artigo, foto de
    autor, galeria): redimensiona pro tamanho máximo de exibição e recomprime
    antes de enviar, pra uma foto de celular não chegar em tamanho/qualidade
    original e deixar a página pesada. Sempre sai como JPEG.

    `max_dimension` é ajustável pra quem precisa de mais resolução que o padrão --
    o banner do carrossel, por exemplo, ocupa a largura inteira da tela (pode passar
    de 1600px em monitores grandes), então usa um teto maior pra não borrar.
    """
    image = Image.open(file_storage)
    image = ImageOps.exif_transpose(image)  # corrige rotação de fotos de celular
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")

    image.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=IMAGE_JPEG_QUALITY, optimize=True)
    buffer.seek(0)

    key_name = f"{uuid.uuid4().hex}.jpg"
    return upload_to_b2(key_name, buffer, folder=folder)
