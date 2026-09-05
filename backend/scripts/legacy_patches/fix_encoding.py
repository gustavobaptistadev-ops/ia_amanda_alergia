import os
import glob

def fix_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            content = f.read()
        
        text = content.decode('utf-8', errors='replace')
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text)
        print(f"Fixed {filepath}")
    except Exception as e:
        print(f"Error {filepath}: {e}")

files = glob.glob('backend/**/*.py', recursive=True) + glob.glob('frontend/**/*.tsx', recursive=True)
for f in files:
    fix_file(f)
