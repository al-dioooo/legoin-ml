"""Labels the team's own phone photos of bricks for stages 2 and 3.

    python -m tools.labeler cut         # stage 1 crops of photos/<session>/*
    python -m tools.labeler label       # a local page where one person labels every crop
    python -m tools.labeler merge A B   # agreement of two labelers, then label.csv

The files live under the data root, notebooks 02 and 03's `data/foto_mandiri`. The README's
"Labeling your own photos" section has the whole procedure.
"""
