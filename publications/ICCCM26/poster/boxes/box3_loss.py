"""3 · What each encoding cannot say"""
from hamonpy.capability import native_loss
from hamonpy.cli import convert_text
from hamonpy.report import WRITERS
from hamonpy.serialize import sequence_to_dict

text = open("in/progression.hamon").read()
seq = sequence_to_dict(convert_text(text, "hamon"))

for f in WRITERS:
    print(f"{f:10}", dict(native_loss(seq, text, f)) or "says it all")
