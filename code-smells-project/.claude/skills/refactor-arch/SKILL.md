---
name: refactor-arch
description: >
  Audita e refatora um projeto backend legado para o padrão MVC, de forma
  agnóstica de tecnologia (Python/Flask, Node/Express e outras stacks). Executa
  3 fases sequenciais: (1) análise da stack e da arquitetura, (2) auditoria de
  anti-patterns com relatório por severidade e pausa para confirmação,
  (3) refatoração para MVC com validação de boot e endpoints. Use quando o
  usuário invocar /refactor-arch ou pedir "auditar e refatorar a arquitetura
  deste projeto". NÃO use para revisar um diff/PR (use code review), gerar
  testes ou criar features novas.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash, Edit, Write
---

# refactor-arch

Você é um arquiteto de software fazendo a auditoria e a refatoração de um projeto legado. Trabalhe no **diretório atual** (a raiz do projeto). O conhecimento de domínio está em `references/`; este arquivo define **o fluxo**. Leia cada referência **no momento indicado**, não antes.

| Fase | Referências a ler |
|---|---|
| 1 · Análise | `references/project-analysis.md` |
| 2 · Auditoria | `references/anti-patterns-catalog.md`, `references/audit-report-template.md`, e `references/mvc-guidelines.md` §4 e §6 (para o Refactoring Plan) |
| 3 · Refatoração | `references/mvc-guidelines.md`, `references/refactoring-playbook.md` |

## Regras invioláveis

1. **Nenhum arquivo do projeto é criado, alterado ou removido antes da confirmação da Fase 2.** A única escrita permitida antes disso é o próprio relatório `reports/audit-report.md`, que é a saída da auditoria. Também não execute o app antes da confirmação, porque isso pode criar arquivos como o banco SQLite.
2. **Buscar → ler → reportar.** Todo finding nasce de um sinal do catálogo, é confirmado lendo o código e cita `arquivo:linha` exatos. Sem confirmação, não há finding.
3. **O contrato da API é preservado** (URLs, métodos, status e formato das respostas), exceto pelas mudanças de segurança listadas no relatório e aprovadas pelo usuário.
4. **As convenções do projeto são preservadas:** idioma dos nomes, sistema de módulos, framework de rotas, comandos de execução e scripts auxiliares.
5. **Honestidade:** reporte números reais. Se algo falhar na validação, diga o que falhou. Nunca marque ✓ sem ter verificado.
6. **Não faça commit nem push.** O versionamento é decisão do usuário.
7. **Escopo de busca:** ignore `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `.git/`, lockfiles, `*.db`, `reports/` e `.claude/`.

---

## Fase 1: Análise do projeto

1. Leia `references/project-analysis.md`.
2. Execute os passos 1 a 8 dessa referência usando Glob, Grep e Read (somente leitura).
3. Imprima o bloco `PHASE 1: PROJECT ANALYSIS` no formato da referência, seguido do **inventário de endpoints** (tabela com método, rota, handler e local).
4. Siga direto para a Fase 2, sem pedir confirmação.

---

## Fase 2: Auditoria

1. Leia `references/anti-patterns-catalog.md` e `references/audit-report-template.md`.
2. Para **cada** anti-pattern AP-01 a AP-14:
   1. Rode os sinais de detecção (Grep com as regex sugeridas, adaptadas à linguagem detectada).
   2. Abra os trechos encontrados e aplique o **"Como confirmar"**. Descarte falsos positivos (ex.: query fora do loop, SQL com placeholder, payload de exemplo).
   3. Registre os confirmados com todas as linhas, a contagem e um trecho de evidência.
   4. Para o AP-13, cruze as versões das dependências (Fase 1) com a tabela de APIs deprecated.
3. Aplique as regras de ajuste de severidade do catálogo, agrupe por anti-pattern e ordene CRITICAL → LOW.
4. Monte o **Refactoring Plan**. Antes, leia `references/mvc-guidelines.md` §4 (estrutura alvo da stack detectada) e §6 (estratégia por nível de organização). O plano deve:
   - declarar a estratégia A/B/C conforme a classificação da Fase 1;
   - descrever a estrutura alvo **usando os nomes de pastas da §4** (ex.: Flask → `config/settings.py`, `models/`, `views/` ou `routes/` já existente, `controllers/`, `middlewares/error_handler.py`). Views/rotas e controllers são camadas **separadas**: não proponha Blueprints/Routers dentro de `controllers/`;
   - listar **todas** as mudanças de contrato que a correção exigiria.
   Qualquer desvio da §4 precisa de justificativa explícita no plano.
5. Confira as contagens: Summary, tabela e total precisam bater.
6. Crie a pasta `reports/` se necessário, salve o relatório em `reports/audit-report.md` e imprima o mesmo conteúdo.
7. Imprima exatamente:
   ```
   Phase 2 complete. Report saved to reports/audit-report.md.
   Proceed with refactoring (Phase 3)? [y/n]
   ```
8. **PARE AQUI e encerre sua resposta.** Aguarde a mensagem do usuário.
   - `y`/`sim`/`yes` → Fase 3.
   - `n`/`não`/`no` → encerre informando que nada foi modificado.
   - Resposta com ajustes (ex.: "sim, mas mantenha o /admin/query") → atualize o plano, resuma o plano ajustado em uma frase e siga para a Fase 3.

---

## Fase 3: Refatoração e validação

Leia `references/mvc-guidelines.md` (completo) e `references/refactoring-playbook.md`. A estrutura executada é a do Refactoring Plan aprovado. Não mude de ideia sobre a estrutura sem avisar o usuário.

### 3.0 · Baseline (antes de qualquer alteração)

Registre como a aplicação se comporta **hoje**. Esse é o critério de "não quebrou".

1. **Ambiente:** use o interpretador do projeto, se houver (`.venv/Scripts/python` no Windows, `.venv/bin/python` no Linux/macOS). Se as dependências não estiverem instaladas, instale-as a partir do manifesto (`pip install -r requirements.txt` na venv, `npm install`).
2. **Banco limpo e determinístico:** se o arquivo de banco não é versionado (confira com `git ls-files`), apague-o antes de cada execução. Rode o seed, se o projeto exigir. Repita **exatamente** a mesma preparação na validação final.
3. **Subir o app** em background, com warnings visíveis (`python -W default app.py`, `node --trace-deprecation src/app.js`), redirecionando a saída para um log fora do projeto (diretório temporário). Aguarde a porta responder (polling com timeout, sem `sleep` fixo longo).
4. **Chamar cada endpoint do inventário**, com payloads válidos (tirados de `*.http`, README ou do código) e ao menos um caso de erro por recurso (ex.: id inexistente → 404, login inválido → 401). Registre: método, rota, status e chaves de primeiro nível do JSON (ou o texto, se a resposta for texto). Chame rotas destrutivas por último.
5. **Registre os warnings** de deprecation emitidos pelo código do projeto (evidência do AP-13).
6. **Pare o processo** e confirme que a porta foi liberada. No Windows, se `kill` não bastar, localize o PID pela porta (`netstat -ano`) e encerre com `taskkill //PID <pid> //F`.

### 3.1 · Plano de transformação

1. Escolha a estratégia pela classificação da Fase 1 (`mvc-guidelines.md` §6): **A** decomposição completa, **B** evolução incremental, **C** só correções de código.
2. Monte a tabela **origem → destino**: cada função/rota/classe atual e o arquivo/camada para onde vai.
3. Associe cada finding (F-xx) ao seu padrão do playbook (PT-xx).

### 3.2 · Execução

Aplique as transformações na ordem da regra 4 do playbook: **config → camadas → segurança → integridade/performance → erros → duplicação/deprecated/legibilidade**.

- Depois de **cada bloco**, verifique que o projeto ainda carrega: `python -c "import app"`, ou `node -e "require('./src/app')"` quando o entry point não sobe servidor ao ser importado. Se não carregar, corrija antes de seguir.
- Scripts auxiliares que importam o app (ex.: `seed.py`) precisam continuar funcionando. Atualize-os se o formato dos dados mudou (ex.: hash de senha).
- Remova os arquivos antigos que foram totalmente migrados, para não coexistirem com os pacotes novos.
- Crie `.env.example` com as variáveis introduzidas. Atualize o README do projeto se os comandos de execução ou as variáveis mudaram.

### 3.3 · Validação

Repita o baseline com **a mesma preparação** e compare:

| Verificação | Critério de aprovação |
|---|---|
| Boot | O app sobe sem erro e a porta responde |
| Endpoints | Mesmo status e mesmas chaves de primeiro nível do baseline em **todas** as rotas, exceto as mudanças de contrato aprovadas |
| Mudanças aprovadas | Rota protegida: 401/403 sem credencial e o status original com credencial. Campo sensível removido: ausente |
| Deprecated | Nenhum warning de deprecation vindo do código do projeto |
| Anti-patterns | Rode de novo os sinais dos findings corrigidos: nenhum CRITICAL/HIGH remanescente confirmado |
| Estrutura | Checklist da §7 do `mvc-guidelines.md` atendido |
| Scripts auxiliares | Seed e demais scripts executam sem erro |

Se algo falhar: diagnostique, corrija e valide de novo, **no máximo 5 ciclos**. Se ainda falhar, pare e reporte ao usuário exatamente o que continua falhando, sem declarar sucesso.

Ao final, pare o app e confirme que nenhum processo ficou rodando.

### 3.4 · Resumo final

Salve em `reports/refactor-summary.md` e imprima:

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## Strategy
<A/B/C + uma frase>

## New Project Structure
<árvore de diretórios, anotando a camada de cada pasta>

## Findings Resolved
| ID | Severity | Anti-pattern | Status | How (PT-xx) |
|----|----------|--------------|--------|-------------|
(status: RESOLVED | PARTIAL | NOT FIXED, com motivo)

## Contract Changes Applied
- <mudança aprovada> (ou "Nenhuma")

## Validation
  ✓/✗ Application boots without errors
  ✓/✗ All endpoints respond as baseline (<ok>/<total>)
  ✓/✗ Approved contract changes verified
  ✓/✗ No deprecation warnings from project code
  ✓/✗ No CRITICAL/HIGH anti-patterns remaining
  ✓/✗ MVC structure checklist complete

## Endpoint Comparison
| Método | Rota | Baseline | Depois | OK |
|--------|------|----------|--------|----|

## How to run
<comandos atualizados, variáveis de ambiente>
================================
```
