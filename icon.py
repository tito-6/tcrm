from pathlib import Path
from PIL import Image, ImageDraw

OUTPUT_DIR = Path("generated/tcrm-app-icons")

APP_ICONS = {
    "tcrm_crm": {
        "foreground": "#FFFFFF",
        "background": "#2563EB",
        "label": "CRM"
    },
    "tcrm_propertio": {
        "foreground": "#FFFFFF",
        "background": "#059669",
        "label": "PROP"
    },
    "tcrm_call_center": {
        "foreground": "#FFFFFF",
        "background": "#7C3AED",
        "label": "CALL"
    },
    "tcrm_ai": {
        "foreground": "#FFFFFF",
        "background": "#DB2777",
        "label": "AI"
    },
}

def generate_icons() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for module_name, config in APP_ICONS.items():
        img = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw rounded rectangle container
        draw.rounded_rectangle(
            [(0, 0), (128, 128)],
            radius=28,
            fill=config["background"]
        )

        # Draw inner icon badge container
        draw.rounded_rectangle(
            [(32, 32), (96, 96)],
            radius=16,
            fill=(255, 255, 255, 40)
        )

        output_path = OUTPUT_DIR / f"{module_name}.png"
        img.save(output_path, "PNG")
        print(f"Generated: {output_path}")

if __name__ == "__main__":
    generate_icons()