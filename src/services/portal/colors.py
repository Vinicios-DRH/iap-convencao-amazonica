import colorsys

from PIL import Image, ImageOps

_PALETTE_SIZE = 12
_SATURATION_THRESHOLD = 0.35
_FALLBACK_COLOR = "#f29422"  # var(--pt-orange) do portal.css -- usado se a extração falhar


def _hsv(rgb):
    r, g, b = rgb
    return colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)


def _quantize_dominant(pixels: list) -> tuple:
    """Bota os pixels lado a lado numa imagem de 1 linha só (a posição não importa pra
    quantize) e devolve a cor mais comum da paleta reduzida."""
    sample = Image.new("RGB", (len(pixels), 1))
    sample.putdata(pixels)
    palette_image = sample.convert("P", palette=Image.ADAPTIVE, colors=_PALETTE_SIZE)
    palette = palette_image.getpalette()
    _, idx = sorted(palette_image.getcolors(), reverse=True)[0]
    return tuple(palette[idx * 3: idx * 3 + 3])


def extract_accent_color(file_storage) -> str:
    """
    Pega uma cor de destaque da imagem do banner, pra usar no botão "Acesse aqui" --
    cada banner acaba com um botão na cor da própria imagem, em vez de sempre laranja.

    Quantizar a imagem inteira direto (fundo + tudo) não funciona bem quando o fundo é
    grande e neutro (parede, concreto, céu) e só uma parte menor da imagem tem cor viva:
    a quantização "gasta" o orçamento de cores distinguindo tons quase iguais de cinza e
    empurra toda a cor vibrante pra dentro de uma única cor borrada. Por isso, primeiro
    filtra só os pixels saturados (a "cor viva" da imagem) e quantiza só esses -- assim o
    fundo neutro nunca disputa espaço na paleta. Sem pixel vivo o suficiente (imagem
    genuinamente sem cor, tipo preto e branco), cai pra cor mais comum dentro de uma
    faixa de claridade razoável.
    """
    try:
        image = Image.open(file_storage)
        image = ImageOps.exif_transpose(image)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        image.thumbnail((150, 150))
        rgb_image = image.convert("RGB")
        pixels = list(rgb_image.getdata())

        vivid_pixels = [
            p for p in pixels
            if (lambda hsv: hsv[1] >= _SATURATION_THRESHOLD and 0.15 <= hsv[2] <= 0.97)(_hsv(p))
        ]

        if len(vivid_pixels) >= max(50, len(pixels) * 0.01):
            best_color = _quantize_dominant(vivid_pixels)
        else:
            # sem cor viva o suficiente -- pega a cor mais comum da imagem inteira que
            # não seja preto/branco puro (evita botão invisível ou texto branco ilegível)
            palette_image = rgb_image.convert("P", palette=Image.ADAPTIVE, colors=_PALETTE_SIZE)
            palette = palette_image.getpalette()
            color_counts = sorted(palette_image.getcolors(), reverse=True)
            best_color = None
            for _, idx in color_counts:
                candidate = tuple(palette[idx * 3: idx * 3 + 3])
                if 0.15 <= _hsv(candidate)[2] <= 0.97:
                    best_color = candidate
                    break
            if best_color is None:
                _, idx = color_counts[0]
                best_color = tuple(palette[idx * 3: idx * 3 + 3])

        return "#{:02x}{:02x}{:02x}".format(*best_color)
    except Exception:
        return _FALLBACK_COLOR
    finally:
        file_storage.seek(0)  # devolve o cursor pro save_image_upload conseguir ler de novo
