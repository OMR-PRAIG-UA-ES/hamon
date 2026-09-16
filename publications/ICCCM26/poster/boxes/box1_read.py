"""1 · Read any encoding"""
from hamonpy.cli import convert_file
from hamonpy.serialize import sequence_to_dict, sequence_to_hamon_text

for name in ("harte.lab", "humdrum.krn", "dcml.tsv"):
    seq = convert_file(f"in/{name}")
    open(f"out/{name}.hamon", "w").write(sequence_to_hamon_text(seq))   # see out/* files below
    groups = sequence_to_dict(seq)["groups"]
    for label in (groups[0]["primary"][0], groups[-1]["primary"][0]):    # first and last chord
        typed = {k: v for k, v in label["semantic"].items() if k != "kind"}
        print(f"{name:12} {label['surface']:8} {typed}")               # see console output below
