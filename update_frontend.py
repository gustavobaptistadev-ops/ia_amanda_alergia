import os
import re

files_to_update = [
    'frontend/src/app/configuracoes/page.tsx',
    'frontend/src/app/conhecimento/page.tsx',
    'frontend/src/app/conversas/page.tsx',
    'frontend/src/app/kanban/page.tsx',
    'frontend/src/app/page.tsx'
]

import_statement = "import { fetchWithAuth } from '../../lib/api';\n"

for file_path in files_to_update:
    if not os.path.exists(file_path):
        print(f"Skipping {file_path}")
        continue
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'fetchWithAuth' not in content:
        # Add import at the top after "use client" if it exists, or at very top
        if '"use client";' in content:
            content = content.replace('"use client";', '"use client";\n' + import_statement, 1)
        elif "'use client';" in content:
            content = content.replace("'use client';", "'use client';\n" + import_statement, 1)
        else:
            content = import_statement + content
            
        # Replace global fetch but avoid renaming things that might accidentally match.
        # It's better to just replace etch( with etchWithAuth( 
        # But wait, what if it's wait fetch(? It will become wait fetchWithAuth(. This is correct.
        # Let's use regex to ensure we only match the function call etch(.
        content = re.sub(r'\bfetch\(', 'fetchWithAuth(', content)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file_path}")
