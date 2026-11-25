"""What a crop can be labeled: the API contract's 13 parts and 10 colors, plus `other`.

The part ids are `classes` in release v0.2.0's `legoin_mobilenetv3_part_labels.json`, in its
order, with their LEGO design ids. The color ids are `colors` in its `legoin_warna.json`, with
Rebrickable's RGB as in notebook 03's `KATALOG_WARNA`. An empty part or color means doubtful:
notebooks 02 and 03 skip that crop for that stage.
"""

OTHER = "other"
DOUBTFUL = ""

PARTS = {
    "brick-1x1": "3005",
    "brick-1x2": "3004",
    "brick-1x3": "3622",
    "brick-1x4": "3010",
    "brick-2x2": "3003",
    "brick-2x3": "3002",
    "brick-2x4": "3001",
    "plate-1x2": "3023",
    "plate-2x2": "3022",
    "plate-2x4": "3020",
    "slope-2x2": "3039",
    "tile-1x2": "3069b",
    "round-1x1": "3062b",
}

# id: (Rebrickable RGB, name on the page)
COLORS = {
    "red": ("C91A09", "merah"),
    "blue": ("0055BF", "biru"),
    "yellow": ("F2CD37", "kuning"),
    "green": ("237841", "hijau"),
    "black": ("05131D", "hitam"),
    "white": ("FFFFFF", "putih"),
    "light-gray": ("A0A5A9", "abu-abu muda"),
    "dark-gray": ("6C6E68", "abu-abu tua"),
    "orange": ("FE8A18", "oranye"),
    "brown": ("582A12", "cokelat"),
}

PART_VALUES = {*PARTS, OTHER, DOUBTFUL}
COLOR_VALUES = {*COLORS, OTHER, DOUBTFUL}

# Crops wanted per class, from notebooks 02 (section 10) and 03 (section 8.2).
TARGET = 30
TARGET_OTHER = 50
