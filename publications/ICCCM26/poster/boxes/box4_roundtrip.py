"""4 · What the round-trip lost"""
from hamonpy.cli import convert_file
from hamonpy.report import lossy_report

rep = lossy_report(convert_file("in/progression.hamon"), "mei", mode="native")

for f in rep.semantic:
    if f.path.startswith(("groups", "regions")):      # the music, not the bookkeeping
        print(f"{f.kind:8} {f.path:30} {f.summary}")
