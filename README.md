# Skill `refactor-arch`: Refatoração Arquitetural Automatizada

Entrega do desafio de **Skills** do MBA. O objetivo é criar uma skill do Claude Code que analisa, audita e refatora projetos legados para o padrão MVC, de forma agnóstica de tecnologia.

> Enunciado original: [devfullcycle/mba-ia-refactor-projects-skill](https://github.com/devfullcycle/mba-ia-refactor-projects-skill)

**Ferramenta:** Claude Code · **Projetos-alvo:** 2× Python/Flask + 1× Node.js/Express

---

## A) Análise Manual

### Metodologia

Cada projeto foi analisado em três passos:

1. **Leitura estrutural:** o que cada arquivo faz e onde as responsabilidades se misturam.
2. **Prova em execução:** os problemas de segurança foram reproduzidos com a aplicação rodando localmente (`curl`), para confirmar que são exploráveis de fato e não apenas teóricos.
3. **Conferência por busca (grep):** cada problema foi localizado por um *sinal de detecção* (ex.: "string SQL concatenada com `+`"), para garantir arquivo e linha exatos.

O passo 3 mostrou que a leitura visual **subestima** o problema: no Projeto 1, a primeira leitura apontou ~10 queries vulneráveis a SQL Injection, e a busca encontrou **19**. Também revelou **falsos positivos**: o sinal "query dentro de `for`" apontou linhas fora de loop. Essas duas lições orientaram o design da skill (buscar primeiro e confirmar lendo antes de reportar).

Severidades conforme a escala do desafio: **CRITICAL** (segurança/quebra total de separação) · **HIGH** (violação forte de MVC/SOLID) · **MEDIUM** (duplicação, performance, validação) · **LOW** (legibilidade, magic numbers).

### Projeto 1: `code-smells-project` (Python/Flask, API de E-commerce)

**Estrutura atual:** 4 arquivos (~780 linhas). Os nomes sugerem MVC (`models.py`, `controllers.py`), mas as responsabilidades estão misturadas: `app.py` executa SQL, `controllers.py` acessa o banco direto e `models.py` concentra o SQL de 4 domínios e ainda regra de negócio.

| # | Sev. | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **SQL Injection:** queries montadas por concatenação de strings (19 ocorrências) | `models.py:28, 48, 58, 68, 92, 110, 127, 140, 149, 155, 158, 164, 174, 188, 192, 220, 224, 280, 291-297` | **Comprovado:** login como admin sem senha usando o e-mail `admin@loja.com' --`. O `--` comenta a verificação de senha. |
| 2 | CRITICAL | **Credencial hardcoded e vazada:** `SECRET_KEY` escrita no código e devolvida pelo `/health` | `app.py:7`, `controllers.py:289` | **Comprovado:** `GET /health` retorna a chave. Com ela é possível forjar sessões assinadas do Flask. |
| 3 | CRITICAL | **Senhas em texto puro e expostas na API** | `database.py:76-78`, `models.py:83, 99` | **Comprovado:** `GET /usuarios` lista as senhas de todos os usuários. Não há nenhum uso de hash no projeto. |
| 4 | CRITICAL | **Endpoints administrativos sem autenticação:** `/admin/query` executa SQL arbitrário e `/admin/reset-db` apaga o banco | `app.py:47-57, 59-78` | **Comprovado:** qualquer pessoa lê a tabela de usuários ou destrói todos os dados com um `POST`. |
| 5 | HIGH | **Regra de negócio fora da camada correta:** faixas de desconto dentro do acesso a dados; notificações (e-mail/SMS/push) simuladas com `print` no controller | `models.py:256-262`, `controllers.py:208-210, 248, 250` | Viola a separação de responsabilidades: a regra não pode ser testada nem alterada sem mexer em SQL ou em HTTP. |
| 6 | HIGH | **Estado global mutável:** uma conexão SQLite global compartilhada por todas as requisições, com `check_same_thread=False` | `database.py:4, 8, 10` | Acoplamento sem injeção de dependência. A flag apenas silencia a proteção de concorrência do SQLite. |
| 7 | MEDIUM | **Queries N+1:** uma query por pedido e mais uma por item | `models.py:187-199, 219-231` (listagens), `139-166` (`criar_pedido`) | 100 pedidos com 3 itens geram 401 queries, onde um `JOIN` resolveria com 1. |
| 8 | MEDIUM | **Duplicação:** validação de produto copiada entre criar/atualizar; montagem de pedido copiada; 16 blocos `except Exception` idênticos devolvendo `str(e)` | `controllers.py:30-34` vs `74-78`; `models.py:171-201` vs `203-233` | Toda correção precisa ser feita em vários lugares. `str(e)` vaza detalhes internos ao cliente. Falta error handler centralizado. |
| 9 | LOW | **Magic numbers e listas soltas:** limiares/percentuais de desconto, categorias e status válidos escritos inline | `models.py:257-262`, `controllers.py:52, 242` | Valores de negócio sem nome e sem ponto único de alteração. |
| 10 | LOW | **`print` no lugar de logging e debug fixo:** 19 `print` e `debug=True` sem controle por ambiente | `controllers.py` (14×), `app.py` (5×); `app.py:8, 88` | Sem níveis de log. Com `host="0.0.0.0"`, o console interativo do Werkzeug (que executa código Python) fica exposto na rede, protegido apenas por PIN. |

**Resumo:** CRITICAL 4 · HIGH 2 · MEDIUM 2 · LOW 2 (**10 problemas**)

### Projeto 2: `ecommerce-api-legacy` (Node.js/Express, LMS com checkout)

**Estrutura atual:** 3 arquivos (~180 linhas). `app.js` delega tudo a uma única classe, `AppManager`, que concentra conexão, schema, seed, rotas, regra de checkout, "gateway" de pagamento e relatório. `utils.js` mistura configuração com segredos, cache global e "criptografia". Não há separação de camadas. Diferente do Projeto 1, **não há SQL Injection**: todas as queries usam placeholders `?`.

| # | Sev. | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded:** senha do banco e chave **live** do gateway de pagamento no código | `utils.js:2-5` | Qualquer pessoa com acesso ao repositório obtém credenciais de produção. |
| 2 | CRITICAL | **"Hash" de senha caseiro e quebrado:** `badCrypto` repete os 2 primeiros caracteres do base64 da senha; senha ausente vira `"123456"` | `utils.js:17-23`, `AppManager.js:68` | **Comprovado:** `senhaforte`, `se` e `sol` geram o mesmo hash `c2c2c2c2c2`. O resultado depende só dos ~12 primeiros bits da senha, e o base64 é reversível. |
| 3 | CRITICAL | **Dados sensíveis em log:** número completo do cartão e chave do gateway impressos no console | `AppManager.js:45` | **Comprovado:** o log mostra `Processando cartão 4111222233334444 na chave pk_live_...`. Viola PCI-DSS, e os logs costumam ir para ferramentas de terceiros. |
| 4 | CRITICAL | **God Class:** `AppManager` acumula conexão, DDL, seed, rotas HTTP, regra de negócio e integração de pagamento | `AppManager.js:4-139` | Separação de responsabilidades inexistente: nada pode ser testado ou substituído isoladamente. |
| 5 | HIGH | **Callback hell sem transação:** checkout com 6 níveis de callbacks aninhados; matrícula, pagamento e auditoria gravados sem `BEGIN/COMMIT` | `AppManager.js:37-77` | Se o insert do pagamento falhar, a matrícula já foi gravada: aluno matriculado sem pagar. Fluxo difícil de ler e de tratar erros. |
| 6 | HIGH | **Rotas sensíveis sem autenticação e exclusão sem integridade:** relatório financeiro aberto; `DELETE /users/:id` não trata matrículas e pagamentos | `AppManager.js:80, 131-137` | **Comprovado:** após o `DELETE`, o relatório passa a mostrar `"student":"Unknown"` com pagamento de 997. Dados órfãos e faturamento exposto publicamente. |
| 7 | HIGH | **Estado global mutável:** `globalCache` e `totalRevenue` em escopo de módulo e exportados | `utils.js:9-10, 25` | Estado compartilhado entre requisições, sem dono nem limite (vazamento de memória). `totalRevenue` é exportado como primitivo e nunca é atualizado (código morto). |
| 8 | MEDIUM | **Queries N+1** no relatório: por curso, uma query de matrículas; por matrícula, mais uma de usuário e uma de pagamento | `AppManager.js:89-127` | Crescimento O(cursos × matrículas) de queries, onde um único `JOIN` com `GROUP BY` resolveria. |
| 9 | MEDIUM | **Erros ignorados e sem tratamento centralizado:** `err` recebido e nunca checado; respostas de erro em texto puro espalhadas | `AppManager.js:57, 92, 104, 106, 133` | Se a query da linha 92 falhar, `enrollments` é `undefined` e `.length` derruba o processo. O `DELETE` responde sucesso mesmo em erro. |
| 10 | MEDIUM | **Validação de entrada ausente:** senha opcional, e-mail e cartão sem validação de formato | `AppManager.js:35, 68` | Usuários criados com senha padrão; dados inválidos chegam ao banco. |
| 11 | LOW | **Nomes crípticos:** variáveis `u, e, p, cid, cc` e campos abreviados no contrato (`usr`, `eml`, `pwd`) | `AppManager.js:29-33` | Leitura exige decifrar cada variável. |
| 12 | LOW | **Magic values / regra fake:** aprovação por `cc.startsWith("4")`, loop de `10000` iterações sem efeito, `self = this` misturado com arrow functions | `AppManager.js:26, 46`, `utils.js:19` | Regras sem nome nem explicação; o loop só consome CPU (gera sempre a mesma string). |

**Resumo:** CRITICAL 4 · HIGH 3 · MEDIUM 3 · LOW 2 (**12 problemas**)

### Projeto 3: `task-manager-api` (Python/Flask, Task Manager)

**Estrutura atual:** ~1.100 linhas divididas em `models/`, `routes/`, `services/` e `utils/`, com SQLAlchemy. A separação existe **só nas pastas**: os blueprints em `routes/` concentram validação, regra de negócio, acesso a dados e montagem da resposta (75 acessos a `db.session`/`Model.query` e 57 validações inline). Enquanto isso, `services/` e quase todo `utils/` **nunca são chamados**. A camada de controller não existe.

| # | Sev. | Problema | Local | Por que é relevante |
|---|---|---|---|---|
| 1 | CRITICAL | **Credenciais hardcoded:** `SECRET_KEY` e usuário/senha SMTP no código | `app.py:13`, `services/notification_service.py:9-10` | Segredos versionados no repositório. A senha SMTP dá acesso à conta de e-mail. |
| 2 | CRITICAL | **Senha com MD5 e hash exposto na API:** `to_dict()` inclui `password`, usado em login, listagem e criação | `models/user.py:21, 29, 32` | **Comprovado:** o login devolve `81dc9bdb52d04dc20036dbd8313ed055`, que é o `md5('1234')` disponível em qualquer rainbow table. MD5 sem salt é inadequado para senhas. |
| 3 | CRITICAL | **Ausência de autenticação e escalada de privilégio:** nenhuma rota protegida; `role` aceito do body; token "JWT" é uma string previsível | `routes/user_routes.py:52, 71, 120-122, 210` | **Comprovado:** um `POST /users` anônimo com `"role":"admin"` cria um administrador (201). O token `fake-jwt-token-1` é forjável trocando o número. |
| 4 | HIGH | **Rotas gordas, sem camada de controller/serviço:** validação, regra de negócio (atraso, estatísticas, produtividade) e queries dentro dos blueprints; CRUD de categorias dentro do blueprint de **relatórios** | `routes/task_routes.py` (24 acessos a dados / 24 validações), `routes/user_routes.py` (20/25), `routes/report_routes.py` (31/8, categorias em `157-223`) | As pastas sugerem camadas, mas a responsabilidade está toda na rota. Regras não podem ser testadas sem HTTP, e o blueprint de relatórios mistura dois domínios. |
| 5 | MEDIUM | **Queries N+1 e contagens repetidas:** `Model.query` dentro de loops e uma query `count()` por status/prioridade | `task_routes.py:41-57`, `report_routes.py:55-56, 161-163`, `user_routes.py:22`; 13× `filter_by(...).count()` em `report_routes.py:19-28`, `task_routes.py:276-279` | **Medido:** `GET /tasks` executa 17 queries para 10 tasks; `GET /reports/summary`, 20 queries. `joinedload` e `GROUP BY` resolveriam em 1-3. |
| 6 | MEDIUM | **Regra de negócio duplicada:** o cálculo de "atrasada" está copiado 6 vezes, embora `Task.is_overdue()` exista e nunca seja chamado; as listas de status/roles válidos aparecem 8 vezes | `task_routes.py:31, 72, 285`, `report_routes.py:35, 133`, `user_routes.py:172`; listas em `task_routes.py:110, 177`, `user_routes.py:71, 120`, `models/task.py:39`, `utils/helpers.py:75, 110-111` | Mudar a regra exige alterar 6 lugares; um esquecido gera respostas inconsistentes entre endpoints. |
| 7 | MEDIUM | **APIs deprecated:** `Model.query.get()` (legado no SQLAlchemy 2.0 → `db.session.get()`) e `datetime.utcnow()` (deprecated no Python 3.12+ → `datetime.now(timezone.utc)`) | 16× `.query.get(` em `routes/`; 22× `utcnow` (ex.: `models/task.py:15-16, 52`, `task_routes.py:31`) | **Comprovado:** a execução emite `LegacyAPIWarning` e `DeprecationWarning`. `utcnow()` está agendado para remoção e vai quebrar numa versão futura do Python. |
| 8 | MEDIUM | **Validação frágil e tratamento de erro ausente:** tipos não checados, 13 `except:` sem tipo e nenhum error handler central | `task_routes.py:113, 261`; `except:` em `task_routes.py:62, 137, 204, 236`, `user_routes.py:130, 149`, `report_routes.py:186, 207, 221`, `helpers.py:46, 49, 88` | **Comprovado:** `priority="5"` (string) e `?priority=abc` derrubam a requisição com **500**. O `except:` sem tipo engole até `KeyboardInterrupt` e esconde a causa. |
| 9 | LOW | **Código morto:** `NotificationService`, 11 funções/constantes de `utils/helpers.py` e `Task.validate_status/validate_priority` nunca são chamados | `services/notification_service.py:4`, `utils/helpers.py:9-116`, `models/task.py:38-48` | Dá a falsa impressão de que existe camada de serviço e validação centralizada. A lógica "morta" já diverge da usada (ex.: `parse_date` aceita `dd/mm/aaaa`, as rotas não). |
| 10 | LOW | **Imports não usados:** 19 imports sem uso (`os`, `sys`, `json`, `time`, `math`, `hashlib`...) | `app.py:7`, `routes/task_routes.py:7`, `routes/user_routes.py:6`, `routes/report_routes.py:7-8`, `utils/helpers.py:2-7`, `models/task.py:3` | Ruído, e sugere dependências que não existem. |
| 11 | LOW | **Verbosidade e config fixa:** `if cond: return True else: return False`, `type(x) == list`, `print` como log, `debug=True` fixo | `models/user.py:35-38`, `models/task.py:40-60`, `task_routes.py:141`, `app.py:34` | Legibilidade; debug sem controle por ambiente. |

**Resumo:** CRITICAL 3 · HIGH 1 · MEDIUM 4 · LOW 3 (**11 problemas**)

---

## B) Construção da Skill

_A preencher._

## C) Resultados

_A preencher._

## D) Como Executar

_A preencher._
