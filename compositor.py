"""Image compositing for CD Background Studio (offline, no game interaction)."""
from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}


def load_image(path: str | Path) -> Image.Image:
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError('Choose a PNG, JPG, WEBP, or BMP image.')
    with Image.open(path) as image:
        image.load()
        return ImageOps.exif_transpose(image).convert('RGB')


def cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Fill the output area while maintaining aspect ratio (crop as needed)."""
    return ImageOps.fit(image.convert('RGB'), size, Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def default_preserve_mask(size: tuple[int, int]) -> Image.Image:
    """Approximate screenshot mask. White = preserve original screenshot pixels."""
    w, h = size
    mask = Image.new('L', size, 0)
    d = ImageDraw.Draw(mask)
    def rect(a: float, b: float, c: float, e: float):
        d.rectangle((int(a*w), int(b*h), int(c*w), int(e*h)), fill=255)

    rect(0, 0, 1, .088)
    rect(0, 0, .162, .58)
    rect(.865, 0, 1, .26)
    rect(0, .585, 1, 1)
    rect(.442, .157, .704, .90)
    return mask


def composite(wallpaper: Image.Image, screenshot: Image.Image | None,
              preserve_mask: Image.Image | None) -> Image.Image:
    """Blend the original screenshot's masked pixels over the wallpaper."""
    if screenshot is None:
        return wallpaper.convert('RGB').copy()
    foreground = screenshot.convert('RGB')
    background = cover(wallpaper, foreground.size)
    if preserve_mask is None:
        return background
    if preserve_mask.size != foreground.size:
        raise ValueError('Mask must match screenshot size')
    return Image.composite(foreground, background, preserve_mask.convert('L'))


def paint_mask(mask: Image.Image, x: int, y: int, radius: int,
               preserve: bool, last: tuple[int, int] | None = None) -> None:
    """Continuous brush: white preserves screenshot; black reveals wallpaper."""
    color = 255 if preserve else 0
    d = ImageDraw.Draw(mask)
    r = max(1, int(radius))
    if last:
        d.line([last, (int(x), int(y))], fill=color, width=2*r)
    d.ellipse((x-r, y-r, x+r, y+r), fill=color)
