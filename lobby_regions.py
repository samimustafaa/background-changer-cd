"""Regions for an on-screen *lobby-only* wallpaper overlay.

The wallpaper is clipped to the blue-marked background area of the supplied
1650x927 reference. The foreground player/UI/props remain the actual live game
pixels because those regions of the overlay are transparent.

The preset is approximate and specific to the supplied 16:9 lobby composition.
"""
from __future__ import annotations
from PIL import Image, ImageDraw, ImageChops, ImageFilter, ImageOps


# Vertices traced from the user's blue outline, expressed as fractions.
# The lower line is intentionally above the platform and lower props.
BG_POLYGON = (
    (.047, .087), (.165, .094), (.215, .063), (.998, .067),
    (.998, .472), (.889, .488), (.880, .425), (.851, .426),
    (.836, .394), (.799, .396), (.792, .537), (.752, .563),
    (.723, .585), (.717, .646), (.645, .641), (.609, .636),
    (.547, .622), (.481, .620), (.353, .576), (.245, .575),
    (.133, .571), (.047, .550),
)


def _poly(points, size):
    w, h = size
    return [(round(x * (w - 1)), round(y * (h - 1))) for x, y in points]


def background_area(size: tuple[int, int]) -> Image.Image:
    """White pixels are eligible to receive the live wallpaper overlay."""
    mask = Image.new('L', size, 0)
    d = ImageDraw.Draw(mask)
    d.polygon(_poly(BG_POLYGON, size), fill=255)

    # Sidebar buttons, labels, currency bar, other HUD elements.
    # The curved sky edge from the user annotation passes behind these widgets.
    w, h = size
    r = lambda a,b,c,e: (int(a*w), int(b*h), int(c*w), int(e*h))
    d.rectangle(r(0,0,.049,.58), fill=0)
    d.rectangle(r(.049,.09,.17,.47), fill=0)
    d.rectangle(r(.872,.085,1,.237), fill=0)

    # Foreground world props rising into the outlined area: left cactus,
    # right cactus & chest, and right crate. These holes are approximate.
    d.polygon(_poly(((.041,.401),(.086,.396),(.124,.475),(.117,.594),
                     (.042,.595)), size), fill=0)
    d.polygon(_poly(((.792,.393),(.82,.381),(.854,.431),(.882,.417),
                     (.89,.593),(.77,.638),(.743,.64),(.736,.565)), size),fill=0)
    d.rectangle(r(.883,.474,1,.635),fill=0)
    return mask


def player_protection(size: tuple[int, int]) -> Image.Image:
    """Transparent holes protect the animated player and sword/weapon.

    This is a conservative (approximate) outline; it can leave some original
    background beside the character. A true replacement requires game assets.
    """
    protect = Image.new('L', size, 0)
    d = ImageDraw.Draw(protect)
    w,h=size
    # Backpack handle/pole reaching into sky.
    d.polygon(_poly(((.444,.158),(.453,.155),(.495,.292),(.501,.353),
                     (.479,.361),(.459,.245)),size),fill=255)
    # Helmet, backpack, torso, legs above lower border.
    d.polygon(_poly(((.503,.254),(.516,.241),(.537,.242),(.555,.26),
                     (.559,.314),(.577,.326),(.594,.361),(.588,.403),
                     (.601,.459),(.604,.636),(.464,.636),(.463,.481),
                     (.461,.409),(.474,.355),(.48,.321),(.498,.301)),size), fill=255)
    # Left arm and right hand/weapon outline.
    d.polygon(_poly(((.475,.364),(.514,.372),(.553,.379),(.581,.347),
                     (.653,.281),(.689,.268),(.697,.289),(.687,.327),
                     (.65,.35),(.595,.387),(.581,.46),(.538,.508),
                     (.476,.499),(.463,.454)),size),fill=255)
    # Giant sword crossing the right side of the player.
    d.polygon(_poly(((.554,.432),(.577,.45),(.686,.866),
                     (.657,.917),(.54,.529)),size),fill=255)
    return protect


def live_wallpaper_mask(size: tuple[int, int],
                        extra_protection: Image.Image | None = None) -> Image.Image:
    """Opaque wallpaper area; black remains the real game's visible pixels."""
    allowed = background_area(size)
    protected = player_protection(size)
    if extra_protection is not None:
        other = extra_protection.convert('L').resize(size, Image.Resampling.NEAREST)
        protected = ImageChops.lighter(protected, other)
    return ImageChops.subtract(allowed, protected)


def chroma_frame(wallpaper: Image.Image, size: tuple[int, int],
                 protected: Image.Image | None = None,
                 chroma: tuple[int,int,int] = (1, 2, 3)) -> Image.Image:
    """Keyed RGB frame used by transparent click-through Win32 Tk window."""
    image = ImageOps.fit(wallpaper.convert('RGB'), size, Image.Resampling.LANCZOS)
    result = Image.new('RGB', size, chroma)
    allowed = live_wallpaper_mask(size, protected)
    # Tk's -transparentcolor needs exact key pixels; mask is intentionally binary.
    result.paste(image, (0, 0), allowed.point(lambda x: 255 if x >= 128 else 0))
    return result
