import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the first definition with a generic variable to merge with the second
content = content.replace('temporal_anchor = f"\\n[RELÓGIO', 'relogio_anchor = f"\\n[RELÓGIO')

# Add relogio_anchor to the final temporal_anchor
content = content.replace('temporal_anchor = (\\n        f"📅 CALENDÁRIO', 'temporal_anchor = (\\n        f"{relogio_anchor}\\n📅 CALENDÁRIO')

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")
