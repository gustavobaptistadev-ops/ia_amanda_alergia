import os
import re

files_to_update = [
    'frontend/src/app/configuracoes/page.tsx',
    'frontend/src/app/conhecimento/page.tsx',
    'frontend/src/app/conversas/page.tsx',
    'frontend/src/app/kanban/page.tsx',
    'frontend/src/app/page.tsx'
]

for file_path in files_to_update:
    if not os.path.exists(file_path):
        continue
    
    # Calculate depth from 'app'
    # src/app/page.tsx -> depth 0 (inside app)
    # src/app/configuracoes/page.tsx -> depth 1
    parts = file_path.split('src/app/')[1].split('/')
    depth = len(parts) - 1
    
    if depth == 0:
        correct_import = "import { fetchWithAuth } from '../lib/api';\n"
    elif depth == 1:
        correct_import = "import { fetchWithAuth } from '../../lib/api';\n"
    elif depth == 2:
        correct_import = "import { fetchWithAuth } from '../../../lib/api';\n"
        
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    content = re.sub(r"import \{ fetchWithAuth \} from '\.\./\.\./lib/api';\n", correct_import, content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print(f"Fixed {file_path}")
