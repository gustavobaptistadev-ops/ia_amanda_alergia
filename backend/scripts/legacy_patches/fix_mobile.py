import re

with open('frontend/src/app/conversas/page.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix the top margin to clear the hamburger menu on mobile
content = content.replace(
    '<div className="flex justify-between items-center">',
    '<div className="flex justify-between items-center pt-14 lg:pt-0">'
)

# 3. Fix the bottom bar text flex issue
content = re.sub(
    r'<Bot className="w-4 h-4 text-blue-600" /> Amanda IA está atendendo este paciente\. Clique em <b>"Assumir"</b> para responder manualmente\.',
    r'<Bot className="w-4 h-4 text-blue-600 flex-shrink-0" /> <span>Amanda IA está atendendo este paciente. Clique em <b>"Assumir"</b> para responder manualmente.</span>',
    content
)

# 4. Fix the Chat Header specifically
chat_header = '''<div className="p-3 md:p-4 border-b border-slate-200 flex items-center justify-between bg-white z-10 shadow-sm relative">
                <div className="flex items-center gap-3">'''
chat_header_fixed = '''<div className="p-3 md:p-4 border-b border-slate-200 flex items-center justify-between bg-white z-10 shadow-sm relative">
                <div className="flex items-center gap-2 md:gap-3 flex-1 min-w-0 pr-2">'''
content = content.replace(chat_header, chat_header_fixed)

# 5. Fix the main container height for mobile (h-full min-h-0)
content = content.replace(
    '<div className="h-[calc(100vh-8rem)] flex flex-col space-y-4 animate-in fade-in duration-500">',
    '<div className="flex-1 flex flex-col space-y-4 animate-in fade-in duration-500 min-h-0 h-[calc(100vh-8rem)] lg:h-full">',
)

with open('frontend/src/app/conversas/page.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done')
