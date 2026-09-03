import re

with open('backend/app/core/rag.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Change retrieve_context to always append load_all_local_knowledge()
target = '''        if clean_chunks:
            return "\\n\\n".join(clean_chunks)
    except Exception as e:'''

replacement = '''        if clean_chunks:
            # Force appending local knowledge base to ensure latest data is ALWAYS present
            return "\\n\\n".join(clean_chunks) + "\\n\\n[DADOS MAIS RECENTES (SOBRESCREVE O ANTERIOR)]:\\n" + load_all_local_knowledge()
    except Exception as e:'''

content = content.replace(target, replacement)

with open('backend/app/core/rag.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")
