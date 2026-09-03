# Checklist do fluxo de agendamento

## Implementacao concluida

- [x] Persistir o estado do agendamento separadamente do historico de mensagens.
- [x] Preservar nome, CPF com zeros iniciais, nascimento, pagamento e queixa apos a poda do historico.
- [x] Identificar quando a consulta e para o proprio contato ou para terceiro.
- [x] Exigir a queixa antes da coleta cadastral.
- [x] Exigir nome, CPF, nascimento e forma de atendimento antes da agenda.
- [x] Consultar dois dias quando o paciente nao pede uma data especifica.
- [x] Consultar novamente quando o paciente pede outro dia.
- [x] Aceitar somente um horario que tenha sido efetivamente oferecido.
- [x] Vincular expressoes como "sexta as 17" ao dia correto da lista apresentada.
- [x] Impedir que horario ambiguo entre dois dias seja confirmado automaticamente.
- [x] Impedir regressao para queixa, nome, CPF ou nascimento depois de confirmados.
- [x] Exigir uma correcao explicita antes de substituir CPF ou nascimento confirmados.
- [x] Impedir reabertura do cadastro depois da confirmacao do agendamento.
- [x] Tornar a criacao do agendamento idempotente para o mesmo contato, data e horario.
- [x] Remover CPF, nascimento e telefone da descricao enviada ao Google Calendar.
- [x] Restringir o cache compartilhado a perguntas publicas e impessoais.
- [x] Invalidar o namespace antigo do cache para nao reutilizar respostas legadas.
- [x] Remover emojis das mensagens e instrucoes de producao do backend.
- [x] Cobrir o fluxo e suas regressoes com testes automatizados.

## Validacao automatizada

- [x] Suite completa: 47 testes aprovados.
- [x] Compilacao de todos os modulos Python aprovada.
- [x] Importacao do grafo e contrato do estado aprovados no ambiente virtual.
- [x] Varredura das mensagens do backend sem os emojis conhecidos.
- [x] Verificacao de espacos e conflitos de patch com `git diff --check`.

## Validacao apos deploy na Railway

- [ ] Confirmar que o deploy terminou sem erro de inicializacao ou migracao.
- [ ] Iniciar uma conversa nova pelo painel antes do teste.
- [ ] Executar o roteiro principal abaixo sem apagar mensagens durante o fluxo.
- [ ] Confirmar que apenas dois dias de horarios sao apresentados inicialmente.
- [ ] Confirmar que "sexta as 17" cria somente um agendamento.
- [ ] Confirmar que a resposta seguinte "sim" envia a localizacao sem reabrir o cadastro.
- [ ] Repetir o teste escolhendo um dia diferente dos apresentados.
- [ ] Repetir o teste para uma terceira pessoa.
- [ ] Conferir no painel e no banco que nao houve agendamento duplicado.
- [ ] Conferir no Google Calendar que a descricao nao contem CPF, nascimento ou telefone.

## Roteiro principal de aceite

1. Paciente: `Oi`.
2. Paciente: `Estou com alergia nos bracos`.
3. Paciente: `Gustavo Henrique Baptista`.
4. Paciente: `00511483155`.
5. Paciente: `04/08/1986`.
6. Paciente: `Plano Bradesco`.
7. Paciente: `Sexta as 17`, usando um horario realmente apresentado.
8. Paciente: `Sim`, depois da pergunta sobre localizacao.

Resultado esperado: cada dado e solicitado uma unica vez, o horario e confirmado uma unica vez e a localizacao e enviada sem retornar ao cadastro.

## Monitoramento inicial

- [ ] Observar os logs do primeiro teste sem compartilhar tokens ou URLs assinadas.
- [ ] Verificar a sequencia de estagios: `AWAITING_COMPLAINT`, `AWAITING_PATIENT_NAME`, `AWAITING_CPF`, `AWAITING_BIRTH_DATE`, `AWAITING_PAYMENT`, `READY_FOR_AVAILABILITY`, `AWAITING_SLOT`, `READY_TO_BOOK`, `BOOKED`.
- [ ] Registrar qualquer mensagem que saia da sequencia com horario e identificador mascarado do contato.
- [ ] Manter rollback disponivel para o commit desta implementacao durante a validacao inicial.
