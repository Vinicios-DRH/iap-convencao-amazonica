from b2sdk.v2 import InMemoryAccountInfo, B2Api
import os

# Pegue os valores do seu ambiente, ou substitua aqui pelos seus valores
B2_KEY_ID = os.environ.get("B2_KEY_ID")
B2_APPLICATION_KEY = os.environ.get("B2_APPLICATION_KEY")
B2_BUCKET_NAME = os.environ.get("B2_BUCKET_NAME")


def get_b2():
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    b2_api.authorize_account("production", B2_KEY_ID, B2_APPLICATION_KEY)
    bucket = b2_api.get_bucket_by_name(B2_BUCKET_NAME)
    return bucket


def upload_to_b2(filename, fileobj, folder=""):
    """
    filename: nome do arquivo final (ex: comprovantes/1234.pdf)
    fileobj: arquivo aberto em modo binário (ex: request.files['file'].stream)
    folder: (opcional) pasta dentro do bucket
    """
    bucket = get_b2()
    full_path = f"{folder}/{filename}" if folder else filename
    fileobj.seek(0)
    bucket.upload_bytes(fileobj.read(), full_path)
    return full_path


def get_b2_file_url(filename):
    # Padrão público: https://f000.backblazeb2.com/file/[bucket]/[filename]
    return f"https://f005.backblazeb2.com/file/{B2_BUCKET_NAME}/{filename}"
