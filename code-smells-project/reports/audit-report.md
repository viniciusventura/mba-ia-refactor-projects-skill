================================
ARCHITECTURE AUDIT REPORT
================================
Project:  code-smells-project
Stack:    Python 3.14.4 + Flask 3.1.1 (flask-cors 5.0.1, sqlite3)
Files:    4 analyzed | ~780 lines of code
Date:     2026-09-30
Architecture: A) Monolítica: 4 arquivos com "camadas" só no nome; SQL em app.py, controllers.py e models.py; regra de negócio em models.py

## Summary
CRITICAL: 6 | HIGH: 3 | MEDIUM: 3 | LOW: 3

| ID | Severity | Anti-pattern | Location |
|----|----------|--------------|----------|
| F-01 | CRITICAL | SQL Injection (AP-01) | models.py:28, 48, 58, 68, 92, 110, 127, 140, 149, 155, 158, 164, 174, 188, 192, 220, 224, 280, 291-297 |
| F-02 | CRITICAL | Credenciais hardcoded (AP-02) | app.py:7, controllers.py:289 |
| F-03 | CRITICAL | Armazenamento inseguro de senha (AP-03) | models.py:109-111, 126-129; database.py:75-83 |
| F-04 | CRITICAL | Exposição de dados sensíveis (AP-04) | models.py:83, 99; controllers.py:285-289 |
| F-05 | CRITICAL | Endpoint sensível sem autenticação (AP-05) | app.py:47-57, 59-78 |
| F-06 | CRITICAL | God File (AP-06) | app.py:1-88, controllers.py:1-292, models.py:1-314 |
| F-07 | HIGH | Regra de negócio na camada errada (AP-07) | models.py:137-146, 256-262; controllers.py:208-210, 247-250, 266-274; app.py:49-55 |
| F-08 | HIGH | Estado global mutável / acoplamento sem DI (AP-08) | database.py:4-11 |
| F-09 | HIGH | Operação multi-etapa sem transação (AP-09) | models.py:133-169, 65-70 |
| F-10 | MEDIUM | Query N+1 / queries repetidas (AP-10) | models.py:187-193, 219-225, 139-141, 154-156, 239-254; controllers.py:268-274 |
| F-11 | MEDIUM | Código duplicado (AP-11) | controllers.py:28-46 × 72-90; models.py:12-21, 31-40, 304-313; 79-86, 94-102; 171-201 × 203-233 |
| F-12 | MEDIUM | Erro engolido / sem handler central / validação ausente (AP-12) | controllers.py (16 blocos except) + app.py:77; controllers.py:43-46, 87-90, 118-121, 169-170, 195-201, 239-245 |
| F-13 | LOW | Magic numbers / listas de domínio inline (AP-14) | models.py:257-262; controllers.py:47-50, 52, 242 |
| F-14 | LOW | Logging inadequado e debug fixo (AP-14) | app.py:8, 56, 83-86, 88; controllers.py (14 prints) |
| F-15 | LOW | Código morto: imports sem uso (AP-14) | models.py:2; database.py:2 |

## Findings

### F-01 [CRITICAL] SQL Injection (AP-01)
File: models.py:28, 48, 58, 68, 92, 110, 127, 140, 149, 155, 158, 164, 174, 188, 192, 220, 224, 280, 291-297
Principle: OWASP A03 Injection
Description: 19 queries montadas por concatenação de strings. As rotas com `<int:id>` limitam parte dos casos, mas `email`/`senha` (login), `nome`/`descricao`/`categoria` (produtos), `nome`/`email`/`senha` (usuários), `termo`/`categoria` (busca) e `produto_id`/`quantidade` (JSON do pedido) chegam sem filtro ao SQL.
Evidence:
```python
cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```
Impact: `email = "admin@loja.com' --"` faz login como admin sem senha. `GET /produtos/busca?q=' UNION SELECT ...` lê qualquer tabela, inclusive as senhas. É explorável sem autenticação.
Recommendation: parametrizar todas as queries com `?` (PT-01).
Contract change: NO

### F-02 [CRITICAL] Credenciais hardcoded (AP-02)
File: app.py:7, controllers.py:289
Principle: OWASP A07 / 12-Factor (Config)
Description: `SECRET_KEY` é um literal no código, sem leitura de ambiente, e o mesmo valor é copiado na resposta do `/health` (ver F-04).
Evidence:
```python
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
```
Impact: o segredo fica no controle de versão e é público via API. Qualquer assinatura feita com ele (sessões, tokens) pode ser forjada.
Recommendation: `config/settings.py` lendo `SECRET_KEY`, `DEBUG`, `DB_PATH`, `HOST`, `PORT` e `ADMIN_TOKEN` do ambiente, com `.env.example` (PT-02).
Contract change: NO (o vazamento no /health é tratado em F-04)

### F-03 [CRITICAL] Armazenamento inseguro de senha (AP-03)
File: models.py:109-111, 126-129; database.py:75-83
Principle: OWASP A02 Cryptographic Failures
Description: a senha é gravada em texto puro no `INSERT` de usuário e no seed, e comparada dentro do SQL. Não há nenhuma biblioteca de hash no projeto (bcrypt, argon2, scrypt, pbkdf2 ou werkzeug.security).
Evidence:
```python
"INSERT INTO usuarios (nome, email, senha, tipo) VALUES ('" +
nome + "', '" + email + "', '" + senha + "', '" + tipo + "')"
```
Impact: qualquer leitura do banco (backup, F-01, F-05, F-04) expõe as senhas de todos os usuários.
Recommendation: `werkzeug.security.generate_password_hash` ao criar/seedar e `check_password_hash` no login, buscando o usuário só pelo e-mail (PT-03). O `loja.db` existente, com senhas em texto puro, precisa ser recriado.
Contract change: NO (login continua com o mesmo payload e as mesmas respostas)

### F-04 [CRITICAL] Exposição de dados sensíveis (AP-04)
File: models.py:83, 99; controllers.py:285-289
Principle: OWASP A01/A09
Description: 2 serializadores de usuário incluem `senha` e chegam ao `jsonify` de `GET /usuarios` e `GET /usuarios/<id>`. O `GET /health` devolve `secret_key`, `db_path` e `debug`.
Evidence:
```python
"senha": row["senha"],                           # models.py:83 e :99
"secret_key": "minha-chave-super-secreta-123"    # controllers.py:289
```
Impact: qualquer cliente anônimo obtém as senhas de todos os usuários e a chave da aplicação.
Recommendation: serializador de saída de usuário sem `senha`; `/health` só com status, contagens, versão e ambiente (PT-04, PT-02).
Contract change: YES: `senha` sai dos itens de `GET /usuarios` e `GET /usuarios/<id>`; `secret_key`, `db_path` e `debug` saem do `GET /health`.

### F-05 [CRITICAL] Endpoint sensível sem autenticação (AP-05)
File: app.py:47-57, 59-78
Principle: OWASP A01 Broken Access Control
Description: `POST /admin/reset-db` apaga as 4 tabelas e `POST /admin/query` executa SQL arbitrário vindo do body (`cursor.execute(query)`, app.py:69). Não há nenhum mecanismo de autenticação no projeto (grep por `auth|jwt|login_required|session|before_request` sem resultado).
Evidence:
```python
query = dados.get("sql", "")
cursor.execute(query)
```
Impact: qualquer cliente lê as senhas, altera preços ou destrói todos os dados.
Recommendation: remover `/admin/query`; proteger `/admin/reset-db` com `middlewares/auth.py` → `require_admin_token`, que compara `Authorization: Bearer <token>` com `ADMIN_TOKEN` do ambiente em tempo constante (PT-05). Sem `ADMIN_TOKEN` configurado, a rota fica sempre bloqueada.
Contract change: YES: `/admin/query` deixa de existir (404); `/admin/reset-db` passa a exigir `Authorization: Bearer <ADMIN_TOKEN>` (401 sem credencial ou com credencial inválida).

### F-06 [CRITICAL] God File (AP-06)
File: app.py:1-88, controllers.py:1-292, models.py:1-314
Principle: SRP (SOLID) + MVC
Description: 3 arquivos acumulam responsabilidades de camadas diferentes:
- app.py: config (7-8), registro de rotas (11-47), SQL (49-55, 66-76), execução (80-88).
- controllers.py: HTTP/validação de 5 domínios (produtos, usuários, pedidos, relatórios, health), acesso a dados (266-274), notificações (208-210, 248-250) e config (285-289).
- models.py: SQL de 4 domínios, regra de estoque/total (137-146) e regra de desconto (256-262).
Evidence:
```python
def health_check():          # controllers.py:264: "controller" com SQL e config
    db = get_db()
    cursor.execute("SELECT COUNT(*) FROM produtos")
```
Impact: toda mudança toca arquivos centrais; não há como testar regra de negócio sem banco e HTTP.
Recommendation: decomposição completa por domínio em `config/`, `models/`, `controllers/`, `views/`, `services/`, `middlewares/`, `utils/` (PT-06).
Contract change: NO

### F-07 [HIGH] Regra de negócio na camada errada (AP-07)
File: models.py:137-146, 256-262; controllers.py:208-210, 247-250, 266-274; app.py:49-55
Principle: SRP (SOLID) + MVC
Description: 6 pontos: regra de desconto por faixa de faturamento e validação de estoque/cálculo do total dentro de funções de acesso a dados; notificações (e-mail, SMS, push) no meio do handler HTTP; SQL direto no controller do health e na rota de reset.
Evidence:
```python
if faturamento > 10000:
    desconto = faturamento * 0.1
```
Impact: a regra fica presa ao SQL; as notificações ficam presas ao HTTP; nenhuma das duas pode ser reutilizada ou testada sozinha.
Recommendation: regras de domínio (desconto, total, estoque) como funções do model; notificações em `services/notificacao_service.py` chamadas pelo controller (PT-07).
Contract change: NO

### F-08 [HIGH] Estado global mutável / acoplamento sem DI (AP-08)
File: database.py:4-11
Principle: DIP (SOLID)
Description: uma única conexão global, criada sob demanda com `global` e compartilhada entre as threads do servidor com `check_same_thread=False`.
Evidence:
```python
global db_connection
if db_connection is None:
    db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
Impact: requisições concorrentes compartilham o mesmo estado transacional, e um `commit` de uma requisição grava escritas pendentes de outra (ver F-09). O caminho do banco não é configurável.
Recommendation: conexão por requisição em `flask.g`, fechada no `teardown_appcontext`, com caminho vindo de `Settings` (PT-08).
Contract change: NO

### F-09 [HIGH] Operação multi-etapa sem transação (AP-09)
File: models.py:133-169, 65-70
Principle: Integridade (ACID)
Description: `criar_pedido` faz 1 INSERT em `pedidos` e, por item, 1 INSERT em `itens_pedido` e 1 UPDATE de estoque, sem `rollback`. Se um passo falhar (ex.: `KeyError` em `item["quantidade"]`), as escritas anteriores ficam pendentes na conexão global e são gravadas pelo próximo `commit` de qualquer requisição. O estoque é checado e decrementado em passos separados (corrida). `deletar_produto` apaga o produto e deixa `itens_pedido` órfãos, que passam a aparecer como "Desconhecido".
Evidence:
```python
cursor.execute("INSERT INTO pedidos ...")          # 149
...
cursor.execute("UPDATE produtos SET estoque = estoque - ...")   # 164
db.commit()                                         # 168: único ponto; sem rollback
```
Impact: pedidos sem itens, estoque decrementado sem pedido e estoque negativo sob concorrência.
Recommendation: `with database.transaction():` (commit/rollback) envolvendo todo o pedido; `UPDATE ... SET estoque = estoque - ? WHERE id = ? AND estoque >= ?` checando `rowcount` (PT-09). Os órfãos da exclusão: manter `produto_nome = "Desconhecido"` (comportamento atual) e não apagar histórico de pedidos.
Contract change: NO

### F-10 [MEDIUM] Query N+1 / queries repetidas (AP-10)
File: models.py:187-193, 219-225, 139-141, 154-156, 239-254; controllers.py:268-274
Principle: Performance
Description: `get_pedidos_usuario` e `get_todos_pedidos` fazem 1 + P + I queries (1 por pedido e 1 por item). `criar_pedido` busca cada produto 2 vezes (140 e 155). O relatório faz 5 queries separadas onde 1 agregação basta; o health faz 4.
Evidence:
```python
for row in rows:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = " + str(row["id"]))
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = " + str(item["produto_id"]))
```
Impact: o custo de `GET /pedidos` cresce com o número de itens do banco inteiro.
Recommendation: 1 query de itens com `LEFT JOIN produtos` para todos os pedidos da lista; relatório com `COUNT`/`SUM(CASE ...)` numa query; reutilizar a busca de produto no pedido (PT-10).
Contract change: NO

### F-11 [MEDIUM] Código duplicado (AP-11)
File: controllers.py:28-46 × 72-90; models.py:12-21, 31-40, 304-313; models.py:79-86, 94-102; models.py:171-201 × 203-233
Principle: DRY
Description: 5 duplicações: validação de produto copiada entre criar e atualizar; serialização de produto 3 vezes; de usuário 2 vezes; montagem de pedido+itens em 2 funções quase idênticas. A cópia da validação é **divergente**: `atualizar_produto` não valida tamanho do nome nem categoria, então um produto pode ser atualizado para uma categoria que o `POST` recusaria.
Evidence:
```python
if "nome" not in dados:                      # controllers.py:30 e :74
    return jsonify({"erro": "Nome é obrigatório"}), 400
```
Impact: regra de negócio inconsistente entre criação e atualização; mudança de schema exige editar 3 serializadores.
Recommendation: uma função `validar_produto(dados)` usada por create e update; um serializador por entidade; uma função de montagem de pedidos (PT-11). **Nota:** aplicar a validação completa no update faz o `PUT` passar a recusar nome curto/longo e categoria inválida (400), que hoje são aceitos.
Contract change: YES: `PUT /produtos/<id>` passa a devolver 400 para nome < 2 ou > 200 caracteres e categoria fora da lista, como o `POST` já faz.

### F-12 [MEDIUM] Erro engolido / sem handler central / validação ausente (AP-12)
File: controllers.py:10, 21, 60, 95, 108, 125, 133, 143, 164, 185, 218, 226, 234, 254, 261, 291; app.py:77; controllers.py:43-46, 87-90, 118-121, 169-170, 195-201, 239-245
Principle: Robustez / Fail-fast
Description: 17 blocos `except Exception as e` devolvem `str(e)` ao cliente; não há `@app.errorhandler`. Entradas inválidas viram 500: body ausente/não-JSON em `/login` e `/pedidos/<id>/status` (`None.get`), `preco`/`estoque` não numéricos (`TypeError` em `< 0`), `preco_min=abc` (`float`), itens de pedido sem `produto_id`/`quantidade` (`KeyError`). `quantidade` ≤ 0 é aceita: um pedido com quantidade negativa **aumenta** o estoque e gera total negativo. `PUT /pedidos/<id>/status` devolve 200 para pedido inexistente.
Evidence:
```python
except Exception as e:
    return jsonify({"erro": str(e)}), 500
```
Impact: mensagens internas (SQL, tipos) vazam ao cliente; erro do cliente aparece como erro do servidor; manipulação de estoque via quantidade negativa.
Recommendation: `middlewares/error_handler.py` com `AppError` e handlers para `AppError`, `HTTPException` e `Exception` (500 genérico, logado); validação de tipo e de faixa na borda (PT-12).
Contract change: YES: respostas 500 passam a trazer mensagem genérica (mesma chave `erro`); entrada malformada (body ausente/não-JSON, tipos inválidos, `preco_min`/`preco_max` não numéricos, itens sem `produto_id`/`quantidade`, `quantidade` ≤ 0) passa de 500 (ou 201) para 400; `PUT /pedidos/<id>/status` com pedido inexistente passa de 200 para 404.

### F-13 [LOW] Magic numbers / listas de domínio inline (AP-14)
File: models.py:257-262; controllers.py:47-50, 52, 242
Principle: Clean Code
Description: 6 literais de regra de desconto (10000/0.1, 5000/0.05, 1000/0.02), limites de nome (2, 200) e 2 listas de domínio inline (categorias, status).
Evidence:
```python
elif faturamento > 5000:
    desconto = faturamento * 0.05
```
Impact: regra escondida no código; alterar uma faixa exige caçar literais.
Recommendation: `utils/constants.py` com `CATEGORIAS_VALIDAS`, `STATUS_PEDIDO`, `FAIXAS_DESCONTO`, `NOME_MIN/MAX` (PT-14).
Contract change: NO

### F-14 [LOW] Logging inadequado e debug fixo (AP-14)
File: app.py:8, 56, 83-86, 88; controllers.py:8, 11, 57, 61, 106, 161, 179, 182, 208, 209, 210, 219, 248, 250
Principle: Clean Code
Description: 19 `print` como log de aplicação (3 deles com e-mail do usuário) e `debug=True` fixo em 2 lugares (config e `app.run`), além de host/porta fixos.
Evidence:
```python
app.run(host="0.0.0.0", port=5000, debug=True)
```
Impact: o debugger interativo do Werkzeug exposto em 0.0.0.0 permite execução de código remoto; logs sem nível nem destino configurável.
Recommendation: `logging` com logger por módulo; `DEBUG`, `HOST`, `PORT` vindos de `Settings`, com `DEBUG=false` por padrão (PT-14, PT-02).
Contract change: NO

### F-15 [LOW] Código morto: imports sem uso (AP-14)
File: models.py:2; database.py:2
Principle: Clean Code
Description: 2 imports nunca usados: `import sqlite3` em models.py e `import os` em database.py.
Evidence:
```python
import sqlite3   # models.py:2, nenhuma referência a sqlite3. no arquivo
```
Impact: ruído; sugere dependências que não existem.
Recommendation: remover na decomposição (PT-14).
Contract change: NO

## Deprecated APIs
Nenhuma API deprecated identificada para as versões em uso (Python 3.14.4, Flask 3.1.1, flask-cors 5.0.1). Detecção estática; a confirmação com `python -W default` será feita no baseline da Fase 3.

## Positive Points
- O seed em database.py:70-83 já usa placeholders `?` com `executemany`.
- As rotas com id usam o conversor `<int:...>`, o que já barra injeção pelos parâmetros de URL.
- O envelope de resposta é consistente (`dados`, `sucesso`, `mensagem`, `erro`) e deve ser mantido.
- `criar_produto` já valida campos obrigatórios, faixas e categoria.

## Refactoring Plan (Phase 3 preview)
Strategy: A) decomposição completa. A Fase 1 classificou o projeto como monolítico; `controllers.py` e `models.py` da raiz são removidos após a migração.
Target structure (mvc-guidelines §4, Python/Flask):
- `app.py`: `create_app()` + `app = create_app()` + `if __name__ == "__main__"`; `python app.py` continua funcionando.
- `config/settings.py`: `Settings` lida do ambiente (`SECRET_KEY`, `DEBUG`, `HOST`, `PORT`, `DB_PATH`, `ADMIN_TOKEN`, `AMBIENTE`).
- `database.py`: conexão por requisição (`flask.g` + teardown), `init_app`, `transaction()`, schema e seed (senhas com hash).
- `models/`: `produto_model.py`, `usuario_model.py`, `pedido_model.py` (pedidos + agregação do relatório + regras de total/desconto), `sistema_model.py` (contagens do health, limpeza do reset).
- `controllers/`: `produto_controller.py`, `usuario_controller.py`, `pedido_controller.py`, `relatorio_controller.py`, `sistema_controller.py` (index, health, reset).
- `views/`: um Blueprint por domínio (`produto_routes.py`, `usuario_routes.py` com `/login`, `pedido_routes.py`, `relatorio_routes.py`, `sistema_routes.py`) e `register_blueprints(app)` em `views/__init__.py`. As views só delegam aos controllers; URLs e nomes de endpoint preservados.
- `services/notificacao_service.py`: notificações de pedido (e-mail/SMS/push simulados via log).
- `middlewares/error_handler.py` (`AppError` + `register_error_handlers`) e `middlewares/auth.py` (`require_admin_token`).
- `utils/constants.py`: categorias, status, faixas de desconto, limites.
- `.env.example` + README atualizado.
Sem desvios da §4.
Contract changes requiring approval:
- F-05: `POST /admin/query` removido (404).
- F-05: `POST /admin/reset-db` exige `Authorization: Bearer <ADMIN_TOKEN>` (401 sem credencial ou com credencial inválida).
- F-04: `senha` removido das respostas de `GET /usuarios` e `GET /usuarios/<id>`.
- F-04: `secret_key`, `db_path` e `debug` removidos de `GET /health`.
- F-11: `PUT /produtos/<id>` passa a aplicar a mesma validação do `POST` (400 para nome fora de 2-200 caracteres e categoria inválida).
- F-12: respostas 500 com mensagem genérica (sem `str(e)`); entrada malformada → 400 em vez de 500; `quantidade` ≤ 0 → 400; `PUT /pedidos/<id>/status` inexistente → 404 em vez de 200.
Out of scope:
- Autenticação nas demais rotas que expõem ou alteram dados de outros usuários (`GET /usuarios`, `GET /pedidos`, `GET /relatorios/vendas`, escrita de produtos e status de pedido). Exigiria que `/login` emitisse um token, uma mudança de contrato maior que deve ser decidida à parte.
- Devolver estoque ao cancelar pedido: hoje só há um log ("Devolver estoque"); implementar mudaria o comportamento do negócio. O log será mantido via serviço de notificação.
- O `loja.db` existente tem senhas em texto puro e não é migrado; deve ser apagado para o seed recriar com hash.

================================
Total: 15 findings
================================
