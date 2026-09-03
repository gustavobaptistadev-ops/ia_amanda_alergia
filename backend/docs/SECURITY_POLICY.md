# Política de Segurança — IA Amanda | Clínica Lifeline One
> Versão 1.0 | Data: 31/08/2026 | Classificação: Confidencial

---

## 1. Visão Geral

Este documento descreve as camadas de segurança, decisões arquiteturais e conformidade LGPD do sistema **IA Amanda**, recepcionista virtual da Clínica Lifeline One. Destina-se a fins de auditoria interna, conformidade com o CFM (Conselho Federal de Medicina) e eventuais certificações futuras (ISO 27001, HIPAA).

---

## 2. Arquitetura de Segurança — 6 Camadas Independentes

### Camada 1 — WAF por Regex com Normalização Anti-Ofuscação (`input_shield.py`)
- **Técnica:** 12+ padrões Regex cobrindo Jailbreak, DAN, roleplay malicioso, injeção de delimitadores, off-topic explícito.
- **Normalização:** O texto é normalizado via NFKD Unicode e mapeamento leetspeak antes da análise, impedindo contorno por substituição de caracteres.
- **Comportamento em falha:** Falha fechada (fail-closed) — bloqueia a mensagem.

### Camada 2 — Detector de Base64 Oculto (`input_shield.py`)
- **Técnica:** Identifica tokens Base64 com 20+ caracteres no texto, os decodifica e relança os Regex sobre o conteúdo decodificado.
- **Propósito:** Bloquear ataques sofisticados onde o payload malicioso é codificado em Base64 para escapar da Camada 1.
- **Comportamento em falha:** Falha fechada.

### Camada 3 — WAF Cognitivo V2 com LLM (`input_shield.py`)
- **Técnica:** Para mensagens com mais de 400 caracteres, um segundo modelo `gpt-4o-mini` atua exclusivamente como classificador SAFE/UNSAFE.
- **Decisão arquitetural — FAIL-OPEN:** Em caso de falha da API OpenAI (timeout, outage), esta camada é ignorada e o fluxo continua.
- **Justificativa do Fail-Open:** As Camadas 1 e 2 já processaram a mensagem com Regex e detecção Base64. Um fail-closed aqui bloquearia mensagens legítimas de pacientes durante qualquer instabilidade da OpenAI, causando impacto direto na experiência clínica. O risco residual foi avaliado como aceitável dado o contexto de saúde.
- **Revisão:** Esta decisão deve ser reavaliada se o sistema processar dados de saúde de nível Tier 1 (internações, prontuários eletrônicos completos).

### Camada 4 — DLP Financeiro (`input_shield.py`)
- **Técnica:** Mascara padrões de cartão de crédito (13-19 dígitos) e senhas explícitas antes de qualquer processamento pela LLM principal.
- **Comportamento em falha:** Falha aberta — mascaramento não impede o fluxo se falhar.

### Camada 5 — Sanitização de Tags XML/Delimitadores (`input_shield.py`)
- **Técnica:** Remove e escapa `<system>`, `[INST]`, `### System:` e outros delimitadores de prompt que o usuário possa injetar manualmente.
- **Envelopamento:** O input sanitizado é encapsulado em `<user_message>...</user_message>` para separação clara no contexto da LLM.

### Camada 6 — Guardrail de Saída (`guardrails.py`)
- **Técnica:** A resposta gerada pela Amanda é avaliada por um segundo LLM antes de ser enviada ao paciente.
- **Critérios de reprovação:** Prescrição médica ilegal, vazamento de dados de terceiros, obediência a comandos de jailbreak.
- **Exceções clínicas explícitas:** Orientação de suspensão de antialérgicos antes de testes é classificada como APROVADA (procedimento padrão de preparo de exame).
- **Comportamento em falha:** Fail-open — em caso de falha do validador, a resposta é permitida (para não bloquear atendimentos).

### Camada Adicional — Rate Limit por Telefone (`limiter.py`)
- **Técnica:** Sliding Window via Redis. Máximo de 20 mensagens por número de telefone por minuto.
- **Propósito:** Proteger contra DDoS semântico — dado que todos os webhooks chegam do mesmo IP (servidor Evolution API), o rate limiting por IP seria ineficaz.
- **Comportamento em falha:** Fail-open — se o Redis estiver indisponível, o limite não é aplicado.

### Camada Adicional — Sanitização de Chunks RAG (`rag.py`)
- **Técnica:** Fragmentos recuperados da base de conhecimento são sanitizados antes de serem injetados no contexto da LLM.
- **Propósito:** Proteger contra Indirect Prompt Injection — ataques onde documentos na base de conhecimento contêm comandos maliciosos.

---

## 3. Triagem de Emergência Médica (`message_processor.py`)

- Palavras-gatilho de emergência (anafilaxia, falta de ar grave, etc.) são verificadas **antes** do processamento da IA.
- Em caso de emergência detectada, a Amanda responde imediatamente orientando o SAMU 192.
- O evento é registrado no `SystemLog` com categoria `triagem_emergencia` e nível `ALERTA`.
- O fluxo de IA é interrompido para a mensagem de emergência — não gera custo de token OpenAI.

---

## 4. Conformidade LGPD

| Princípio LGPD | Implementação |
|---|---|
| **Finalidade** | Dados coletados exclusivamente para abertura de prontuário e agendamento médico |
| **Necessidade** | Apenas Nome, CPF, Telefone e Convênio são coletados |
| **Transparência** | O prompt informa ao paciente a finalidade da coleta |
| **Segurança** | Mensagens armazenadas com `EncryptedText`; logs nunca expõem número completo |
| **Não discriminação** | A IA não toma decisões com base em dados sensíveis além do agendamento |
| **Responsabilização** | Este documento serve como registro de processo |

---

## 5. Dados Nunca Coletados ou Transmitidos

- Senhas de pacientes
- Dados bancários (mascarados pela Camada 4 antes de qualquer processamento)
- Dados de outros pacientes (sem cross-referência entre conversas)
- Prontuários eletrônicos completos
- Dados biométricos

---

## 6. Revisão e Auditoria

Este documento deve ser revisado:
- A cada mudança significativa na arquitetura de segurança
- Anualmente, ou conforme exigido por auditorias do CFM/ANVISA
- Após qualquer incidente de segurança

**Próxima revisão programada:** 31/08/2027
