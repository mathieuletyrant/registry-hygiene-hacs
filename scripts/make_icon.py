"""Draw the integration's icon.

Kept as a script rather than as a checked-in PNG nobody can edit: the icon is
nine rounded squares and two colours, so the drawing *is* the source, and a
tweak is a number here rather than a round trip through a design tool.

Run it with the test venv, which already has Pillow because Home Assistant
does: `.venv/bin/python scripts/make_icon.py`.

The output goes to `icons/`, sized the way home-assistant/brands wants it --
`icon.png` at 256 and `icon@2x.png` at 512, transparent, square. Submitting
them there is what lets the `brands` check come out of the ignore list in
.github/workflows/hacs.yaml.
"""

from pathlib import Path

from PIL import Image, ImageDraw

# Home Assistant's blue for the tidy rows, and the amber of a warning repair
# for the one that is out of place -- the same colour the integration's own
# findings are shown in.
BLUE = (24, 188, 242, 255)
AMBER = (255, 167, 38, 255)

CANVAS = 1024
TILE = 254
GAP = 60
RADIUS = 56
ODD_ONE_OUT = (2, 1)  # column, row
TILT = -13  # degrees; enough to read as misfiled at 32px, not enough to be cute


def _tile(colour: tuple[int, int, int, int]) -> Image.Image:
    image = Image.new("RGBA", (TILE, TILE), (0, 0, 0, 0))
    ImageDraw.Draw(image).rounded_rectangle(
        (0, 0, TILE - 1, TILE - 1), RADIUS, fill=colour
    )
    return image


def draw() -> Image.Image:
    grid = 3 * TILE + 2 * GAP
    origin = (CANVAS - grid) // 2
    icon = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))

    for row in range(3):
        for column in range(3):
            x = origin + column * (TILE + GAP)
            y = origin + row * (TILE + GAP)

            if (column, row) != ODD_ONE_OUT:
                icon.alpha_composite(_tile(BLUE), (x, y))
                continue

            tilted = _tile(AMBER).rotate(
                TILT, expand=True, resample=Image.Resampling.BICUBIC
            )
            overhang = (tilted.width - TILE) // 2
            icon.alpha_composite(tilted, (x - overhang, y - overhang))

    return icon


def main() -> None:
    icon = draw()
    out = Path(__file__).resolve().parents[1] / "icons"
    out.mkdir(exist_ok=True)

    for name, size in (("icon.png", 256), ("icon@2x.png", 512)):
        icon.resize((size, size), Image.Resampling.LANCZOS).save(out / name)
        print(f"wrote {out / name} ({size}x{size})")


if __name__ == "__main__":
    main()
