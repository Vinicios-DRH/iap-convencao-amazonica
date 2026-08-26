from b2sdk.v2 import InMemoryAccountInfo, B2Api
from b2sdk.v2.exception import FileNotPresent
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

    Toda key aqui é um uuid gerado na hora do upload (ver save_upload/save_image_upload)
    -- nunca é reaproveitada por outro arquivo, então dá pra cachear "pra sempre" sem risco
    de servir conteúdo desatualizado. Sem isso, o navegador rebaixa a mesma imagem do zero
    a cada visita, porque o B2 não manda Cache-Control nenhum por padrão.
    """
    bucket = get_b2()
    full_path = f"{folder}/{filename}" if folder else filename
    fileobj.seek(0)
    bucket.upload_bytes(fileobj.read(), full_path, cache_control="public, max-age=31536000, immutable")
    return full_path


def delete_from_b2(filename):
    """
    Apaga o arquivo de verdade do bucket (ao contrário de só ocultar no banco).
    Se o arquivo já não existir mais (apagado antes, ou key desatualizada), trata
    como sucesso -- o estado final desejado (fora do bucket) já está valendo.
    Qualquer outro erro (rede, autenticação) sobe pra quem chamou decidir o que fazer.
    """
    bucket = get_b2()
    try:
        file_version = bucket.get_file_info_by_name(filename)
    except FileNotPresent:
        return
    file_version.delete()


def get_b2_file_url(filename):
    # Padrão público: https://f000.backblazeb2.com/file/[bucket]/[filename]
    return f"https://f005.backblazeb2.com/file/{B2_BUCKET_NAME}/{filename}"
