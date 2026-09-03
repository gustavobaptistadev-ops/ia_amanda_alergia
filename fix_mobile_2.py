import re

with open('frontend/src/app/conversas/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

chat_header = '''              <div className="p-3 md:p-4 px-4 md:px-6 border-b border-slate-200 bg-white flex items-center justify-between">
                <div className="flex items-center gap-3">'''

chat_header_fixed = '''              <div className="p-3 md:p-4 px-4 md:px-6 border-b border-slate-200 bg-white flex items-center justify-between gap-2 overflow-x-auto no-scrollbar">
                <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0 pr-2 shrink-0">'''

if chat_header in content:
    content = content.replace(chat_header, chat_header_fixed)
else:
    print("Not found")

with open('frontend/src/app/conversas/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("done")
