import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from compositor import cover, composite, default_preserve_mask, paint_mask


def test_wallpaper_fit_4k():
    wallpaper = Image.new('RGB', (1200, 800), (12, 50, 120))
    result = cover(wallpaper, (3840, 2160))
    assert result.size == (3840, 2160)
    assert result.getpixel((100, 100)) == (12, 50, 120)


def test_mask_preserves_original():
    screenshot = Image.new('RGB', (200, 100), 'red')
    wallpaper = Image.new('RGB', (200, 100), 'blue')
    mask = Image.new('L', screenshot.size, 0)
    paint_mask(mask, 80, 40, 12, True)
    result = composite(wallpaper, screenshot, mask)
    assert result.getpixel((80, 40)) == (255, 0, 0)
    assert result.getpixel((0, 0)) == (0, 0, 255)
    paint_mask(mask, 80, 40, 12, False)
    assert composite(wallpaper, screenshot, mask).getpixel((80, 40)) == (0, 0, 255)


def test_default_mask_dimensions():
    mask = default_preserve_mask((1650, 927))
    assert mask.size == (1650, 927)
    assert mask.getpixel((10, 10)) == 255
    assert mask.getpixel((350, 200)) == 0
    assert mask.getpixel((850, 290)) == 255
    assert mask.getpixel((600, 790)) == 255


def test_blue_region_preserves_player_ui_platform():
    from lobby_regions import live_wallpaper_mask
    mask = live_wallpaper_mask((1650, 927))
    assert mask.getpixel((360, 210)) == 255  # sky backdrop
    assert mask.getpixel((1485, 260)) == 255  # right sky backdrop
    assert mask.getpixel((140, 210)) == 0     # sidebar controls
    assert mask.getpixel((860, 300)) == 0     # character
    assert mask.getpixel((860, 20)) == 0      # top HUD
    assert mask.getpixel((700, 780)) == 0     # platform / floor


def test_chroma_frame_keeps_sky_only():
    from lobby_regions import chroma_frame
    wallpaper = Image.new('RGB', (3840, 2160), (22, 80, 130))
    preview = chroma_frame(wallpaper, (1650, 927))
    assert preview.getpixel((360, 210)) == (22, 80, 130)
    assert preview.getpixel((860, 300)) == (1, 2, 3)
    assert preview.getpixel((140, 210)) == (1, 2, 3)
