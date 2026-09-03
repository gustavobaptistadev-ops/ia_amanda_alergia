# Checklist de Segurança

Use este checklist para acompanhar a execução de [SECURITY_EXECUTION_PLAN.md](SECURITY_EXECUTION_PLAN.md). Marque cada item somente após anexar evidência no ticket, pipeline ou relatório de operação.

## Estado rápido

- [x] Defaults previsíveis removidos de autenticação e criptografia no código.
- [x] JWT obrigatório para endpoints de usuário; bypass de desenvolvimento removido.
- [x] WebSocket exige JWT em `access_token`.
- [x] Frontend deixou de publicar `NEXT_PUBLIC_INTERNAL_API_KEY`.
- [x] Guardrail de saída não libera resposta quando o validador está indisponível.
- [ ] Credenciais reais revogadas e rotacionadas no ambiente.
- [ ] Secret manager configurado e auditado.
- [ ] Webhook migrado para HMAC com proteção contra replay.
- [ ] RAG migrado para ingestão versionada e troca atômica.
- [ ] Pentest, DAST, restauração de backup e aprovação de go-live concluídos.

## Fase 0 - Contenção e inventário

- [ ] Inventariar todas as chaves de API, banco, Redis, Evolution, OpenAI e Google.
- [ ] Revogar todas as chaves que possam ter sido usadas fora de um secret manager.
- [ ] Gerar novos valores aleatórios, únicos por ambiente e com no mínimo 32 caracteres.
- [ ] Auditar histórico Git, imagens Docker, CI/CD, logs, backups e observabilidade.
- [ ] Confirmar que `backend/.env` não é publicado e nenhum segredo está no frontend.
- [ ] Restringir painel administrativo por VPN, allowlist ou rede privada.
- [ ] Confirmar exposição pública do WebSocket e webhook.
- [ ] Abrir registro formal para o risco de credenciais expostas e definir proprietário.

## Fase 1 - Identidade e acesso

- [x] Aplicação falha no startup quando segredos mínimos não estão configurados.
- [x] Segredos de API, JWT, webhook e criptografia estão separados no código.
- [x] Usuário sem JWT recebe `401` em endpoints autenticados.
- [x] Conexão WebSocket sem token é rejeitada.
- [ ] Definir matriz de funções: admin, médico e recepcionista.
- [ ] Aplicar autorização por função em operações destrutivas e administrativas.
- [x] Reset global exige usuário autenticado com função `admin`.
- [ ] Validar tenant/clínica no acesso a contatos, mensagens, agenda e logs.
- [ ] Reduzir validade do JWT e adicionar `iss`, `aud`, `iat` e revogação.
- [ ] Implementar HMAC no webhook com timestamp, nonce e anti-replay.
- [ ] Testar rotação de cada segredo sem downtime indevido.

## Fase 2 - Dados, criptografia e LGPD

- [x] Criptografia não usa fallback de `INTERNAL_API_KEY`.
- [ ] Gerar `ENCRYPTION_KEY` Fernet no secret manager.
- [ ] Definir migração e rotação da chave dos dados existentes.
- [ ] Criar inventário de dados, finalidade, base legal, retenção e compartilhamentos.
- [ ] Verificar logs, traces, métricas e alertas sem PII ou dados clínicos.
- [ ] Definir retenção e eliminação de mensagens, checkpoints, logs e backups.
- [ ] Testar restauração e descarte seguro de backups.

## Fase 3 - LLM e RAG

- [x] Guardrail usa contingência segura quando o validador falha.
- [ ] Definir resposta neutra para indisponibilidade de validação clínica.
- [ ] Testar jailbreak, Unicode, leetspeak, Base64, prompt injection indireta e exfiltração.
- [ ] Remover interpolação direta de texto não confiável em prompts de classificação.
- [ ] Versionar documentos RAG com checksum e validação de origem.
- [ ] Substituir exclusão destrutiva por índice novo e troca atômica.
- [ ] Definir limites de tokens, custo, timeout e circuit breaker por provedor.

## Fase 4 - Aplicação e infraestrutura

- [ ] Remover `unsafe-inline` da CSP usando nonce/hash.
- [x] Remover `unsafe-eval` e restringir CORS por configuração.
- [ ] Forçar HTTPS, HSTS e cookies seguros quando aplicável.
- [ ] Configurar rate limit por rota, IP, identidade e telefone.
- [ ] Definir fallback local conservador quando Redis estiver indisponível.
- [ ] Configurar limites de payload, concorrência e timeout para dependências.
- [ ] Executar containers sem privilégio, com imagem mínima e filesystem somente leitura.
- [ ] Restringir portas, rede interna e tráfego de saída.
- [ ] Documentar RPO/RTO e testar rollback.

## Fase 5 - Monitoramento e validação

- [ ] Auditar login, autorização, webhook inválido, bloqueios, mudanças administrativas e exportações.
- [ ] Alertar picos de `401/403`, replay, falhas de assinatura, erro de Redis/LLM e orçamento.
- [ ] Criar runbooks de vazamento, indisponibilidade, abuso de webhook e incidente LGPD.
- [ ] Adicionar secret scanning, SAST, análise de dependências e DAST ao CI.
- [ ] Executar pentest focado em API e WebSocket.
- [ ] Realizar exercício de resposta a incidente.
- [ ] Atualizar `SECURITY_POLICY.md` para refletir o comportamento implementado.
- [ ] Obter aprovação técnica e de privacidade para go-live.

## Evidências obrigatórias para go-live

- [ ] Relatório de credenciais revogadas e rotacionadas.
- [ ] Matriz de autorização aprovada.
- [ ] Resultados dos testes automatizados e adversariais.
- [ ] Resultado de SAST, DAST, secret scan e pentest.
- [ ] Evidência de backup restaurado e rollback testado.
- [ ] Runbooks revisados por uma segunda pessoa.
- [ ] Registro de exceções, compensações e datas de revisão.

## Deploy pela Railway

- [ ] Cadastrar na Railway, por ambiente, `INTERNAL_API_KEY`, `WEBHOOK_SECRET`, `JWT_SECRET_KEY` e `ENCRYPTION_KEY`.
- [ ] Cadastrar também as credenciais de banco, Redis, OpenAI, Evolution API e Google no painel de variáveis/secret manager.
- [ ] Não copiar valores do `.env` local para produção sem rotação e registro de proprietário.
- [ ] Confirmar que o serviço Railway usa PostgreSQL/Redis gerenciados e conexões TLS quando disponíveis.
- [ ] Verificar que o comando `start.sh` executa migrações antes de iniciar a API e o worker.
- [ ] Confirmar que a ausência de segredo faz o deploy falhar, sem iniciar em modo inseguro.
- [ ] Configurar domínio HTTPS, CORS permitido e origem do painel no ambiente Railway.
- [ ] Configurar health check, restart policy, logs e alertas de erro de startup.
- [x] `start.sh` bloqueia deploy antes de migrações quando segredo obrigatório está ausente ou fraco.
- [ ] Fazer deploy em ambiente de staging antes da produção.
- [ ] Após o deploy, validar `401` sem token, login, WebSocket autenticado e webhook assinado.
- [ ] Configurar `PUBLIC_API_URL` para o domínio HTTPS público da API e testar o link curto da agenda.
- [ ] Registrar URL, commit implantado, horário, responsável e resultado do smoke test.
- [ ] Somente depois aprovar produção e acompanhar logs por pelo menos 30 minutos.
