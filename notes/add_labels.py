import re

path = "/Users/krissankaran/Desktop/teaching/data_visualization_notes/notes/03-small_multiples.qmd"

labels = [
    None,  # setup chunk already has label
    "gapminder-prep",
    "gapminder-ridges",
    "raw-points",
    "ridge-points",
    "degree-panels",
    "area-nonmulti",
    "athlete-panels",
    "athlete-consistent",
    "panel-annotations",
    "facet-columns",
    "facet-rows",
    "facet-both",
    "facet-wrap",
    "facet-reorder",
    "ridge-plot",
    "ridgeline-manual",
    "patchwork-basic",
    "patchwork-layout",
    "vg-setup",
    "vg-scatter",
    "vg-bar",
    "vg-concat",
]

with open(path, "r") as f:
    lines = f.readlines()

# Find chunk start lines
chunk_starts = []
for i, line in enumerate(lines):
    if re.match(r"^```\{(r|ojs)\}\s*$", line):
        chunk_starts.append(i)

assert len(chunk_starts) == len(labels), f"chunk count {len(chunk_starts)} vs labels {len(labels)}"

# Insert labels where missing
inserts = []
label_idx = 0
for start_idx in chunk_starts:
    lbl = labels[label_idx]
    label_idx += 1
    if lbl is None:
        continue
    # Check if next non-empty line already has a label
    j = start_idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j < len(lines) and re.match(r"^#\|\s*label:", lines[j]):
        continue  # already labeled
    inserts.append((start_idx + 1, f"#| label: {lbl}\n"))

# Apply inserts in reverse order to preserve indices
for idx, label_line in reversed(inserts):
    lines.insert(idx, label_line)

with open(path, "w") as f:
    f.writelines(lines)

print(f"Inserted {len(inserts)} labels")
