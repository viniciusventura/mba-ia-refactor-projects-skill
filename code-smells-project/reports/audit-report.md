================================
ARCHITECTURE AUDIT REPORT
================================
Project:  code-smells-project
Stack:    Python 3.14.4 + Flask 3.1.1 (flask-cors 5.0.1, Werkzeug 3.1.8)
Files:    4 analyzed | ~780 lines of code
Date:     2026-10-15
Architecture: A) Monolítica: 4 arquivos na raiz, sem pastas de camada; `controllers.py` e `models.py` atendem 4 domínios cada e `app.py` mistura config, rotas e SQL

## Summary
CRITICAL: 6 | HIGH: 4 | MEDIUM: 3 | LOW: 3

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | SQL Injection (AP-01) | models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-299 |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:7, 8, 88; controllers.py:287-289 |
| F-03 | CRITICAL | Armazenamento inseguro de senha (AP-03) | models.py:109-111, 126-129; database.py:75-83 |
| F-04 | CRITICAL | Exposição de dados sensíveis (AP-04) | models.py:83, 99; controllers.py:285-289 |
| F-05 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | app.py:14, 15, 16, 18, 19, 23, 26, 47-57, 59-78 |
| F-06 | CRITICAL | God File (AP-06) | app.py:1-88; controllers.py:1-292; models.py:1-314 |
| F-07 | HIGH | Leitura de dados de terceiros sem autenticação (AP-05) | app.py:24, 25, 28 |
| F-08 | HIGH | Regra de negócio na camada errada (AP-07) | models.py:256-262; controllers.py:52-54, 208-210, 247-250, 264-274; app.py:47-78 |
| F-09 | HIGH | Estado global mutável / sem DI (AP-08) | database.py:4-11 |
| F-10 | HIGH | Operação multi-etapa sem transação + exclusão física (AP-09) | models.py:133-169, 65-70 |
| F-11 | MEDIUM | Query N+1 / queries repetidas (AP-10) | models.py:187-199, 219-231, 139-141, 154-156, 239-254; controllers.py:268-274 |
| F-12 | MEDIUM | Código duplicado (AP-11) | controllers.py:28-50, 72-90; models.py:12-21, 31-40, 304-313, 79-86, 95-102, 171-201, 203-233 |
| F-13 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | controllers.py (16 `except`), app.py:77-78; controllers.py:118-121, 169-170, 239-245 |
| F-14 | LOW | Magic numbers / listas de domínio inline (AP-14) | models.py:247-262; controllers.py:52, 242; app.py:36; controllers.py:285-286 |
| F-15 | LOW | Código morto / imports sem uso (AP-14) | database.py:2; models.py:2; controllers.py:268 |
| F-16 | LOW | Logging inadequado (AP-14) | app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250 |

## Findings

### F-01 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 47-50, 57-61, 68, 92, 109-111, 126-129, 140, 148-151, 155, 157-161, 163-166, 174, 188, 192, 220, 224, 279-281, 289-299
Principle: OWASP A03 Injection
Description: 19 queries montadas por concatenação de strings. Em 15 delas o valor concatenado vem da requisição (body, query string ou rota): login (109-111), busca `q`/`categoria` (289-299), CRUD de produto (47-50, 57-61), criação de usuário (126-129), `produto_id`/`quantidade`/`usuario_id` do body do pedido (140, 148-151, 155, 157-161, 163-166) e ids de rota (28, 68, 92, 174, 279-281). As outras 4 (188, 192, 220, 224) concatenam valores lidos do próprio banco, que podem ter sido gravados via injection. Nenhuma query do projeto usa placeholder (`?`), exceto o seed em database.py:70-83.
Evidence:
```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
query += " AND (nome LIKE '%" + termo + "%' OR descricao LIKE '%" + termo + "%')"
```
Impact: `email = "admin@loja.com' --"` faz login como admin sem senha; `GET /produtos/busca?q=' UNION SELECT ...` lê qualquer tabela (inclusive senhas); `produto_id` enviado como string no JSON do pedido altera o UPDATE de estoque.
Recommendation: parametrizar todas as 19 queries com `?` e argumentos separados; a busca monta só os fragmentos `AND ... LIKE ?` e passa os valores numa lista (PT-01).
Contract change: NO

### F-02 [CRITICAL] Credenciais hardcoded (AP-02)
File: app.py:7, 8, 88; controllers.py:287-289
Principle: OWASP A07 / 12-Factor (Config)
Description: `SECRET_KEY` literal no código (app.py:7), `DEBUG = True` fixo (app.py:8) e `app.run(host="0.0.0.0", debug=True)` (app.py:88), sem nenhuma leitura de ambiente (`os.environ` não aparece no projeto). A mesma chave é repetida literalmente na resposta do `/health` (controllers.py:289, ver F-04).
Evidence:
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
app.run(host="0.0.0.0", port=5000, debug=True)
```
Impact: a chave está no repositório e na resposta pública da API, então qualquer token/sessão assinado com ela pode ser forjado. O debugger do Werkzeug fica ativo e exposto em todas as interfaces de rede.
Recommendation: criar `config/settings.py` lendo `SECRET_KEY`, `DEBUG`, `HOST`, `PORT`, `DB_PATH` e `TOKEN_MAX_AGE` do ambiente. Sem `SECRET_KEY` no ambiente, gerar uma chave aleatória por processo e logar um aviso. `DEBUG` passa a ter default `False`. Criar `.env.example` (PT-02).
Contract change: NO (o vazamento no `/health` é tratado em F-04)

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models.py:109-111, 126-129; database.py:75-83
Principle: OWASP A02 Cryptographic Failures
Description: a senha recebida em `POST /usuarios` é gravada em texto puro (models.py:126-129), o login compara a senha dentro do SQL (models.py:109-111) e o seed grava as 3 senhas em texto puro (database.py:75-83). Não existe nenhum uso de `bcrypt`, `argon2`, `scrypt`, `pbkdf2`, `hashlib` ou `werkzeug.security` no projeto.
Evidence:
```python
"INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" +
nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"
```
Impact: qualquer leitura do banco (F-01, `/admin/query`, `GET /usuarios`) entrega as senhas reais de todos os usuários, inclusive `admin123` do administrador.
Recommendation: `werkzeug.security.generate_password_hash` na criação e no seed; login busca o usuário por e-mail e valida com `check_password_hash`. Migração no boot: senhas existentes que não estão em formato de hash são re-hasheadas (PT-03).
Contract change: NO (login com as mesmas credenciais continua funcionando)

### F-04 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83, 99; controllers.py:285-289
Principle: OWASP A01/A09
Description: 3 pontos de vazamento. `get_todos_usuarios` (models.py:83) e `get_usuario_por_id` (models.py:99) serializam o campo `senha`, que chega ao cliente em `GET /usuarios` e `GET /usuarios/<id>`. O `/health` devolve `secret_key`, `debug` e `db_path` (controllers.py:287-289).
Evidence:
```python
"senha": row["senha"],                              # models.py:83 e 99
"secret_key": "minha-chave-super-secreta-123"       # controllers.py:289
```
Impact: qualquer cliente anônimo obtém a senha de todos os usuários (inclusive do admin) e a chave secreta da aplicação.
Recommendation: serializador de saída de usuário sem `senha` (PT-04); `/health` deixa de devolver `secret_key`, `debug` e `db_path` (PT-04 + PT-02).
Contract change: YES: o campo `senha` sai de `dados` em `GET /usuarios` e `GET /usuarios/<id>`; as chaves `secret_key`, `debug` e `db_path` saem da resposta de `GET /health`.

### F-05 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: app.py:14, 15, 16, 18, 19, 23, 26, 47-57, 59-78
Principle: OWASP A01 Broken Access Control
Description: o projeto não tem nenhum mecanismo de autenticação (`auth`, `jwt`, `login_required`, `session` e `before_request` não aparecem). `POST /login` só devolve os dados do usuário, sem token. Classificação das rotas sem auth:
- Classe 1 (administrativa): `POST /admin/reset-db` (app.py:47-57) apaga todas as tabelas; `POST /admin/query` (app.py:59-78) executa qualquer SQL recebido no body.
- Classe 2 (destrutiva): `DELETE /produtos/<id>` (app.py:16).
- Classe 3 (escrita em dado compartilhado ou de terceiro): `POST /produtos` (app.py:14), `PUT /produtos/<id>` (app.py:15), que alteram catálogo, preço e estoque; `PUT /pedidos/<id>/status` (app.py:26); `POST /pedidos` (app.py:23), que cria pedido em nome de qualquer `usuario_id` informado no body e baixa o estoque compartilhado.
- Classe 5 com senha: `GET /usuarios` (app.py:18) e `GET /usuarios/<id>` (app.py:19) expõem `senha` (F-04).
Teste de "não esqueci nada" para as escritas fora do finding: `POST /usuarios` é cadastro público e não aceita `tipo` do body (controllers.py:153-160 não repassa `tipo`, que fica `cliente`); `POST /login` é a própria autenticação.
Evidence:
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    ...
    cursor.execute(query)          # query = dados.get("sql")
```
Impact: qualquer cliente anônimo destrói o banco, lê ou altera qualquer tabela via SQL, altera preço e estoque, apaga produtos, muda o status de qualquer pedido, faz pedidos em nome de outros usuários e lê as senhas de todos.
Recommendation (PT-05):
1. `POST /login` passa a devolver um token assinado com expiração (`itsdangerous.URLSafeTimedSerializer` + `SECRET_KEY`), dentro de `dados.token`.
2. `middlewares/auth.py` com `require_auth(role=None)`: lê `Authorization: Bearer <token>`. Sem token ou com token inválido/expirado → 401; papel insuficiente → 403.
3. Remover `POST /admin/query`.
4. `POST /admin/reset-db`, `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status` e `GET /usuarios` → `require_auth(role="admin")`.
5. `GET /usuarios/<id>` → autenticado, e só o próprio usuário ou admin (outro usuário → 403).
6. `POST /pedidos` → autenticado; o `usuario_id` do body precisa ser o do token (ou o usuário precisa ser admin), senão 403.
Contract change: YES: `POST /admin/query` deixa de existir (404); `POST /login` ganha `dados.token`; as 8 rotas dos itens 4 a 6 passam a exigir `Authorization: Bearer <token>` (401 sem credencial, 403 sem o papel/dono exigido).

### F-06 [CRITICAL] God File (AP-06)
File: app.py:1-88; controllers.py:1-292; models.py:1-314
Principle: SRP (SOLID) + MVC
Description: três arquivos acumulam responsabilidades de camadas diferentes:
- `app.py`: config (7-8), registro das 19 rotas (11-32, 47, 59), handlers com SQL direto (47-78) e bootstrap/servidor (80-88).
- `controllers.py` (292 linhas, 17 funções, 5 domínios: produtos, usuários, pedidos, relatórios, health): parse HTTP, validação (28-54, 72-90, 150-158, 192-201, 242), integrações simuladas de e-mail/SMS/push (208-210, 248-250) e SQL direto (264-274).
- `models.py` (314 linhas, 17 funções, 4 domínios): SQL de produtos, usuários, pedidos e relatórios, além de regra de negócio (estoque e total 139-146, desconto 256-262).
Evidence:
```python
import controllers                       # app.py:3: um único módulo com todos os handlers
app.add_url_rule("/produtos", "listar_produtos", controllers.listar_produtos, methods=["GET"])
```
Impact: qualquer mudança num domínio mexe nos mesmos arquivos dos outros; não há como testar regra sem banco e HTTP; os nomes "controllers"/"models" não correspondem às camadas reais.
Recommendation: decompor por domínio e por camada na estrutura da §4 (`config/`, `models/`, `controllers/`, `views/`, `services/`, `middlewares/`, `utils/`), reduzindo `app.py` a entry point com `create_app()` e removendo `controllers.py` e `models.py` (PT-06).
Contract change: NO

### F-07 [HIGH] Leitura de dados de terceiros sem autenticação (AP-05)
File: app.py:24, 25, 28
Principle: OWASP A01 Broken Access Control
Description: 3 rotas de leitura (classe 5, sem senha/token) abertas a anônimos: `GET /pedidos` (todos os pedidos de todos os clientes), `GET /pedidos/usuario/<id>` (pedidos de qualquer cliente) e `GET /relatorios/vendas` (faturamento da loja).
Evidence:
```python
app.add_url_rule("/pedidos", "listar_todos_pedidos", controllers.listar_todos_pedidos, methods=["GET"])
app.add_url_rule("/relatorios/vendas", "relatorio_vendas", controllers.relatorio_vendas, methods=["GET"])
```
Impact: vazamento do histórico de compras dos clientes e de dados financeiros da loja.
Recommendation: `GET /pedidos` e `GET /relatorios/vendas` → `require_auth(role="admin")`; `GET /pedidos/usuario/<id>` → autenticado, só o próprio usuário ou admin (PT-05).
Contract change: YES: as 3 rotas passam a exigir `Authorization: Bearer <token>` (401 sem credencial, 403 sem papel/dono).

### F-08 [HIGH] Regra de negócio na camada errada (AP-07)
File: models.py:256-262; controllers.py:52-54, 208-210, 247-250, 264-274; app.py:47-78
Principle: SRP (SOLID) + MVC
Description: 5 pontos. A faixa de desconto do relatório está dentro da função de acesso a dados (models.py:256-262). A lista de categorias válidas (regra de domínio) fica no handler HTTP (controllers.py:52-54). As notificações de e-mail/SMS/push estão no meio dos handlers (controllers.py:208-210, 247-250). O controller de health faz SQL direto (controllers.py:264-274). Os handlers de `/admin/*` fazem SQL dentro do `app.py` (47-78).
Evidence:
```python
desconto = 0
if faturamento > 10000:
    desconto = faturamento * 0.1          # models.py:256-258, dentro da função de query
print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]) ...)   # controllers.py:208
```
Impact: a regra não pode ser reutilizada nem testada sem banco/HTTP; trocar o canal de notificação exige mexer em handlers HTTP.
Recommendation: cálculo de desconto e categorias válidas no model do domínio, com SQL isolado; notificações em `services/notificacao_service.py` chamadas pelo controller; SQL de health e admin nos models (PT-07).
Contract change: NO

### F-09 [HIGH] Estado global mutável / acoplamento sem DI (AP-08)
File: database.py:4-11
Principle: DIP (SOLID)
Description: uma única conexão SQLite global (`db_connection`), mutada via `global` e aberta com `check_same_thread=False`, é compartilhada por todas as requisições e threads do servidor. O caminho `loja.db` também é fixo (database.py:5).
Evidence:
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Impact: requisições concorrentes compartilham a mesma transação implícita. O `commit()` de uma requisição grava escritas pendentes de outra, e um erro no meio de uma deixa lixo para a seguinte (ver F-10). Também impede usar outro banco em testes.
Recommendation: conexão por requisição em `flask.g`, fechada no `teardown_appcontext`; caminho do banco vindo de `Settings.DB_PATH`; schema/seed executados em `init_app` (PT-08).
Contract change: NO

### F-10 [HIGH] Operação multi-etapa sem transação + exclusão física (AP-09)
File: models.py:133-169, 65-70
Principle: Integridade (ACID)
Description: 2 problemas.
1. `criar_pedido` grava em 3 tabelas em passos separados (INSERT pedidos 148-151, INSERT itens_pedido 157-161 e UPDATE estoque 163-166 por item) sem `try/rollback`. Se um passo falhar, os anteriores ficam pendentes na conexão global e são persistidos pelo próximo `commit()` de qualquer requisição. A checagem de estoque (144) e a baixa (163-166) são separadas e a baixa não tem condição, então pedidos concorrentes deixam o estoque negativo.
2. `DELETE /produtos/<id>` faz exclusão física (models.py:68) de um produto referenciado por `itens_pedido`. Os pedidos antigos passam a mostrar `"produto_nome": "Desconhecido"` (models.py:196, 228), o que apaga histórico de negócio.
Evidence:
```python
cursor.execute("INSERT INTO pedidos ...")                     # 148
...
cursor.execute("UPDATE produtos SET estoque = estoque - " + ...)  # 163, sem rollback em caso de erro
cursor.execute("DELETE FROM produtos WHERE id = " + str(id))  # 68
```
Impact: pedido sem itens, estoque baixado sem pedido, estoque negativo e perda de histórico de vendas.
Recommendation (PT-09):
1. `criar_pedido` numa transação única (`with conn:` / rollback em erro), com baixa atômica `UPDATE produtos SET estoque = estoque - ? WHERE id = ? AND estoque >= ?` e verificação de `rowcount`. Se falhar, a resposta é a mesma de hoje (400 "Estoque insuficiente para ...").
2. Soft delete de produtos: tabela `produtos` ganha `removido INTEGER NOT NULL DEFAULT 0`, `removido_em TIMESTAMP NULL` e `removido_por INTEGER NULL` (id do admin do token). `DELETE /produtos/<id>` faz `UPDATE ... SET removido = 1, removido_em = CURRENT_TIMESTAMP, removido_por = ? WHERE id = ? AND removido = 0` (id já removido → 404). `GET /produtos`, `/produtos/busca` e `/produtos/<id>` e a criação de pedido ignoram produtos removidos. Pedidos e relatórios continuam mostrando o nome do produto. Migração no boot: `ALTER TABLE produtos ADD COLUMN ...` quando a coluna não existe (`PRAGMA table_info`). Não há cascata: os itens de pedido são mantidos.
`POST /admin/reset-db` (app.py:51-54) também faz DELETE físico, mas é a ferramenta administrativa de reset do banco. Fica como está, protegida por admin (F-05), e as 4 exclusões vão para uma transação única.
Contract change: YES (comportamental): após `DELETE /produtos/<id>`, o produto continua no banco e os pedidos que o contêm mostram o nome real em vez de "Desconhecido". A resposta do DELETE (200) e o 404 do GET posterior ficam iguais.

### F-11 [MEDIUM] Query N+1 / queries repetidas (AP-10)
File: models.py:187-199, 219-231, 139-141, 154-156, 239-254; controllers.py:268-274
Principle: Performance
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem 1 query de pedidos + 1 por pedido (itens, 188/220) + 1 por item (nome do produto, 192/224), ou seja, 1 + P + I queries. `criar_pedido` busca cada produto 2 vezes (140 e 155). `relatorio_vendas` faz 5 queries sequenciais de agregação (239-254) e o health faz 4 (268-274).
Evidence:
```python
for row in rows:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Impact: o custo de `GET /pedidos` cresce linearmente com pedidos × itens.
Recommendation: uma query com `JOIN itens_pedido` + `LEFT JOIN produtos` agrupada em Python; produtos do pedido carregados uma vez com `IN (?, ?...)`; relatório com um único `SELECT COUNT(*), SUM(total), SUM(CASE WHEN status=...)` (PT-10).
Contract change: NO

### F-12 [MEDIUM] Código duplicado (AP-11)
File: controllers.py:28-50, 72-90; models.py:12-21, 31-40, 304-313, 79-86, 95-102, 171-201, 203-233
Principle: DRY
Description: 4 duplicações.
1. A validação de produto está copiada em create (controllers.py:28-50) e update (72-90). As cópias já divergem: o update não valida o tamanho do nome nem a categoria, então `PUT` aceita uma categoria que o `POST` rejeita (duplicação de regra de negócio).
2. A serialização de produto aparece 3 vezes (models.py:12-21, 31-40, 304-313).
3. A serialização de usuário aparece 2 vezes (79-86, 95-102).
4. `get_pedidos_usuario` (171-201) e `get_todos_pedidos` (203-233) são idênticas, salvo o WHERE.
Evidence:
```python
if "nome" not in dados:
    return jsonify({"erro": "Nome é obrigatório"}), 400     # controllers.py:30 e 74
```
Impact: as correções precisam ser feitas em vários lugares, e a regra de categoria já está inconsistente entre create e update.
Recommendation: `validar_produto(dados)` única no model de produto, usada por create e update; `_produto_to_dict`/`_usuario_to_dict`; uma função de listagem de pedidos com filtro opcional (PT-11). A regra única aplica a validação completa nos dois casos, o que alinha o `PUT` ao `POST`.
Contract change: YES: `PUT /produtos/<id>` com categoria inválida ou nome fora de 2-200 caracteres passa a responder 400, como já acontece no `POST`.

### F-13 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: controllers.py:10-12, 21-22, 60-62, 95-96, 108-109, 125-126, 133-134, 143-144, 164-165, 185-186, 218-220, 226-227, 234-235, 254-255, 261-262, 291-292; app.py:77-78; controllers.py:118-121, 169-170, 239-245
Principle: Robustez / Fail-fast
Description: 17 blocos `except Exception as e: return jsonify({"erro": str(e)}), 500`, que devolvem detalhes internos ao cliente. Não existe `@app.errorhandler`. Entradas inválidas viram 500: `?preco_min=abc` (`float()` em 118-121), body ausente em `/login` e `/pedidos/<id>/status` (`dados.get` em `None`, 169-170 e 239-240), `preco` string no `POST /produtos` (comparação `<` em 43), item de pedido sem `produto_id`/`quantidade` (KeyError em models.py:140). `PUT /pedidos/<id>/status` responde 200 para pedido inexistente (245, sem checar se o pedido existe).
Evidence:
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
Impact: vazamento de detalhes internos (mensagens do SQLite que ajudam a explorar F-01), status incorretos e um handler de erro copiado 17 vezes.
Recommendation: `middlewares/error_handler.py` com `AppError(mensagem, status)` + `register_error_handlers` (500 genérico com log do stack trace); validação na borda (body JSON obrigatório, números convertíveis, itens com `produto_id`/`quantidade` inteiros > 0); 404 para pedido inexistente (PT-12).
Contract change: YES: entradas malformadas que hoje dão 500 passam a 400 com `{"erro": ...}`; o 500 deixa de conter `str(e)` e devolve uma mensagem genérica; `PUT /pedidos/<id>/status` com id inexistente passa de 200 a 404.

### F-14 [LOW] Magic numbers / listas de domínio inline (AP-14)
File: models.py:247-262; controllers.py:52, 242; app.py:36; controllers.py:285-286
Principle: Clean Code
Description: 6 literais nas faixas de desconto (10000/5000/1000 e 0.1/0.05/0.02, models.py:257-262); statuses literais no relatório (247-253) e na validação (controllers.py:242); lista de categorias inline (controllers.py:52); versão `"1.0.0"` repetida (app.py:36, controllers.py:285); `"ambiente": "producao"` fixo (controllers.py:286).
Evidence:
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
```
Impact: mudar uma faixa de desconto ou um status exige caçar literais em vários arquivos.
Recommendation: `utils/constants.py` com `STATUS_PEDIDO`, `CATEGORIAS_VALIDAS`, `FAIXAS_DESCONTO`, `API_VERSION`; ambiente vindo de `Settings` (PT-14).
Contract change: NO

### F-15 [LOW] Código morto / imports sem uso (AP-14)
File: database.py:2; models.py:2; controllers.py:268
Principle: Clean Code
Description: 3 ocorrências: `import os` sem uso (database.py:2), `import sqlite3` sem uso (models.py:2) e `cursor.execute("SELECT 1")` cujo resultado nunca é lido (controllers.py:268).
Evidence:
```python
import os        # database.py:2, nenhuma referência a os.
```
Impact: ruído na leitura.
Recommendation: remover (PT-14).
Contract change: NO

### F-16 [LOW] Logging inadequado (AP-14)
File: app.py:56, 83-86; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208-210, 219, 248, 250
Principle: Clean Code
Description: 19 `print` usados como log da aplicação (5 em app.py, 14 em controllers.py). 3 deles registram o e-mail do usuário em login/cadastro (controllers.py:161, 179, 182).
Evidence:
```python
print("Login falhou: " + email)
```
Impact: não há nível nem formato, não dá para desligar, e dado pessoal vai parar no stdout.
Recommendation: módulo `logging` com logger por módulo e nível adequado; log de login sem o e-mail completo (id do usuário ou e-mail mascarado) (PT-14).
Contract change: NO

## Deprecated APIs
Nenhuma API deprecated identificada estaticamente para as versões em uso (Python 3.14.4, Flask 3.1.1, Werkzeug 3.1.8): nenhum padrão da tabela do AP-13 ocorre no código. A confirmação por execução (`python -W default app.py`) é feita no baseline da Fase 3.

## Positive Points
- O seed (database.py:70-83) já usa `executemany` com placeholders `?`.
- `CREATE TABLE IF NOT EXISTS` e seed só com banco vazio tornam o boot idempotente.
- O formato de resposta é uniforme (`dados` / `sucesso` / `mensagem` / `erro`). A refatoração preserva esse formato.
- As rotas usam conversores tipados (`<int:id>`), o que já bloqueia injection pelos ids de rota no nível do Flask.

## Refactoring Plan (Phase 3 preview)
Strategy: A) decomposição completa (Fase 1 classificou como monolítico: 4 arquivos, sem camadas).
Target structure (§4 Flask, pacotes na raiz para manter `python app.py`):
```
app.py                       # create_app() + app = create_app() + __main__
config/settings.py           # Settings do ambiente (SECRET_KEY, DEBUG, HOST, PORT, DB_PATH, TOKEN_MAX_AGE, APP_ENV)
database.py                  # conexão por requisição (sqlite3 + flask.g), schema, migração soft delete/hash, seed
models/                      # produto_model, usuario_model, pedido_model, relatorio_model (SQL parametrizado + regra de domínio)
controllers/                 # produto_, usuario_, pedido_, relatorio_, health_, admin_controller (orquestração + HTTP in/out)
views/                       # produto_, usuario_, pedido_, relatorio_, health_, admin_routes (Blueprints só delegam) + register_blueprints
services/notificacao_service.py   # e-mail/SMS/push simulados (hoje são prints)
middlewares/error_handler.py      # AppError + register_error_handlers
middlewares/auth.py               # token assinado + require_auth(role)
utils/constants.py                # status, categorias, faixas de desconto, versão
.env.example
```
`controllers.py` e `models.py` da raiz são removidos. As URLs, métodos e endpoint names do Flask são mantidos.
Contract changes requiring approval:
- F-04: `senha` sai de `GET /usuarios` e `GET /usuarios/<id>`; `secret_key`, `debug` e `db_path` saem de `GET /health`.
- F-05: `POST /admin/query` removida (404); `POST /login` devolve `dados.token`; exigem `Authorization: Bearer <token>`: admin → `POST /admin/reset-db`, `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `PUT /pedidos/<id>/status`, `GET /usuarios`; dono ou admin → `GET /usuarios/<id>`, `POST /pedidos` (`usuario_id` do body = usuário do token).
- F-07: admin → `GET /pedidos`, `GET /relatorios/vendas`; dono ou admin → `GET /pedidos/usuario/<id>`.
- F-10: `DELETE /produtos/<id>` vira soft delete (tabela `produtos`, colunas novas `removido`, `removido_em`, `removido_por`, migração `ALTER TABLE` no boot, sem cascata). A resposta não muda, e pedidos antigos passam a mostrar o nome real do produto.
- F-12: `PUT /produtos/<id>` passa a aplicar as mesmas validações do `POST` (categoria, tamanho do nome) → 400.
- F-13: entrada malformada 500 → 400; 500 sem `str(e)`; `PUT /pedidos/<id>/status` com id inexistente 200 → 404.
Out of scope:
- `print("... Devolver estoque.")` em controllers.py:250: o cancelamento de pedido nunca devolve o estoque. Implementar isso é regra de negócio nova, não refatoração. A mensagem passa para o serviço de notificação sem mudança de comportamento.
- Unicidade de e-mail em `usuarios` (a tabela não tem `UNIQUE`): exigiria tratar duplicatas já existentes e mudaria o contrato de `POST /usuarios`. Não é finding do catálogo; fica registrado como observação.

================================
Total: 16 findings
================================
