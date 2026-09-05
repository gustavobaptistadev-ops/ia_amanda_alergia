# Regra de Ouro: Alta Performance, Limpeza e Padrão Sênior

A partir de agora e em todas as sessões futuras, você (Antigravity) deve obrigatoriamente seguir este procedimento para TODO arquivo, pasta ou linha de código que você tocar ou criar:

1. **Zero Poluição Visual e Estrutural**:
   - Nunca deixe código comentado, lixo residual de refatorações ou imports não utilizados (F401).
   - O código deve ser elegante, minimalista e autoexplicativo.

2. **Conformidade Estrita com PEP 8 (Python) e Padrões da Linguagem**:
   - Não use variáveis ambíguas como `l`, `O`, `I` (E741). Renomeie para nomes significativos (ex: `logger_instance`, `log_item`).
   - Mantenha espaçamento, margens e linhas dentro do limite de caracteres exigido (ou use ferramentas de formatação).
   - As importações devem SEMPRE ficar no topo do arquivo (E402).

3. **Verificação de Lints Embutida no Processo**:
   - Sempre que modificar um arquivo de forma substancial, assuma a responsabilidade de executar um verificador (como `flake8`, `mypy`, ou formatação `black` se disponível) para garantir que você não introduziu sujeira.

4. **Arquitetura e Nomenclatura Padrão**:
   - Ao criar novos arquivos, coloque-os na pasta arquitetural correta (ex: `app/services`, `app/core/graph_nodes`).
   - Não acople lógica pesada em locais indevidos (ex: roteadores HTTP ou arquivos de configuração). Extraia para serviços.

5. **Prevenção de Retrabalho**:
   - Antes de dar uma tarefa como concluída, revise silenciosamente o código gerado. Se estiver bagunçado, corrija antes de apresentar ao usuário.

*Nota: Esta regra existe para garantir que o projeto "Sistema de Recepção Inteligente" (ou qualquer outro) se mantenha sempre com qualidade de CTO/Engenharia Sênior.*
