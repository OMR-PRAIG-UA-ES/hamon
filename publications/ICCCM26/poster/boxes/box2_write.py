"""2 · Write any encoding"""
from hamonpy.cli import convert_file
from hamonpy.report import write_to

seq = convert_file("in/progression.hamon")
for fmt, ext in (("humdrum", "krn"), ("mei", "mei"), ("lilypond", "ly"), ("dcml", "tsv")):
    open(f"out/progression.{ext}", "w").write(write_to(seq, fmt, mode="native"))
    print(f"{fmt:10} → out/progression.{ext}")
