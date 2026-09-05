import re

with open('backend/app/core/orchestrator.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add FRUSTRACAO_HANDOFF routing
if 'FRUSTRACAO_HANDOFF' not in content:
    content = content.replace(
        'if any(k in last_msg for k in ["urg',
        'if any(k in last_msg for k in ["humano", "atendente", "falar com pessoa", "t\\u00e1 dif\\u00edcil", "n\\u00e3o entende", "p\\u00e9ssimo", "horr\\u00edvel", "burra", "burro", "robo"]):\\n        logger.info("Inten\\u00e7\\u00e3o identificada via Heur\\u00edstica: FRUSTRACAO_HANDOFF")\\n        return {"intent": "FRUSTRACAO_HANDOFF"}\\n\\n    if any(k in last_msg for k in ["urg'
    )
    
    # Update route_intent
    content = content.replace(
        'if intent == "URGENCIA":',
        'if intent == "FRUSTRACAO_HANDOFF":\\n        return "handoff_flow"\\n    if intent == "URGENCIA":'
    )

    # Add handoff_flow_node function
    handoff_node = '''
def handoff_flow_node(state: AgentState):
    """Nó de Transbordo Humano."""
    msg = (
        "Compreendo perfeitamente. Estou transferindo o seu atendimento agora mesmo para a nossa equipe humana. "
        "Um de nossos recepcionistas já foi notificado e vai dar continuidade ao seu atendimento por aqui em instantes. [TRANSFERIR_HUMANO]"
    )
    return {"messages": [AIMessage(content=msg)]}
'''
    content = content.replace('def urgency_flow_node(state: AgentState):', handoff_node + '\\ndef urgency_flow_node(state: AgentState):')

    # Add handoff_flow to graph compilation
    content = content.replace(
        'workflow.add_node("urgency_flow", urgency_flow_node)',
        'workflow.add_node("handoff_flow", handoff_flow_node)\\n    workflow.add_node("urgency_flow", urgency_flow_node)'
    )
    
    content = content.replace(
        'workflow.add_edge("urgency_flow", END)',
        'workflow.add_edge("handoff_flow", END)\\n    workflow.add_edge("urgency_flow", END)'
    )

with open('backend/app/core/orchestrator.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("done")
