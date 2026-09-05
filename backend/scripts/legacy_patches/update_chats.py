import re

with open('backend/app/api/endpoints/chats.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''        # Transiǜo transparente: Atendente assumiu a conversa, pausa o bot temporariamente
        contact.bot_active = False
        await db.commit()
        await manager.broadcast("update")'''

replacement = '''        # Transição transparente: Atendente assumiu a conversa, pausa o bot temporariamente
        contact.bot_active = False
        await db.commit()
        await manager.broadcast("update")
        
        # INJEÇÃO NA MEMÓRIA DO LANGGRAPH
        try:
            from app.core.orchestrator import app_graph, init_checkpointer
            from langchain_core.messages import AIMessage
            if app_graph is None:
                await init_checkpointer()
            # Injeta a mensagem humana como se fosse a IA falando (para manter a ilusão contextual)
            config = {"configurable": {"thread_id": phone_number}}
            msg_to_inject = AIMessage(content=f"*(Mensagem enviada por humano)*: {clean_text}")
            await app_graph.aupdate_state(config, {"messages": [msg_to_inject]})
        except Exception as e:
            import logging
            logging.warning(f"Não foi possível atualizar a memória do LangGraph para {phone_number}: {e}")'''

# Regex to match target with any encoding issues for 'Transiǜo'
import re
# We can just match contact.bot_active = False...
target_regex = r"contact\.bot_active = False\s*await db\.commit\(\)\s*await manager\.broadcast\(\"update\"\)"
import copy
new_content = re.sub(target_regex, replacement, content)

with open('backend/app/api/endpoints/chats.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("done")
