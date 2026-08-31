import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    content = content.replace('"\\""', '"""')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

fix_file('backend/app/api/endpoints/webhook.py')
fix_file('backend/app/services/message_processor.py')
