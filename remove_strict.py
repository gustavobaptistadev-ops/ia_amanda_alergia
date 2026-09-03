import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the strict onboarding logic
strict_logic = r'                # \[STRICT ONBOARDING\] Se faltar.*?ANTES de prosseguir\\.\\n"'

content = re.sub(strict_logic, '', content, flags=re.DOTALL)

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")
