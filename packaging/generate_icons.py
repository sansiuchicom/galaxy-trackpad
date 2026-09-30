"""Generate Galaxy Trackpad brand icons (PNG / ICO / Android mipmaps)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "branding"
WIN_ASSETS = ROOT / "windows" / "assets"
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res"

BG = (23, 27, 34, 255)  # #171B22
FG = (124, 240, 194, 255)  # #7CF0C2
FG_DIM = (124, 240, 194, 70)


def make_mark(px: int) -> Image.Image:
    im = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    margin = max(1, px // 10)
    d.rounded_rectangle(
        [margin, margin, px - margin - 1, px - margin - 1],
        radius=max(2, px // 5),
        fill=BG,
    )
    pad_m = int(px * 0.28)
    d.rounded_rectangle(
        [pad_m, pad_m, px - pad_m - 1, px - pad_m - 1],
        radius=max(2, px // 12),
        fill=FG_DIM,
        outline=FG,
        width=max(1, px // 32),
    )
    cx = cy = px // 2
    arm = int(px * 0.18)
    thick = max(2, px // 18)
    d.rectangle([cx - thick // 2, cy - arm, cx + thick // 2, cy + arm], fill=FG)
    d.rectangle([cx - arm, cy - thick // 2, cx + arm, cy + thick // 2], fill=FG)
    return im


def main() -> None:
    OUT.mkdir(exist_ok=True)
    WIN_ASSETS.mkdir(exist_ok=True)

    base = make_mark(1024)
    png_path = OUT / "galaxy_trackpad_icon.png"
    base.save(png_path)

    ico_sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    ico_imgs = [base.resize(s, Image.Resampling.LANCZOS) for s in ico_sizes]
    ico_path = OUT / "galaxy_trackpad.ico"
    ico_imgs[0].save(
        ico_path,
        format="ICO",
        sizes=[(i.width, i.height) for i in ico_imgs],
        append_images=ico_imgs[1:],
    )

    base.resize((256, 256), Image.Resampling.LANCZOS).save(WIN_ASSETS / "icon.png")
    ico_imgs[0].save(
        WIN_ASSETS / "icon.ico",
        format="ICO",
        sizes=[(i.width, i.height) for i in ico_imgs],
        append_images=ico_imgs[1:],
    )

    densities = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, px in densities.items():
        folder_path = ANDROID_RES / folder
        folder_path.mkdir(parents=True, exist_ok=True)
        make_mark(px).save(folder_path / "ic_launcher.png")

    print(f"Wrote {png_path}")
    print(f"Wrote {ico_path}")
    print(f"Wrote {WIN_ASSETS / 'icon.ico'}")
    print("Android mipmaps updated")


if __name__ == "__main__":
    main()
