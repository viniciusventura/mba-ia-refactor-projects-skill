================================
ARCHITECTURE AUDIT REPORT
================================
Project:  code-smells-project
Stack:    Python 3.14.4 (venv) + Flask 3.1.1 (Werkzeug 3.1.8, flask-cors 5.0.1)
Files:    4 analyzed | ~780 lines of code
Date:     2026-09-30
Architecture: A) Monolítica: 4 arquivos na raiz, sem pastas de camada; `models.py` concentra SQL de 4 domínios e regras de negócio, `app.py` mistura config, rotas e SQL.

## Summary
CRITICAL: 6 | HIGH: 3 | MEDIUM: 3 | LOW: 3

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | SQL Injection (AP-01) | models.py:28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 291-299 |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:7, controllers.py:289 |
| F-03 | CRITICAL | Armazenamento inseguro de senha (AP-03) | models.py:110, 126-129; database.py:75-82 |
| F-04 | CRITICAL | Exposição de dados sensíveis (AP-04) | models.py:83, 99; controllers.py:285-289 |
| F-05 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | app.py:47-57, 59-78 |
| F-06 | CRITICAL | God Class / God File (AP-06) | models.py:1-314, app.py:1-88 |
| F-07 | HIGH | Regra de negócio na camada errada (AP-07) | models.py:139-146, 256-262; controllers.py:208-210, 247-250, 266-274; app.py:49-55, 66-76 |
| F-08 | HIGH | Estado global mutável / acoplamento sem DI (AP-08) | database.py:4-10 |
| F-09 | HIGH | Operação multi-etapa sem transação (AP-09) | models.py:133-169, 65-70 |
| F-10 | MEDIUM | Query N+1 / queries repetidas (AP-10) | models.py:187-193, 219-225, 239-254, 140+155; controllers.py:268-274 |
| F-11 | MEDIUM | Código duplicado (AP-11) | models.py:12-21, 31-40, 304-313, 79-86, 95-102, 171-201, 203-233; controllers.py:28-50, 72-90 |
| F-12 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | controllers.py (16× except), app.py:77-78, controllers.py:43-46, 119-121, 169-170, 239-240 |
| F-13 | LOW | Magic numbers / listas de domínio inline (AP-14) | models.py:257-262; controllers.py:52, 242; models.py:247-253 |
| F-14 | LOW | Logging inadequado / debug fixo (AP-14) | app.py:8, 56, 83-88; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250 |
| F-15 | LOW | Código morto / imports sem uso (AP-14) | models.py:2; database.py:2; app.py:7 |

## Findings

### F-01 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 48-49, 58-60, 68, 92, 110, 127-128, 140, 149-150, 155, 158-160, 164-165, 174, 188, 192, 220, 224, 280, 291-299
Principle: OWASP A03 Injection
Description: 19 queries montadas por concatenação de strings. Exploráveis diretamente por HTTP (valores de texto vindos do JSON/query string): 110 (login), 48-49 e 58-60 (produto), 127-128 (usuário), 140, 149-150, 155, 158-160, 164-165 (`produto_id`, `quantidade` e `usuario_id` do body do pedido) e 291-299 (busca `q`/`categoria`). As demais (28, 68, 92, 174, 188, 192, 220, 224, 280) hoje recebem `int` do conversor de rota, valores do próprio banco ou status validado por lista, mas são funções públicas de acesso a dados sem parametrização.
Evidence:
```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
# email = "admin@loja.com' --"  → login como admin sem senha
```
Impact: bypass de login, leitura/alteração/remoção de qualquer tabela via `/login`, `/produtos`, `/produtos/busca`, `/usuarios`, `/pedidos`.
Recommendation: parametrizar todas as queries com `?` (PT-01), inclusive a busca dinâmica (lista de condições + lista de parâmetros).
Contract change: NO

### F-02 [CRITICAL] Credenciais hardcoded (AP-02)
File: app.py:7, controllers.py:289
Principle: OWASP A07 / 12-Factor (Config)
Description: `SECRET_KEY` literal no código, sem leitura de ambiente, e repetido literalmente na resposta do `/health`. (As senhas do seed em database.py:76-78 são dados fictícios, tratados em F-03, não como credencial de config.)
Evidence:
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
...
"secret_key": "minha-chave-super-secreta-123"
```
Impact: qualquer pessoa com acesso ao repositório (ou ao `/health`) conhece a chave de assinatura da aplicação.
Recommendation: ler `SECRET_KEY` (e `DEBUG`, `DB_PATH`, porta) de variáveis de ambiente num módulo de config, com `.env.example` (PT-02); remover o valor da resposta (F-04).
Contract change: NO (a remoção do campo no `/health` está em F-04)

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models.py:110, 126-129; database.py:75-82
Principle: OWASP A02 Cryptographic Failures
Description: senhas gravadas em texto puro (criação de usuário e seed) e comparadas dentro do SQL. Nenhuma lib de hash (`bcrypt`, `argon2`, `werkzeug.security`...) é usada no projeto.
Evidence:
```python
"INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" +
nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"
```
Impact: qualquer vazamento do banco (ou do `/admin/query`, F-05, ou do `GET /usuarios`, F-04) expõe as senhas reais de todos os usuários.
Recommendation: `werkzeug.security.generate_password_hash` na criação e no seed, `check_password_hash` no login (busca por email, verificação em Python) (PT-03).
Contract change: NO (login continua aceitando as mesmas credenciais; o banco é recriado pelo seed)

### F-04 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83, 99; controllers.py:285-289
Principle: OWASP A01/A09
Description: 2 serializadores de usuário incluem `senha` e chegam ao `jsonify` de `GET /usuarios` e `GET /usuarios/<id>`; o `/health` devolve `secret_key`, `debug` e `db_path`.
Evidence:
```python
"senha": row["senha"],                              # models.py:83 e 99
"db_path": "loja.db", "debug": True,
"secret_key": "minha-chave-super-secreta-123"       # controllers.py:287-289
```
Impact: senhas em texto puro de todos os usuários e a chave da aplicação obtidas com um GET anônimo.
Recommendation: serializador de saída de usuário sem `senha` (PT-04); `/health` só com status/contagens/versão.
Contract change: YES: `GET /usuarios` e `GET /usuarios/<id>` deixam de retornar `dados[].senha`/`dados.senha`; `GET /health` deixa de retornar `secret_key`, `debug` e `db_path`.

### F-05 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: app.py:47-57, 59-78
Principle: OWASP A01 Broken Access Control
Description: `POST /admin/reset-db` apaga as 4 tabelas e `POST /admin/query` executa SQL arbitrário vindo do body, ambos anônimos. Não existe nenhum mecanismo de autenticação no projeto (grep `auth|jwt|login_required|session|before_request`: 0 ocorrências); o `/login` não emite token.
Evidence:
```python
query = dados.get("sql", "")
...
cursor.execute(query)
```
Impact: qualquer cliente lê as senhas, altera dados ou destrói o banco com uma requisição.
Recommendation: remover `/admin/query`; `/login` passa a emitir um token assinado (itsdangerous + `SECRET_KEY`) e `/admin/reset-db` exige `Authorization: Bearer <token>` de usuário `tipo=admin` (PT-05).
Contract change: YES: `POST /admin/query` deixa de existir (404); `POST /admin/reset-db` retorna 401 sem token e 403 para não-admin; `POST /login` passa a incluir `dados.token` (campo adicional).

### F-06 [CRITICAL] God Class / God File (AP-06)
File: models.py:1-314, app.py:1-88
Principle: SRP (SOLID) + MVC
Description: `models.py` (314 linhas, 17 funções) concentra acesso a dados de 4 domínios (produtos 4-70 e 285-314, usuários 72-131, pedidos 133-233 e 275-283, relatórios 235-273) mais regra de negócio (estoque/total 139-146, desconto 256-262). `app.py` acumula config (6-9), roteamento (11-45), SQL direto em handler (47-78) e bootstrap (80-88). `database.py` junta conexão (7-12), DDL (14-54) e seed (56-84). `controllers.py` também acessa o banco (266-274). Os nomes de arquivo sugerem MVC, mas as camadas não estão separadas.
Evidence:
```python
app.config["SECRET_KEY"] = ...                                  # app.py:7  config
app.add_url_rule("/produtos", ...)                              # app.py:11 rota
cursor.execute("DELETE FROM itens_pedido")                      # app.py:51 SQL
```
Impact: qualquer mudança toca arquivos com responsabilidades misturadas; impossível testar regra de negócio sem banco e HTTP.
Recommendation: decompor em config, conexão, models/repositórios por domínio, services, controllers (Blueprints) e app factory (PT-06).
Contract change: NO

### F-07 [HIGH] Regra de negócio na camada errada (AP-07)
File: models.py:139-146, 256-262; controllers.py:208-210, 247-250, 266-274; app.py:49-55, 66-76
Principle: SRP (SOLID) + MVC
Description: faixas de desconto do relatório (256-262) e validação de estoque/cálculo de total do pedido (139-146) estão na função de acesso a dados; notificações (e-mail/SMS/push, aprovação/cancelamento) estão no meio dos handlers HTTP; `health_check` e as rotas admin executam SQL no controller/rota.
Evidence:
```python
if faturamento > 10000:
    desconto = faturamento * 0.1          # models.py:257-258, dentro da função de SQL
print("ENVIANDO EMAIL: Pedido " + ...)    # controllers.py:208, dentro do handler
```
Impact: regra de desconto e de estoque não reutilizável nem testável isoladamente; efeitos colaterais acoplados ao HTTP.
Recommendation: mover regras para services (pedido, relatório) e notificações para um serviço próprio; controllers só orquestram (PT-07).
Contract change: NO

### F-08 [HIGH] Estado global mutável / acoplamento sem DI (AP-08)
File: database.py:4-10
Principle: DIP (SOLID)
Description: uma única conexão SQLite global, criada sob demanda com `global` e compartilhada entre todas as threads do servidor com `check_same_thread=False`; caminho do banco fixo (linha 5).
Evidence:
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Impact: requisições concorrentes compartilham cursor/transação (commit de uma requisição grava escritas pendentes de outra); impossível trocar o banco em testes.
Recommendation: conexão por requisição em `flask.g`, fechada em `teardown_appcontext`, com caminho vindo da config (PT-08).
Contract change: NO

### F-09 [HIGH] Operação multi-etapa sem transação (AP-09)
File: models.py:133-169, 65-70
Principle: Integridade (ACID)
Description: `criar_pedido` faz INSERT em `pedidos`, N INSERTs em `itens_pedido` e N UPDATEs de estoque com um único `commit` no fim, sem `rollback` em falha; se um passo falhar, as escritas anteriores ficam pendentes na conexão global (F-08) e são gravadas pelo próximo `commit` de qualquer requisição. A checagem de estoque (144) e o decremento (164) não são atômicos (overselling concorrente). `deletar_produto` apaga o produto e deixa `itens_pedido` apontando para ele.
Evidence:
```python
cursor.execute("INSERT INTO pedidos ...")          # 148
for item in itens:
    cursor.execute("INSERT INTO itens_pedido ...") # 157, falha aqui → pedido órfão fica pendente
db.commit()                                        # 168
```
Impact: pedidos sem itens, estoque inconsistente, itens órfãos.
Recommendation: `with conn:` (commit/rollback automático) envolvendo todo o fluxo; decremento condicional `WHERE estoque >= ?` (PT-09).
Contract change: NO

### F-10 [MEDIUM] Query N+1 / queries repetidas (AP-10)
File: models.py:187-193, 219-225, 239-254, 140+155; controllers.py:268-274
Principle: Performance
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem 1 query de pedidos + 1 por pedido (itens) + 1 por item (nome do produto): 1 + P + I queries. O relatório faz 5 queries sequenciais que cabem em 1 agregação. `criar_pedido` busca o mesmo produto 2× por item (140 e 155). `health_check` faz 4 queries (uma delas `SELECT 1` inútil).
Evidence:
```python
for row in rows:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Impact: número de roundtrips cresce linearmente com pedidos e itens.
Recommendation: uma query com `JOIN` entre itens e produtos agrupada em Python; relatório com `SUM(CASE ...)` numa query (PT-10).
Contract change: NO

### F-11 [MEDIUM] Código duplicado (AP-11)
File: models.py:12-21, 31-40, 304-313, 79-86, 95-102, 171-201, 203-233; controllers.py:28-50, 72-90
Principle: DRY
Description: serialização de produto copiada 3×, de usuário 2×; `get_pedidos_usuario` e `get_todos_pedidos` são 95% idênticas (31 linhas cada); validação de produto duplicada entre criar e atualizar **com divergência de regra**: o update não valida tamanho do nome nem categoria (controllers.py:47-54 não têm par em 72-90).
Evidence:
```python
if "nome" not in dados:
    return jsonify({"erro": "Nome é obrigatório"}), 400     # controllers.py:30 e 74
```
Impact: um produto pode ser atualizado para categoria inválida ou nome de 1 caractere, regras que a criação proíbe.
Recommendation: serializadores únicos por entidade e um validador de produto compartilhado por create/update (PT-11).
Contract change: NO (a divergência corrigida só afeta requisições hoje inválidas pela regra de criação)

### F-12 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292; app.py:77-78; controllers.py:43-46, 119-121, 169-170, 239-240
Principle: Robustez / Fail-fast
Description: 17 `except Exception` genéricos (16 em controllers.py, 1 em app.py) que devolvem `str(e)` ao cliente; não há `@app.errorhandler`. Entradas inválidas viram 500: body ausente em `/login` e `PUT /pedidos/<id>/status` (`dados.get` em `None`), `preco`/`estoque` string (`"10" < 0` → TypeError), `preco_min=abc` (`float` → ValueError), item de pedido sem `produto_id`/`quantidade` (KeyError).
Evidence:
```python
dados = request.get_json()
email = dados.get("email", "")     # body ausente → AttributeError → 500 com mensagem interna
```
Impact: detalhes internos (mensagens do SQLite, nomes de colunas) expostos; erros de cliente reportados como falha do servidor.
Recommendation: handler central de erros + validação na borda retornando 400 (PT-12).
Contract change: YES: erros 500 passam a devolver `{"erro": "Erro interno do servidor"}` (mesma chave, sem detalhe interno); entradas malformadas que hoje dão 500 passam a dar 400.

### F-13 [LOW] Magic numbers / listas de domínio inline (AP-14)
File: models.py:257-262, 247-253; controllers.py:52, 242
Principle: Clean Code
Description: 6 literais de faixa de desconto (10000/0.1, 5000/0.05, 1000/0.02); lista de categorias e lista de status inline nos handlers; strings de status repetidas no relatório.
Evidence:
```python
elif faturamento > 5000:
    desconto = faturamento * 0.05
```
Impact: regra comercial escondida e espalhada.
Recommendation: constantes nomeadas no model/domínio (PT-14).
Contract change: NO

### F-14 [LOW] Logging inadequado / debug fixo (AP-14)
File: app.py:8, 56, 83-88; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Principle: Clean Code
Description: 19 `print` usados como log (5 em app.py, 14 em controllers.py), 3 deles com e-mail do usuário (161, 179, 182); `DEBUG=True` e `app.run(host="0.0.0.0", debug=True)` fixos, o que expõe o debugger do Werkzeug na rede.
Evidence:
```python
app.run(host="0.0.0.0", port=5000, debug=True)
```
Impact: sem nível/controle de log, PII em stdout, debugger habilitado fora do ambiente de desenvolvimento.
Recommendation: `logging` com logger por módulo; `DEBUG` vindo da config com default `False` (PT-14, PT-02).
Contract change: NO

### F-15 [LOW] Código morto / imports sem uso (AP-14)
File: models.py:2; database.py:2; app.py:7
Principle: Clean Code
Description: `import sqlite3` em models.py e `import os` em database.py nunca usados; `SECRET_KEY` configurada mas nunca lida pela aplicação (não há sessão/assinatura).
Evidence:
```python
import sqlite3     # models.py:2, nenhum uso de sqlite3. no arquivo
```
Impact: ruído e falsa impressão de dependência.
Recommendation: remover imports mortos; `SECRET_KEY` passa a ter uso real na assinatura do token (F-05) (PT-14).
Contract change: NO

## Deprecated APIs
Nenhuma API deprecated identificada estaticamente para as versões em uso (Python 3.14.4, Flask 3.1.1, Werkzeug 3.1.8). Busca por `utcnow`, `utcfromtimestamp`, `before_first_request`, `JSONEncoder`, `url_quote`, `query.get`, `imp`, `distutils`: 0 ocorrências. A confirmação por execução (`python -W default`) será feita no baseline da Fase 3.

## Positive Points
- O seed em `database.py:70-82` já usa placeholders `?` com `executemany`.
- `criar_usuario` não aceita `tipo` vindo do body (default `cliente`), evitando escalonamento de privilégio na criação.
- Rotas usam conversor `<int:...>`, o que já barra ids não numéricos com 404.
- Resposta padronizada (`dados`/`sucesso`/`erro`/`mensagem`) consistente entre endpoints.

## Refactoring Plan (Phase 3 preview)
Strategy: A) decomposição completa
Target structure: `app.py` (factory + entry point `python app.py`), `config.py` (ambiente), `database.py` (conexão por requisição, schema, seed), `models/` (acesso a dados por domínio: produto, usuário, pedido), `services/` (regras: pedido, relatório, auth, notificação), `controllers/` (Blueprints por recurso, só HTTP), `utils/` ou `errors.py` (handler central, validação). Mantém nomes em português, Flask e o comando de execução.
Contract changes requiring approval:
- F-04: `GET /usuarios` e `GET /usuarios/<id>` sem o campo `senha`; `GET /health` sem `secret_key`, `debug` e `db_path`.
- F-05: `POST /admin/query` removido (404); `POST /admin/reset-db` exige `Authorization: Bearer <token>` de admin (401 sem token, 403 não-admin); `POST /login` inclui `dados.token`.
- F-12: erros 500 com mensagem genérica (mesma chave `erro`); entradas malformadas passam de 500 para 400.
Out of scope: autenticação nas demais rotas de escrita/listagem (`POST/PUT/DELETE /produtos`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`) e restrição de CORS. Ambas mudariam o contrato para todos os clientes atuais; ficam como recomendação de follow-up.

================================
Total: 15 findings
================================
