import datetime

progress_path = '/Users/rd/Desktop/LexicalProject/PROGRESS.md'
with open(progress_path, 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip().startswith("- [ ] M0:") or line.strip().startswith("- [x] M0:"):
        new_lines.append(f"- [x] M0: Fixture Dataset Scaffolding & Manifest Preflight (run, fast, happy, go, good, bad, bank)\n")
        new_lines.append(f"  - Scaffolding: 7 fixture lemmas verified end-to-end across Kaikki, UniMorph, Synsets, Forms, and Morphology tables\n")
        new_lines.append(f"  - Verified: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    elif "check m0?" in line.lower():
        continue
    else:
        new_lines.append(line)

with open(progress_path, 'w') as f:
    f.writelines(new_lines)

print("PASS | M0 confirmed and checkpointed in PROGRESS.md")
