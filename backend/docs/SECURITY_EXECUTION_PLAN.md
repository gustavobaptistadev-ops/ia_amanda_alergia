# Plano de Execução de Segurança

**Sistema:** IA Amanda | Clínica Lifeline One
**Versão:** 1.0  
**Data:** 03/09/2026  
**Objetivo:** elevar o sistema a um nível de segurança adequado para produção, tratando autenticação, segredos, dados pessoais e de saúde, disponibilidade, prompt injection e capacidade de resposta a incidentes.

## 1. Escopo e premissas

Este plano foi baseado na implementação existente e em [SECURITY_POLICY.md](SECURITY_POLICY.md). Os arquivos `scratchpad/README_SECURITY_PACKAGE.md`, `EXECUTIVE_SUMMARY.md`, `SECURITY_AUDIT_REPORT.md` e `IMPLEMENTATION_GUIDE.md` citados em material anterior não estão presentes neste checkout; portanto, as decisões abaixo devem ser confirmadas contra esses documentos caso sejam disponibilizados.

O sistema deve ser tratado como processamento de dados pessoais e potencialmente dados pessoais sensíveis. O plano não presume certificação HIPAA ou ISO 27001; essas referências exigem análise jurídica, contratual e de escopo própria.

## 2. Riscos prioritários identificados

| Prioridade | Risco | Evidência | Impacto |
|---|---|---|---|
| P0 | Segredos padrão no código | `core/security.py`, `core/auth.py` e `core/crypto.py` possuem fallbacks previsíveis | Acesso indevido, falsificação de JWT e perda de confidencialidade |
| P0 | Possível exposição de credenciais já usadas | Chaves padrão e tokens são aceitos por componentes críticos | Comprometimento persistente mesmo após correção do código |
| P1 | Falha aberta em controles de segurança | WAF cognitivo, guardrail de saída e Redis permitem continuidade em erro | Bypass de proteção ou abuso sem limitação |
| P1 | WebSocket sem autenticação/autorização explícita | `get_api_key` retorna sem validar conexões WebSocket | Vazamento de eventos e dados de conversas |
| P1 | Criptografia com fallback e salt estático | `core/crypto.py` deriva a chave de valores de ambiente opcionais | Impossibilidade de rotação segura e risco de descriptografia indevida |
| P1 | CSP permissiva | `main.py` contém `unsafe-inline` e `unsafe-eval` | Aumenta impacto de XSS ou dependência comprometida |
| P1 | Reingestão destrutiva do RAG | `rag.py` exclui a coleção antes de inserir documentos | Indisponibilidade e perda do índice em falha parcial |
| P2 | Divergência entre política e código | A política descreve fail-closed onde a implementação é fail-open | Auditoria incorreta e decisões operacionais inseguras |
| P2 | Cobertura de testes de segurança insuficiente | Não há evidência de suíte cobrindo bypasses dos guardrails | Regressões podem chegar à produção |

## 3. Resultado de segurança esperado

Antes de liberar produção, o sistema deverá:

- Não iniciar em ambiente de produção sem segredos fortes, únicos e fornecidos por secret manager.
- Separar credenciais por finalidade: API interna, JWT, webhook e criptografia.
- Autenticar e autorizar HTTP, WebSocket e webhooks com escopo mínimo.
- Aplicar controles determinísticos mesmo quando Redis ou um provedor LLM estiver indisponível.
- Preservar disponibilidade do RAG com versionamento e troca atômica de índice.
- Registrar eventos de segurança sem CPF, telefone completo, tokens, mensagens ou segredos.
- Possuir testes automatizados, alertas, runbook e evidência de rollback.

## 4. Plano por fases

### Fase 0 - Contenção e inventário (0 a 24 horas)

**Responsável:** líder técnico + responsável pela infraestrutura.  
**Gate:** não iniciar exposição pública adicional até concluir os itens P0.

1. Revogar e substituir imediatamente `INTERNAL_API_KEY`, `WEBHOOK_SECRET`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, chaves OpenAI, Redis e banco, considerando todas como potencialmente expostas.
2. Auditar histórico Git, imagens Docker, CI/CD, logs e variáveis de ambiente em busca de segredos; remover valores reais e invalidar os encontrados.
3. Bloquear fallbacks inseguros em produção: ausência de qualquer segredo obrigatório deve interromper o startup.
4. Restringir temporariamente o acesso administrativo por rede/VPN e limitar origens CORS ao painel oficial.
5. Confirmar se WebSocket e webhook estão expostos à internet; se estiverem, aplicar bloqueio de origem/rede e autenticação antes de reabrir.
6. Criar registro do incidente de credenciais, mesmo que não haja evidência de uso indevido.

**Critérios de aceite:** nenhuma credencial padrão é aceita; todos os segredos críticos têm proprietário, origem, data de rotação e plano de recuperação; não existem segredos válidos no repositório ou artefatos publicados.

### Fase 1 - Identidade, acesso e segredos (dias 1 a 5)

**Responsável:** senior backend + senior infraestrutura.

1. Centralizar configuração em um módulo validado por ambiente, com `production` fail-closed.
2. Remover o bypass implícito de autenticação em `get_current_user`; distinguir claramente usuário autenticado de credencial de serviço.
3. Implementar autorização por função e recurso, incluindo tenant/clinica quando aplicável.
4. Proteger WebSocket com token de curta duração, validação de origem, autorização do canal e limite de conexões por usuário.
5. Usar segredo exclusivo para JWT, algoritmo explicitamente permitido, expiração curta, `iss`, `aud`, `iat`, rotação e revogação quando necessário.
6. Proteger webhook com assinatura HMAC sobre o corpo bruto, timestamp, nonce e proteção contra replay; não depender apenas de token em query string.
7. Migrar segredos para Vault, AWS Secrets Manager, Azure Key Vault ou equivalente; nunca gravá-los em `.env` versionado.

**Critérios de aceite:** matriz de autorização aprovada; testes negativos para cada rota protegida; WebSocket sem token não conecta; webhook com assinatura inválida ou replay é rejeitado; rotação testada sem downtime indevido.

### Fase 2 - Dados, criptografia e LGPD (dias 3 a 10)

**Responsável:** senior backend + DPO/jurídico + infraestrutura.

1. Definir inventário de dados: finalidade, base legal, retenção, origem, consumidores e localização.
2. Corrigir a criptografia para usar chave Fernet gerenciada externamente, sem derivação de fallback; planejar migração e rotação de chaves.
3. Fazer criptografia em trânsito obrigatória e revisar TLS entre API, banco, Redis, Evolution API e serviços LLM.
4. Mascarar dados antes de logs, tracing, métricas, filas, prompts de diagnóstico e alertas; aplicar allowlist de campos auditáveis.
5. Definir retenção e eliminação de mensagens, logs e backups, incluindo restauração e descarte seguro.
6. Revisar compartilhamento com provedores externos, contratos, transferências internacionais e direitos do titular.

**Critérios de aceite:** mapa de dados aprovado; teste de rotação e recuperação de criptografia concluído; busca automatizada não encontra CPF, telefone completo ou token em logs; política de retenção aplicada e testada.

### Fase 3 - Guardrails, LLM e RAG (dias 7 a 15)

**Responsável:** senior backend/ML security.

1. Separar claramente classificação de segurança, prompt do produto e dados recuperados; conteúdo RAG deve ser tratado como não confiável.
2. Substituir interpolação direta da mensagem do usuário no prompt de classificação por mensagens estruturadas e limites de tamanho/custo.
3. Definir política de falha por risco: bloqueio ou resposta segura quando o guardrail de entrada/saída falhar; nunca liberar respostas clínicas não validadas por indisponibilidade silenciosa.
4. Implementar resposta de contingência neutra, sem diagnóstico ou prescrição, quando a validação não estiver disponível.
5. Criar pipeline de ingestão RAG versionado, com checksum, validação de origem, detecção de instruções maliciosas, índice novo e troca atômica; remover `delete_collection()` do caminho de produção.
6. Adicionar testes adversariais para Unicode, leetspeak, Base64, prompt injection indireta, exfiltração, tentativa de prescrição e dados de terceiros.
7. Definir limites de tokens, timeout, orçamento por conversa e circuit breaker por provedor.

**Critérios de aceite:** conjunto de ataques conhecido bloqueado; mensagens legítimas não são bloqueadas acima da meta acordada; indisponibilidade do LLM produz resposta segura; reindexação falha sem apagar o índice ativo.

### Fase 4 - Aplicação, rede e disponibilidade (dias 10 a 20)

**Responsável:** senior infraestrutura + backend.

1. Remover gradualmente `unsafe-inline` e `unsafe-eval` da CSP, usando nonce/hash quando necessário.
2. Fixar CORS por ambiente, validar `Host`, configurar HTTPS, HSTS, cookies seguros e proteção CSRF para fluxos baseados em cookie.
3. Configurar rate limit distribuído por IP, identidade, telefone e rota sensível; em falha do Redis, usar limite local conservador e gerar alerta.
4. Aplicar timeouts, limites de payload, limites de concorrência e circuit breakers para banco, Redis, Evolution API e OpenAI.
5. Executar serviço com usuário não privilegiado, filesystem somente leitura quando possível, imagem mínima e dependências verificadas.
6. Separar rede pública, API, banco, Redis, painel e observabilidade; restringir portas e egress.
7. Formalizar backup criptografado, RPO/RTO, teste de restauração e rollback de deploy.

**Critérios de aceite:** scan de headers sem achados críticos; teste de carga não derruba dependências; restauração de backup validada; acesso de rede documentado e mínimo.

### Fase 5 - Observabilidade, resposta e validação independente (dias 15 a 25)

**Responsável:** security owner + operação + auditor independente.

1. Criar eventos de auditoria para autenticação, falhas de autorização, mudança de configuração, webhook inválido, bloqueios de guardrail, exportação e acesso administrativo.
2. Criar alertas para picos de 401/403, replay, falhas de assinatura, bloqueios anormais, erro de Redis, erro de LLM e uso de orçamento.
3. Produzir runbooks para vazamento de segredo, indisponibilidade, abuso do webhook, incidente de dados e comprometimento de conta.
4. Executar SAST, dependabot/renovação de dependências, secret scanning, DAST e teste de penetração focado em API/WebSocket.
5. Fazer tabletop exercise e registrar evidências, responsáveis, tempos de detecção e recuperação.
6. Atualizar [SECURITY_POLICY.md](SECURITY_POLICY.md) para refletir o comportamento real e estabelecer revisão trimestral e após incidente.

**Critérios de aceite:** todos os achados críticos fechados ou formalmente aceitos pelo responsável de risco; alertas testados; runbooks executáveis por outra pessoa; relatório final arquivado.

## 5. Ordem recomendada de implementação

1. Revogação de credenciais e remoção de defaults.
2. Autenticação/autorização de HTTP, WebSocket e webhook.
3. Criptografia e tratamento de dados sensíveis.
4. Fail-safe dos guardrails, rate limit e circuit breakers.
5. RAG versionado e testes adversariais.
6. CSP, rede, container e hardening operacional.
7. Monitoramento, resposta a incidentes e pentest.

## 6. Testes mínimos obrigatórios

- Testes unitários de normalização, DLP, Base64 e sanitização RAG.
- Testes de integração de autenticação, autorização, webhook e WebSocket.
- Testes de expiração, assinatura, replay e rotação de tokens.
- Testes de falha de Redis, banco, OpenAI e índice vetorial.
- Testes de vazamento em logs e traces.
- Testes de carga para webhook, chat e conexões WebSocket.
- SAST, secret scanning, análise de dependências e DAST no pipeline.
- Teste de restauração de backup e rollback de release.

## 7. Métricas e gates de produção

- 0 segredos padrão ou credenciais reais no repositório, imagens e artefatos.
- 100% das rotas sensíveis com autenticação e autorização testadas.
- 100% dos webhooks validados por assinatura e anti-replay.
- 0 achados críticos abertos no SAST/DAST/pentest no go-live.
- 100% dos logs de produção sem dados sensíveis não mascarados na amostra de validação.
- RTO/RPO aprovados e restauração comprovada.
- MTTD e MTTR definidos, com alerta testado para cada incidente prioritário.

## 8. Pessoas, prazo e orçamento

Para a primeira execução, alocar um senior de segurança/backend e um senior de infraestrutura por 3 a 4 semanas, com apoio parcial de produto, jurídico/DPO e operação. A estimativa de engenharia deve ser refinada após inventário de ambiente; a faixa de US$ 15 mil a US$ 25 mil pode ser usada como envelope inicial, sem considerar custos recorrentes de secret manager, observabilidade, pentest e provedores.

O responsável pelo risco deve aprovar qualquer exceção de fail-open, retenção de dados, exposição pública ou achado crítico não corrigido. Exceções devem ter prazo, justificativa, compensação e data de revisão.

## 9. Decisão de go-live

O sistema só deve ser liberado após concluir as Fases 0 e 1, fechar os gates P0/P1 de identidade e segredos, comprovar os testes de falha e obter aprovação formal do responsável técnico e do responsável por privacidade. As demais fases podem ser entregues incrementalmente, mas nenhuma exceção deve permanecer sem registro de risco e prazo de correção.
