# Checklist de Execução: Anamnese Inteligente (Alergologia)

Este checklist guia a implementação passo a passo da funcionalidade de anamnese curta e humanizada, garantindo que a arquitetura sênior (FSM + LLM) e a segurança clínica sejam rigorosamente mantidas.

## FASE 1: Memória e Máquina de Estados (FSM)
- [ ] Atualizar ooking_state.py: Criar novos campos no dicionário de estado (symptom_duration, current_medication).
- [ ] Modificar ooking_state.py: Atualizar a lógica do estado AWAITING_COMPLAINT para só avançar se a queixa básica e a medicação tiverem sido mapeadas, ou delegar a confirmação estrita à extração semântica.

## FASE 2: Roteamento Semântico e Segurança (Zero-Cost Router)
- [ ] Atualizar patient_data.py: Criar métodos de extração (Regex/Heurística) para identificar menções a antialérgicos, corticoides e tempo de sintoma no texto do paciente.
- [ ] Atualizar conversation_router.py: Adicionar **Red Flags Clínicas** (ex: "garganta fechando", "falta de ar severa", "anafilaxia"). Se detectado, forçar o intent para URGENCIA.
- [ ] Atualizar guardrails.py: Ajustar as permissões médicas. A IA deve ser explicitamente autorizada a *repetir/perguntar* sobre remédios citados pelo paciente para o prontuário, sem que isso seja interpretado como uma *prescrição ilegal* pelo validador.

## FASE 3: Treinamento, Empatia e Prompting (LLM)
- [ ] Atualizar prompt_master.py (Core Persona): Adicionar a diretriz obrigatória de **Escuta Ativa Médica** (validar a dor antes de seguir para a próxima pergunta).
- [ ] Atualizar prompt_master.py (Few-Shot Examples): Inserir 2 novos exemplos de diálogo demonstrando como a IA deve reagir a casos de pele (Urticária) e respiratórios (Rinite/Asma).
- [ ] Atualizar orchestrator.py: Ajustar a geração determinística de mensagens (quando no estado de queixa) para assegurar que a IA sempre faça as perguntas complementares (duração e medicação).

## FASE 4: Testes Automatizados (TDD) e Homologação
- [ ] Adicionar testes em 	est_conversation_router.py garantindo que frases de anafilaxia cortem o fluxo de agendamento e retornem URGENCIA.
- [ ] Adicionar testes em 	est_patient_data.py garantindo a correta extração de medicamentos (ex: "tomei alegra").
- [ ] Adicionar testes em 	est_booking_state.py para validar o armazenamento persistente da anamnese.
- [ ] Executar a suíte completa com pytest e garantir 100% de aprovação.

## FASE 5: Deploy e Monitoramento
- [ ] Verificar a ausência de emojis fixos e prompts vazados com git diff --check.
- [ ] Commit semântico e deploy contínuo (Railway).
- [ ] Validação prática pelo Painel/WhatsApp.
