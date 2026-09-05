import os

path = "d:\\GUSTAVO\\NOVOS PROJETOS\\ia_amanda\\sistema_recepção_inteligente\\backend\\app\\services\\message_processor.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    if 'event_type = data.get("event")' in line and 'if event_type != "messages.upsert"' in lines[i+2]:
        new_lines.append('    event_type = data.get("event", "")\n')
        new_lines.append('    if not event_type:\n')
        new_lines.append('        return\n')
        new_lines.append('    event_type_upper = event_type.upper()\n')
        new_lines.append('    if event_type_upper not in ["MESSAGES.UPSERT", "MESSAGES_UPSERT", "MESSAGE"]:\n')
        new_lines.append('        return\n')
    elif 'if event_type != "messages.upsert"' in line or 'if event_type == "messages.upsert"' in line:
        if '==' in line:
            new_lines.append('        if event_type_upper in ["MESSAGES.UPSERT", "MESSAGES_UPSERT"]:\n')
    else:
        new_lines.append(line)

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("done")
