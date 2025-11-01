import re

# Read the file
with open("fortress_director/orchestrator/orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

# Find all _update_motifs_from_choice method definitions
pattern = r"def _update_motifs_from_choice\(.*?\)(?:\n.*?)*?(?=\n\s*def|\n\s*$)"
methods = re.findall(pattern, content, re.DOTALL | re.MULTILINE)

print(f"Found {len(methods)} _update_motifs_from_choice methods")

# Keep only the first one (which should be the correct one with proper logging)
if len(methods) > 1:
    # Remove all but the first method
    for method in methods[1:]:
        content = content.replace(method, "", 1)

    # Write back
    with open(
        "fortress_director/orchestrator/orchestrator.py", "w", encoding="utf-8"
    ) as f:
        f.write(content)

    print("Removed duplicate methods")
else:
    print("No duplicates found")
