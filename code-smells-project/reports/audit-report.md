================================
ARCHITECTURE AUDIT REPORT
================================
Project:  code-smells-project
Stack:    Python 3.14.4 + Flask 3.1.1 (Werkzeug 3.1.8, flask-cors 5.0.1) + sqlite3
Files:    4 analyzed | ~780 lines of code
Date:     2026-10-01
Architecture: A) Monolítica: 4 arquivos; `models.py` concentra SQL de 4 domínios e regra de desconto, `app.py` mistura config, rotas e SQL.

## Summary
CRITICAL: 6 | HIGH: 3 | MEDIUM: 3 | LOW: 3

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | SQL Injection (AP-01) | models.py:28, 48, 58, 68, 92, 110, 127, 140, 149, 155, 158, 164, 174, 188, 192, 220, 224, 280, 291-297 |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:7, controllers.py:289 |
| F-03 | CRITICAL | Armazenamento inseguro de senha (AP-03) | models.py:110, 127-128; database.py:76-78 |
| F-04 | CRITICAL | Exposição de dados sensíveis (AP-04) | models.py:83, 99; controllers.py:286-289 |
| F-05 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | app.py:47-57, 59-78, 18, 24, 28, 14-16, 26 |
| F-06 | CRITICAL | God File (AP-06) | models.py:1-314, app.py:1-88, controllers.py:1-292, database.py:1-86 |
| F-07 | HIGH | Regra de negócio na camada errada (AP-07) | models.py:139-146, 256-262; controllers.py:208-210, 247-250 |
| F-08 | HIGH | Estado global mutável (AP-08) | database.py:4-11 |
| F-09 | HIGH | Operação multi-etapa sem transação / exclusão física (AP-09) | models.py:148-168, 68; app.py:51-55 |
| F-10 | MEDIUM | Query N+1 / queries repetidas (AP-10) | models.py:187-193, 219-225, 140+155, 239-254; controllers.py:268-274 |
| F-11 | MEDIUM | Código duplicado (AP-11) | models.py:12-21, 31-40, 304-313, 79-86, 95-102, 171-201, 203-233; controllers.py:28-46, 72-90 |
| F-12 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | controllers.py (16× except), app.py:77; controllers.py:119-121, 169-170, 196, 239-240, 43-45, 87-89 |
| F-13 | LOW | Magic numbers e listas de domínio inline (AP-14) | models.py:257-262; controllers.py:47-50, 52, 242 |
| F-14 | LOW | Código morto / imports sem uso (AP-14) | database.py:2; models.py:2; controllers.py:268 |
| F-15 | LOW | Logging inadequado e debug fixo (AP-14) | app.py:8, 56, 83-86, 88; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250 |

## Findings

### F-01 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 48, 58, 68, 92, 110, 127, 140, 149, 155, 158, 164, 174, 188, 192, 220, 224, 280, 291-297
Principle: OWASP A03 Injection
Description: 19 queries montadas por concatenação de strings. As exploráveis diretamente pelo cliente: login (email/senha, l.110), criação/edição de produto (nome, descricao, categoria, l.48, 58), criação de usuário (l.127), busca (`q` e `categoria` da query string, l.291, 293) e criação de pedido (`usuario_id`, `produto_id`, `quantidade` do body, l.140-164). As demais recebem `int` do conversor de rota, mas seguem o mesmo padrão inseguro.
Evidence:
```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```
Impact: `email = "admin@loja.com' --"` faz login como admin sem senha; `GET /produtos/busca?q=' UNION SELECT ...` lê qualquer tabela; payloads de escrita alteram ou apagam dados.
Recommendation: parametrizar todas as queries com `?` (PT-01).
Contract change: NO

### F-02 [CRITICAL] Credenciais hardcoded (AP-02)
File: app.py:7, controllers.py:289
Principle: OWASP A07 / 12-Factor (Config)
Description: `SECRET_KEY` escrita como literal no código, sem leitura de ambiente, e repetida na resposta do `/health` (ver F-04).
Evidence:
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```
Impact: quem lê o repositório (ou chama `/health`) pode forjar qualquer dado assinado com a chave (sessões, tokens).
Recommendation: `config/settings.py` lendo `SECRET_KEY`, `DEBUG`, `DB_PATH`, `HOST`, `PORT` do ambiente; `.env.example` (PT-02).
Contract change: NO

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models.py:110, 127-128; database.py:76-78
Principle: OWASP A02 Cryptographic Failures
Description: senhas gravadas em texto puro no `INSERT` (models.py:127-128) e no seed (database.py:76-78); a verificação é feita por comparação dentro do SQL (models.py:110). Nenhuma biblioteca de hash (`bcrypt`, `werkzeug.security`, `hashlib`...) é usada no projeto.
Evidence:
```python
"INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" +
nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"
```
Impact: qualquer vazamento do banco (ou de `GET /usuarios`, F-04) expõe as senhas reais dos clientes.
Recommendation: `werkzeug.security.generate_password_hash`/`check_password_hash` (já instalado com o Flask); seed com hash; migração no boot que converte senhas em texto puro de bancos existentes (PT-03).
Contract change: NO

### F-04 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83, 99; controllers.py:286-289
Principle: OWASP A01/A09
Description: 2 serializadores de usuário incluem `senha` e chegam ao `jsonify` em `GET /usuarios` e `GET /usuarios/<id>`; o `GET /health` devolve `secret_key`, `debug` e `db_path`.
Evidence:
```python
"db_path": "loja.db",
"debug": True,
"secret_key": "minha-chave-super-secreta-123"
```
Impact: qualquer cliente anônimo obtém as senhas de todos os usuários e a chave da aplicação.
Recommendation: serializador de saída sem `senha` (PT-04); remover `secret_key`, `debug` e `db_path` do health (PT-04/PT-02).
Contract change: YES: campo `senha` deixa de existir nos objetos de `GET /usuarios` e `GET /usuarios/<id>`; `GET /health` deixa de ter as chaves `secret_key`, `debug`, `db_path`.

### F-05 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: app.py:47-57 (`POST /admin/reset-db`), app.py:59-78 (`POST /admin/query`), app.py:18 (`GET /usuarios`), app.py:24 (`GET /pedidos`), app.py:28 (`GET /relatorios/vendas`), app.py:14-16 (`POST/PUT/DELETE /produtos`), app.py:26 (`PUT /pedidos/<id>/status`)
Principle: OWASP A01 Broken Access Control
Description: não existe nenhum mecanismo de autenticação no projeto (grep `auth|jwt|login_required|session|before_request` sem resultados); o `/login` só devolve os dados do usuário, sem token. `/admin/query` executa SQL arbitrário vindo do body; `/admin/reset-db` apaga todas as tabelas; listagem de usuários, de todos os pedidos, relatório financeiro e operações de escrita no catálogo/status são públicas.
Evidence:
```python
query = dados.get("sql", "")
...
cursor.execute(query)
```
Impact: qualquer cliente lê as senhas (`SELECT * FROM usuarios`), apaga o banco ou altera preços e status de pedidos.
Recommendation: remover `/admin/query`; `/login` passa a emitir um token assinado (`itsdangerous`, já dependência do Flask) e `middlewares/auth.py` oferece `require_auth(role=...)`; proteger as rotas listadas (PT-05).
Contract change: YES:
- `POST /admin/query` deixa de existir (404).
- `POST /admin/reset-db` exige token de admin (401 sem token, 403 sem papel admin).
- `GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status` exigem token de admin (401/403).
- `POST /login` passa a incluir `token` dentro de `dados` (chaves de primeiro nível inalteradas).

### F-06 [CRITICAL] God File (AP-06)
File: models.py:1-314, app.py:1-88, controllers.py:1-292, database.py:1-86
Principle: SRP (SOLID) + MVC
Description: nenhum arquivo tem uma única responsabilidade:
- `models.py` (314 linhas, 16 funções): SQL de 4 domínios — produtos (4-70, 285-314), usuários (72-131), pedidos (133-233, 275-283), relatórios (235-273) — mais regra de negócio (estoque/total 139-146, desconto 256-262).
- `app.py`: config (7-9), registro de rotas (11-30), handler inline (32-45), SQL direto em rotas (49-55, 66-76) e entry point (80-88).
- `controllers.py`: HTTP + validação (28-54, 72-90) + notificações (208-210, 247-250) + SQL direto no health (266-274).
- `database.py`: conexão (7-11), DDL (14-53) e seed (56-84).
Evidence:
```python
def relatorio_vendas():          # models.py: SQL + regra de desconto no mesmo corpo
    cursor.execute("SELECT SUM(total) FROM pedidos")
    if faturamento > 10000: desconto = faturamento * 0.1
```
Impact: qualquer mudança toca vários domínios ao mesmo tempo; impossível testar regra de negócio sem banco.
Recommendation: decomposição completa em camadas MVC por domínio (PT-06).
Contract change: NO

### F-07 [HIGH] Regra de negócio na camada errada (AP-07)
File: models.py:139-146, 256-262; controllers.py:208-210, 247-250
Principle: SRP (SOLID) + MVC
Description: 4 pontos: (1) faixas de desconto do relatório dentro da função de acesso a dados (models.py:256-262); (2) verificação de estoque e cálculo do total misturados com as queries (models.py:139-146); (3) notificações de e-mail/SMS/push no meio do handler HTTP (controllers.py:208-210); (4) notificações de status no handler (controllers.py:247-250). Observação: a mensagem "Devolver estoque" (l.250) indica uma regra de negócio não implementada — o cancelamento não devolve o estoque. O comportamento atual será **preservado** (não faz parte do contrato aprovado); fica registrado.
Evidence:
```python
print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) + " criado para usuario " + str(usuario_id))
print("ENVIANDO SMS: Seu pedido foi recebido!")
```
Impact: regra de desconto e notificações não são reutilizáveis nem testáveis fora do HTTP/SQL.
Recommendation: regra de desconto e de estoque nos models de domínio; notificações em `services/notificacao_service.py`, chamadas pelo controller (PT-07).
Contract change: NO

### F-08 [HIGH] Estado global mutável (AP-08)
File: database.py:4-11
Principle: DIP (SOLID)
Description: uma única conexão SQLite global, criada sob demanda com `global` e compartilhada entre threads (`check_same_thread=False`). O servidor de desenvolvimento do Flask é multi-thread: requisições concorrentes usam o mesmo cursor/transação.
Evidence:
```python
global db_connection
if db_connection is None:
    db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Impact: o `commit()` de uma requisição grava escritas pendentes de outra; erros em uma requisição contaminam as seguintes.
Recommendation: conexão por requisição em `flask.g` com `teardown_appcontext`, caminho do banco vindo da config (PT-08).
Contract change: NO

### F-09 [HIGH] Operação multi-etapa sem transação / exclusão física (AP-09)
File: models.py:148-168, 68; app.py:51-55
Principle: Integridade (ACID)
Description: 3 pontos:
- `criar_pedido` (models.py:148-168) grava `pedidos`, N `itens_pedido` e N `UPDATE produtos` sem `rollback`; com a conexão global (F-08), uma exceção no meio deixa as escritas pendentes, que são confirmadas pelo próximo `commit()` de qualquer requisição. A checagem de estoque (l.144) e o débito (l.164) também não são atômicos.
- `deletar_produto` (models.py:68) faz `DELETE FROM produtos` físico: os `itens_pedido` históricos ficam órfãos e passam a aparecer como `"Desconhecido"` (models.py:196, 228).
- `/admin/reset-db` (app.py:51-55) apaga as 4 tabelas (rota administrativa; tratada em F-05).
Evidence:
```python
cursor.execute("DELETE FROM produtos WHERE id = " + str(id))
```
Impact: pedidos sem itens ou estoque debitado sem pedido; perda do nome do produto no histórico de vendas.
Recommendation: helper `transaction()` com `BEGIN`/`COMMIT`/`ROLLBACK` no `criar_pedido`; **soft delete** de produtos (PT-09).
Contract change: NO (o `DELETE /produtos/<id>` mantém status e corpo; o produto some das leituras de negócio como hoje, mas o histórico dos pedidos mantém o nome).

### F-10 [MEDIUM] Query N+1 / queries repetidas (AP-10)
File: models.py:187-193, 219-225, 140+155, 239-254; controllers.py:268-274
Principle: Performance
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem 1 query por pedido (l.188, 220) e mais 1 por item (l.192, 224), dentro dos loops: 1 + P + I queries. `criar_pedido` busca o mesmo produto 2 vezes por item (l.140 e 155). `relatorio_vendas` faz 5 queries separadas (l.239-254) que cabem em 1 agregação; o health faz 4 (l.268-274).
Evidence:
```python
for row in rows:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Impact: o tempo de `GET /pedidos` cresce linearmente com pedidos × itens.
Recommendation: um `JOIN` itens_pedido × produtos para os pedidos selecionados; relatório com `COUNT/SUM/CASE` em uma query (PT-10).
Contract change: NO

### F-11 [MEDIUM] Código duplicado (AP-11)
File: models.py:12-21, 31-40, 304-313 (produto); 79-86, 95-102 (usuário); 171-201 ≡ 203-233 (pedido + itens); controllers.py:28-46 ≈ 72-90 (validação de produto)
Principle: DRY
Description: 7 blocos duplicados: serialização de produto (3×), de usuário (2×), montagem de pedido com itens (2 funções idênticas exceto o `WHERE`) e validação de produto (2×). A validação diverge: o `PUT /produtos/<id>` não valida tamanho do nome (l.47-50) nem a categoria (l.52-54), então aceita categorias que o `POST` rejeita.
Evidence:
```python
if "nome" not in dados:
    return jsonify({"erro": "Nome é obrigatório"}), 400   # controllers.py:30 e 74
```
Impact: regra de negócio inconsistente entre criação e edição; correções precisam ser feitas em vários lugares.
Recommendation: um serializador por entidade e um validador de produto compartilhado (PT-11). Para não alterar o contrato, o `PUT` mantém exatamente as regras atuais (a unificação da regra de categoria fica como sugestão, não aplicada).
Contract change: NO

### F-12 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292; app.py:77-78; controllers.py:119-121, 169-170, 196, 239-240, 43-45, 87-89
Principle: Robustez / Fail-fast
Description: 17 `except Exception` que devolvem `str(e)` ao cliente; nenhum `@app.errorhandler`. Entradas inválidas viram 500 em vez de 400: body ausente no `/login` e no `PUT /pedidos/<id>/status` (`None.get`, l.170, 240); `preco_min=abc` (`float`, l.119); `preco: "abc"` (comparação `str < int`, l.43, 87); item sem `produto_id` (`KeyError`, models.py:140). `quantidade` ≤ 0 não é validada (quantidade negativa **aumenta** o estoque). `PUT /pedidos/<id>/status` devolve 200 para pedido inexistente.
Evidence:
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
Impact: detalhes internos vazam ao cliente; erro do cliente aparece como falha do servidor; manipulação de estoque via quantidade negativa.
Recommendation: `middlewares/error_handler.py` com `AppError` + handlers 404/405/500 genéricos; validação na borda devolvendo 400 (PT-12).
Contract change: YES: entradas inválidas que hoje dão 500 passam a dar 400 (mesma chave `erro`); `quantidade` ≤ 0 passa a dar 400; `PUT /pedidos/<id>/status` de pedido inexistente passa de 200 para 404; erros 500 deixam de expor a mensagem interna.

### F-13 [LOW] Magic numbers e listas de domínio inline (AP-14)
File: models.py:257-262; controllers.py:47-50, 52, 242
Principle: Clean Code
Description: 6 limiares/percentuais de desconto (10000/0.1, 5000/0.05, 1000/0.02), limites de nome (2, 200), lista de categorias e lista de status inline.
Evidence:
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
```
Impact: regra de negócio escondida; alterar uma faixa exige caçar literais.
Recommendation: constantes nomeadas em `utils/constants.py` (PT-14).
Contract change: NO

### F-14 [LOW] Código morto / imports sem uso (AP-14)
File: database.py:2; models.py:2; controllers.py:268
Principle: Clean Code
Description: 3 ocorrências: `import os` e `import sqlite3` nunca usados; `cursor.execute("SELECT 1")` cujo resultado é descartado.
Evidence:
```python
import os        # database.py:2, sem uso
```
Impact: ruído na leitura.
Recommendation: remover (PT-14).
Contract change: NO

### F-15 [LOW] Logging inadequado e debug fixo (AP-14)
File: app.py:8, 56, 83-86, 88; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Principle: Clean Code
Description: 19 `print` usados como log (5 em app.py, 14 em controllers.py), incluindo e-mail do usuário em login (PII). `DEBUG = True` fixo (app.py:8, 88) — com `host="0.0.0.0"`, o debugger do Werkzeug fica exposto na rede.
Evidence:
```python
app.run(host="0.0.0.0", port=5000, debug=True)
```
Impact: sem nível/controle de log; console de debug acessível remotamente.
Recommendation: módulo `logging`; `DEBUG` via ambiente com default `False` (PT-14, PT-02).
Contract change: NO

## Deprecated APIs
Nenhuma API deprecated identificada estaticamente para as versões em uso (Python 3.14.4, Flask 3.1.1, Werkzeug 3.1.8). A prova dinâmica (`python -W default app.py`) será feita no baseline da Fase 3.

## Positive Points
- O cadastro de usuário não aceita `tipo` vindo do body (sempre `cliente`): não há escalada de privilégio por payload.
- Rotas usam conversor `<int:id>`, o que limita a injeção nas rotas por id.
- Validações de produto já retornam 400 com mensagens claras no `POST /produtos`; serão preservadas.
- O seed usa `executemany` com placeholders (database.py:70-83).

## Refactoring Plan (Phase 3 preview)
Strategy: A) decomposição completa — projeto monolítico em 4 arquivos (Fase 1).
Target structure (§4 Python/Flask, pacotes na raiz para manter `python app.py`):
```
app.py                       # create_app() + app = create_app() + __main__
config/settings.py           # Settings lidas do ambiente (SECRET_KEY, DEBUG, DB_PATH, HOST, PORT, TOKEN_MAX_AGE)
database.py                  # conexão por requisição (flask.g), schema, migrações, seed, transaction()
models/produto_model.py      # SQL de produtos + soft delete
models/usuario_model.py      # SQL de usuários + hash de senha
models/pedido_model.py       # SQL de pedidos/itens (JOIN) + regra de estoque/total
models/relatorio_model.py    # agregação + regra de desconto
controllers/produto_controller.py, usuario_controller.py (inclui login), pedido_controller.py,
controllers/relatorio_controller.py, health_controller.py, admin_controller.py
views/produto_routes.py, usuario_routes.py, pedido_routes.py, relatorio_routes.py,
views/health_routes.py (/ e /health), admin_routes.py, views/__init__.py (register_blueprints)
services/notificacao_service.py   # e-mail/SMS/push simulados (via logging)
middlewares/error_handler.py      # AppError + register_error_handlers
middlewares/auth.py               # token assinado (itsdangerous) + require_auth(role)
utils/constants.py                # categorias, status, limites, faixas de desconto
.env.example
```
`controllers.py` e `models.py` da raiz são removidos (substituídos pelos pacotes). Views (Blueprints) e controllers ficam em camadas separadas. Sem desvios da §4.

Soft delete (PT-09):
- Tabela `produtos`: colunas novas `removido INTEGER NOT NULL DEFAULT 0` e `removido_em TIMESTAMP`. A coluna existente `ativo` não é reaproveitada, porque já faz parte da resposta e não tem semântica de exclusão.
- Migração: no boot, `PRAGMA table_info(produtos)` e `ALTER TABLE produtos ADD COLUMN ...` se ausentes (bancos `loja.db` existentes continuam funcionando).
- `DELETE /produtos/<id>` vira `UPDATE produtos SET removido = 1, removido_em = CURRENT_TIMESTAMP`. Leituras de negócio (`GET /produtos`, `/produtos/busca`, `/produtos/<id>`, validação de `criar_pedido`, contagem do health) filtram `removido = 0`. Histórico de pedidos e relatório continuam lendo o produto (nome preservado). Sem cascata: `itens_pedido` não é tocado.
- Migração de senhas: no boot, senhas que não estão no formato hash do Werkzeug são convertidas.

Contract changes requiring approval:
- F-04: `senha` removida das respostas de `GET /usuarios` e `GET /usuarios/<id>`; `secret_key`, `debug`, `db_path` removidos de `GET /health`.
- F-05 (ajustado pelo usuário na aprovação): `POST /admin/query` removida (404); `POST /admin/reset-db`, `DELETE /produtos/<id>` e `GET /relatorios/vendas` passam a exigir `Authorization: Bearer <token>` de admin (401 sem token, 403 sem papel admin); `POST /login` inclui `token` em `dados`. As demais rotas continuam públicas.
- F-12: entradas inválidas que hoje dão 500 passam a 400; `quantidade` ≤ 0 → 400; `PUT /pedidos/<id>/status` inexistente → 404; mensagens de erro 500 genéricas.
Out of scope: autenticação das demais rotas listadas em F-05 (`GET /usuarios`, `GET /pedidos`, `POST`/`PUT /produtos`, `PUT /pedidos/<id>/status`), restringida pelo usuário na aprovação, fica como recomendação; devolução de estoque no cancelamento (F-07, regra ausente hoje; mudaria comportamento) e unificação das regras de validação entre `POST` e `PUT /produtos` (F-11; mudaria quais payloads são aceitos). Ambos ficam como recomendação.

================================
Total: 15 findings
================================
