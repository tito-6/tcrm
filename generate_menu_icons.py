"""Generate official Font Awesome menu icons (fontawesomefree) for TCRM apps."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import fontawesomefree

ROOT = Path(__file__).resolve().parent
FA_SOLID = Path(fontawesomefree.__file__).parent / (
    "static/fontawesomefree/webfonts/fa-solid-900.ttf"
)

# size kept modest; UI CSS shrinks further in the dropdown
SIZE = 64
ICON_PX = 34

ICONS = {
    # path relative to custom_addons or tcrm-src
    "custom_addons/tcrm_saas_core/static/description/icon.png": ("\uf0e4", "#101E55"),  # tachometer
    "custom_addons/tcrm_ai/static/description/icon.png": ("\uf5dc", "#0F766E"),  # brain
    "custom_addons/tcrm_ai_research/static/description/icon.png": ("\uf002", "#6D28D9"),  # search
    "custom_addons/tcrm_research_hub/static/description/icon.png": ("\uf5da", "#C2410C"),  # book-open
    "custom_addons/tcrm_propertio/static/description/icon.png": ("\uf015", "#B91C1C"),  # home
    "custom_addons/tcrm_web_enhance/static/description/icon.png": ("\uf53f", "#1D4ED8"),  # paint-brush
    # Settings / Apps live under base — overwrite description assets used by menus
    "tcrm-src/tcrm/addons/base/static/description/settings.png": ("\uf013", "#374151"),  # cog
    "tcrm-src/tcrm/addons/base/static/description/modules.png": ("\uf1b2", "#4F46E5"),  # cube
}


def render_icon(glyph: str, bg: str, out: Path) -> None:
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # rounded square background
    margin = 2
    draw.rounded_rectangle(
        [margin, margin, SIZE - margin - 1, SIZE - margin - 1],
        radius=14,
        fill=bg,
    )
    font = ImageFont.truetype(str(FA_SOLID), ICON_PX)
    bbox = draw.textbbox((0, 0), glyph, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (SIZE - tw) / 2 - bbox[0]
    y = (SIZE - th) / 2 - bbox[1]
    draw.text((x, y), glyph, font=font, fill="white")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG")
    print(f"OK {out}")


def main() -> None:
    for rel, (glyph, bg) in ICONS.items():
        render_icon(glyph, bg, ROOT / rel)


if __name__ == "__main__":
    main()
