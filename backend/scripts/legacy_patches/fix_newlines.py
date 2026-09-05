import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix literal \n
content = content.replace('\\n', '\n')

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")
