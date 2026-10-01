# Catálogo de Anti-patterns

Referência da **Fase 2 (Auditoria)**. Cada entrada define **o que procurar**, **como confirmar** e **quanto pesa**. O catálogo é agnóstico de linguagem: os sinais cobrem Python e JavaScript/TypeScript, e a seção "Genérico" vale para qualquer stack.

## Índice

| ID | Anti-pattern | Severidade | Princípio violado |
|---|---|---|---|
| [AP-01](#ap-01) | SQL Injection | CRITICAL | OWASP A03 Injection |
| [AP-02](#ap-02) | Credenciais hardcoded | CRITICAL | OWASP A07 / 12-Factor (Config) |
| [AP-03](#ap-03) | Armazenamento inseguro de senha | CRITICAL | OWASP A02 Cryptographic Failures |
| [AP-04](#ap-04) | Exposição de dados sensíveis | CRITICAL | OWASP A01/A09 |
| [AP-05](#ap-05) | Endpoint sensível sem autenticação | CRITICAL | OWASP A01 Broken Access Control |
| [AP-06](#ap-06) | God Class / God File | CRITICAL | SRP (SOLID) + MVC |
| [AP-07](#ap-07) | Regra de negócio na camada errada | HIGH | SRP (SOLID) + MVC |
| [AP-08](#ap-08) | Estado global mutável / acoplamento sem DI | HIGH | DIP (SOLID) |
| [AP-09](#ap-09) | Operação multi-etapa sem transação | HIGH | Integridade (ACID) |
| [AP-10](#ap-10) | Query N+1 / queries repetidas | MEDIUM | Performance |
| [AP-11](#ap-11) | Código duplicado | MEDIUM | DRY |
| [AP-12](#ap-12) | Erro engolido / sem handler central / validação ausente | MEDIUM | Robustez / Fail-fast |
| [AP-13](#ap-13) | Uso de API deprecated | MEDIUM | Manutenibilidade |
| [AP-14](#ap-14) | Magic numbers, nomes ruins, código morto, logging inadequado | LOW | Clean Code |

---

## Regras de uso (leia antes de auditar)

1. **Escopo da busca.** Ignore sempre dependências e artefatos: `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `.git/`, `*.db`, lockfiles (`package-lock.json`, `yarn.lock`, `*.lock`) e a própria pasta `.claude/`. Um grep que varre a `.venv` ou um lockfile produz contagens e falsos positivos (ex.: `minipass` casando com `*Pass`). Arquivos de exemplo de requisição (`*.http`, `*.rest`, coleções Postman) não são código-fonte: use-os para descobrir endpoints, não como finding.
2. **Buscar → ler → reportar.** Os *sinais* são pontos de partida. **Nunca** reporte um finding só porque o padrão bateu: abra o trecho e aplique o "Como confirmar". Heurísticas como "query dentro de loop" geram falsos positivos (ex.: a query está *depois* do loop, ou em outra função).
3. **Linhas exatas.** Todo finding cita `arquivo:linha` ou `arquivo:inicio-fim`. Quando o mesmo anti-pattern aparece em vários pontos, gere **um finding** listando **todas** as ocorrências e informe a contagem (ex.: "19 queries").
4. **Régua única.** Use a severidade definida aqui. Só altere com as regras de ajuste abaixo, e justifique a alteração no finding.
5. **Ausência também é informação.** Se um anti-pattern comum na stack **não** ocorre (ex.: todas as queries usam placeholders), não o reporte. Opcionalmente, cite-o como ponto positivo no relatório.

### Ajuste de severidade

| Situação | Ajuste |
|---|---|
| Problema de segurança **comprovadamente explorável** sem autenticação | mantém ou sobe para CRITICAL |
| Combinação que agrava (ex.: token previsível **+** role aceita do body) | agrupe em um finding com a severidade mais alta |
| Código afetado é **morto** (nunca chamado) | desce um nível e mencione que é código morto |
| Duplicação de **regra de negócio** (não apenas de formatação) | continua MEDIUM (DRY), mas cite o impacto de inconsistência |

---

<a id="ap-01"></a>
## AP-01 · SQL Injection · CRITICAL

**Princípio:** OWASP A03 Injection.
**O que é:** a query SQL é montada juntando texto vindo de fora (request, parâmetro), e esse texto pode alterar a estrutura da query.

**Sinais de detecção**
- Python: `execute(` recebendo string com `+`, f-string (`f"SELECT`), `%` ou `.format(`; variável `query +=` com fragmentos SQL.
- JS/TS: template literal com `${` ou `+` dentro de string contendo `SELECT|INSERT|UPDATE|DELETE`; `db.run/get/all/query(` com string montada.
- Genérico: `execute(variavel)` onde a variável vem diretamente do body da requisição (execução de SQL arbitrário).
- Regex sugerida (cobre linhas de continuação `'" +` e `query += " AND`):
  `(SELECT|INSERT|UPDATE|DELETE)[^"'\n]*["'] *\+|\+ *["'][^"'\n]*(WHERE|VALUES|SET|AND)|'["'] *\+|\+ *["']'|\w+ *\+= *f?["'] *(AND|OR|WHERE|ORDER|LIMIT)|f["'](SELECT|INSERT|UPDATE|DELETE)|\$\{[^}]+\}[^`]*(WHERE|VALUES)`
- Uma query pode ocupar várias linhas: conte **queries** (statements), não linhas.

**Como confirmar**
- O valor concatenado vem de fora (request, argumento de função pública)? Se for constante interna, é LOW (estilo), não injection.
- **Não é finding** se a query usa placeholders: `?`, `%s` passado como 2º argumento, `:nome`, `$1`, ou ORM (`filter_by`, `Model.query.filter(...)`). O `like(f'%{x}%')` do SQLAlchemy é parametrizado.
- **Não é finding** quando o que se concatena são apenas **marcadores gerados** e os valores vão separados: `"... WHERE id IN (" + ", ".join("?" for _ in ids) + ")", ids`. Esse é o jeito correto de parametrizar um `IN` de tamanho variável.
- Conte todas as queries afetadas.

**Exemplo**
```python
cursor.execute("SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'")
# email = "admin@x.com' --"  → a verificação de senha vira comentário
```
**Correção:** playbook → *PT-01 Parametrizar queries*.

---

<a id="ap-02"></a>
## AP-02 · Credenciais hardcoded · CRITICAL

**Princípio:** OWASP A07 / 12-Factor App (config no ambiente).
**O que é:** segredos (chave, senha, token, URL com usuário e senha) escritos no código-fonte.

**Sinais de detecção**
- Nomes: `SECRET_KEY`, `secret`, `password`, `passwd`, `pwd`, `senha`, `token`, `api_key`, `apiKey`, `*Key`, `*Pass`, `private_key`, `dbPass`, `smtp*` atribuídos a **string literal**.
- Prefixos conhecidos: `pk_live_`, `sk_live_`, `AKIA`, `ghp_`, `xox`.
- Regex sugerida (sufixos camelCase são case-sensitive para não casar `minipass`):
  `((?i:secret|passw|pwd|senha|token|api_?key|private_?key)\w*|[a-z]\w*(Key|Pass|Secret|Token))["']?\]?\s*[:=]\s*["'][^"']{3,}["']`

**Como confirmar**
- É **configuração da aplicação**? Payloads de exemplo (`*.http`, testes, seeds de dados fictícios) não são credenciais. Um token montado por concatenação é AP-05, não AP-02.
- É um valor real ou apenas um default de desenvolvimento lido de `os.environ.get("X", "dev")`? Um default inofensivo **com leitura de ambiente** é LOW. Um literal sem leitura de ambiente é CRITICAL.
- Verifique se o segredo **vaza** também em resposta de API ou log. Nesse caso, cite também AP-04.

**Exemplo**
```js
const config = { dbPass: "senha_super_secreta_prod_123", paymentGatewayKey: "pk_live_1234567890abcdef" };
```
**Correção:** playbook → *PT-02 Extrair configuração para ambiente*.

---

<a id="ap-03"></a>
## AP-03 · Armazenamento inseguro de senha · CRITICAL

**Princípio:** OWASP A02 Cryptographic Failures.
**O que é:** senha gravada em texto puro, com hash rápido/sem salt (MD5, SHA1, SHA256 simples) ou com "criptografia" caseira (base64, loops).

**Sinais de detecção**
- `hashlib.md5`, `hashlib.sha1`, `hashlib.sha256` aplicados a senha; `createHash('md5'|'sha1')`.
- `base64`/`btoa`/`Buffer.from(...).toString('base64')` aplicado a senha.
- Coluna `senha`/`password`/`pass` inserida diretamente do input, sem nenhuma chamada de hash.
- Comparação de senha dentro do SQL (`WHERE ... AND senha = ...`).
- Senha default quando ausente (`pwd || "123456"`).
- **Ausência** de `bcrypt`, `argon2`, `scrypt`, `pbkdf2`, `werkzeug.security` no projeto inteiro é um indício forte.

**Como confirmar**
- Siga o fluxo de criação de usuário até o `INSERT`/`save`: o valor gravado passou por uma função de hash adequada?
- Hash caseiro: teste mentalmente (ou execute) se entradas diferentes colidem.

**Exemplo**
```python
self.password = hashlib.md5(pwd.encode()).hexdigest()   # md5('1234') está em qualquer rainbow table
```
**Correção:** playbook → *PT-03 Hash de senha adequado*.

---

<a id="ap-04"></a>
## AP-04 · Exposição de dados sensíveis · CRITICAL

**Princípio:** OWASP A01 (exposição) / A09 (logging).
**O que é:** senha, hash de senha, número de cartão, chave ou configuração interna devolvidos pela API ou escritos em log.

**Sinais de detecção**
- Serializadores (`to_dict`, `toJSON`, dicts de resposta) contendo `password`, `senha`, `pass`, `hash`, `secret`, `card`, `cvv`.
- Endpoints de health/debug devolvendo `secret_key`, `debug`, `db_path`, variáveis de ambiente.
- `print`/`console.log`/`logger.*` interpolando `card`, `cc`, `password`, `pwd`, `token`, `*Key`.
- Handler de erro devolvendo `str(e)` / `err.message` / stack trace ao cliente (se só isso, classifique como AP-12 MEDIUM).

**Como confirmar**
- O campo chega de fato à resposta? Siga o serializador até o `jsonify`/`res.json`.

**Exemplo**
```js
console.log(`Processando cartão ${cc} na chave ${config.paymentGatewayKey}`);
```
**Correção:** playbook → *PT-04 DTO/serializador de saída* e *PT-02*.

---

<a id="ap-05"></a>
## AP-05 · Endpoint sensível sem autenticação · CRITICAL

**Princípio:** OWASP A01 Broken Access Control.
**O que é:** rotas administrativas, destrutivas ou de privilégio acessíveis sem autenticação/autorização; autenticação falsa.

**Sinais de detecção**
- Rotas com `admin`, `reset`, `query`, `delete`, `report`, `financial` sem decorator/middleware de auth (`@login_required`, `@jwt_required`, `requireAuth`, `authenticate`).
- Endpoint que executa comando/SQL recebido no body.
- Token montado por concatenação (`'token-' + id`), sem assinatura.
- Campo de privilégio (`role`, `tipo`, `is_admin`) aceito diretamente do body na criação/edição de usuário.
- **Ausência** de qualquer mecanismo de auth no projeto (`grep -i "auth|jwt|login_required|session"`).

**Como confirmar**
- Existe middleware global que proteja a rota (ex.: `app.use(auth)` antes das rotas, `before_request`)? Se sim, não é finding.
- A ação é realmente sensível (lê dados de outros usuários, altera privilégio, apaga dados)?

**Exemplo**
```python
@app.route("/admin/query", methods=["POST"])
def executar_query():
    cursor.execute(request.get_json()["sql"])     # qualquer pessoa executa qualquer SQL
```
**Correção:** playbook → *PT-05 Proteger rotas sensíveis*.

---

<a id="ap-06"></a>
## AP-06 · God Class / God File · CRITICAL

**Princípio:** SRP (SOLID) e separação MVC.
**O que é:** uma classe ou arquivo que acumula responsabilidades de camadas diferentes: conexão/schema, acesso a dados, regra de negócio, roteamento/HTTP e integrações.

**Sinais de detecção**
- Um arquivo que contém **3 ou mais** destes: criação de conexão/`CREATE TABLE`, SQL/ORM, definição de rotas (`app.get/post`, `@app.route`, `add_url_rule`), regra de negócio (cálculos, `if` de domínio), chamada a serviço externo (pagamento, e-mail).
- Arquivo com funções de **vários domínios** (produtos + usuários + pedidos + relatórios).
- Tamanho: > 300 linhas ou > 15 funções/métodos públicos (indício, não prova).

**Como confirmar**
- Liste as responsabilidades presentes com as linhas de cada uma. O finding deve mostrar esse mapa (ex.: "conexão (7), DDL (12-16), seed (18-21), rotas (28, 80, 131)").
- Arquivo grande, mas coeso num único domínio e numa única camada, **não** é God Class.

**Exemplo**
```js
class AppManager {            // conexão + CREATE TABLE + seed + rotas + checkout + pagamento + relatório
  initDb() { ... }  setupRoutes(app) { app.post('/api/checkout', ...) ... }
}
```
**Correção:** playbook → *PT-06 Decompor God Class em camadas MVC*.

---

<a id="ap-07"></a>
## AP-07 · Regra de negócio na camada errada · HIGH

**Princípio:** SRP (SOLID) e MVC. Controllers orquestram, models guardam dados e regras de domínio, e rotas só roteiam.
**O que é:** cálculos e decisões de negócio dentro de rotas/handlers HTTP ou dentro de funções de acesso a dados; efeitos colaterais (notificação, e-mail) no meio do handler; pastas de camada que existem mas não são usadas.

**Sinais de detecção**
- Handler de rota com `db.session`/`Model.query`/SQL **e** validações **e** cálculos no mesmo corpo (conte: acessos a dados × validações por arquivo de rota).
- Função de acesso a dados com limiares de negócio (`if faturamento > 10000: desconto = ...`).
- `print("ENVIANDO EMAIL...")`, `sendEmail(...)` dentro do handler.
- Pasta `services/` ou `controllers/` existente, mas **não importada** por nenhuma rota.

**Como confirmar**
- A lógica é de domínio (seria a mesma em CLI ou em fila) ou é de HTTP (status code, parse de request)? Só a de domínio fora do lugar é finding.

**Exemplo**
```python
@task_bp.route('/tasks', methods=['GET'])
def get_tasks():
    for t in Task.query.all():
        if t.due_date and t.due_date < datetime.utcnow() and t.status not in ('done','cancelled'): ...
```
**Correção:** playbook → *PT-07 Extrair regra para model/service*.

---

<a id="ap-08"></a>
## AP-08 · Estado global mutável / acoplamento sem DI · HIGH

**Princípio:** DIP (SOLID).
**O que é:** variáveis de módulo alteradas em tempo de execução e compartilhadas entre requisições; dependências (conexão, serviços) obtidas por import global em vez de injetadas.

**Sinais de detecção**
- Python: `global x` dentro de função; variável de módulo `x = None`/`{}`/`[]` reatribuída ou mutada; `check_same_thread=False`.
- JS: `let x = {}`/`let x = 0` em escopo de módulo **e** exportado ou mutado por funções; objetos `cache` globais sem limite.
- Instâncias globais criadas no import (`db = connect(...)` no topo de módulo usado por todos).

**Como confirmar**
- A variável é **mutada** após o carregamento? Constantes e singletons imutáveis (ex.: `db = SQLAlchemy()` configurado via `init_app`) não são finding.

**Exemplo**
```python
db_connection = None
def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect(db_path, check_same_thread=False)
```
**Correção:** playbook → *PT-08 Injeção de dependência / conexão por requisição*.

---

<a id="ap-09"></a>
## AP-09 · Operação multi-etapa sem transação · HIGH

**Princípio:** integridade de dados (atomicidade, ACID).
**O que é:** uma operação de negócio grava em várias tabelas em passos separados, sem transação. Se um passo falhar, os anteriores ficam gravados. Inclui exclusões que deixam registros órfãos.

**Sinais de detecção**
- Vários `INSERT`/`UPDATE`/`DELETE` na mesma função/fluxo **sem** `BEGIN`/`COMMIT`/`ROLLBACK`, `with conn:`, `session.begin()`, `db.transaction`.
- Callbacks aninhados de escrita (`db.run(... , function(){ db.run(...) })`): callback hell de escrita.
- `DELETE` de uma entidade que tem dependentes (FK lógica), deixando registros órfãos.
- **Exclusão física de entidade com histórico:** `DELETE FROM` / `db.session.delete(` / `.destroy(` em clientes/usuários, produtos, pedidos, matrículas, pagamentos, tarefas ou categorias, ou em cascata sobre os dependentes. Isso apaga histórico de negócio (faturamento, pedidos antigos, auditoria).

**Como confirmar**
- Simule a falha no 2º passo: o 1º fica gravado? Se sim, é finding.
- Exclusão física: a entidade é referenciada por registros históricos ou representa um cliente/produto? Se sim, é finding. A recomendação é **sempre soft delete** (PT-09), nunca "apagar os dependentes também". Tabelas puramente técnicas (cache, sessão, tokens expirados) não entram.

**Exemplo**
```js
db.run("INSERT INTO enrollments ...", function () {
  db.run("INSERT INTO payments ...", function (err) {   // se falhar, a matrícula já existe
```
**Correção:** playbook → *PT-09 Transação e async/await* e *Exclusão: soft delete*.

---

<a id="ap-10"></a>
## AP-10 · Query N+1 / queries repetidas · MEDIUM

**Princípio:** performance (número de roundtrips ao banco).
**O que é:** uma query para buscar a lista e mais uma query **por item** dentro do loop; ou várias queries `COUNT` quase idênticas em sequência.

**Sinais de detecção**
- `execute(`, `.query.`, `.get(`, `db.get/all(`, `find(` **dentro do corpo** de `for`/`forEach`/`map`.
- Acesso a relacionamento lazy dentro de loop (`len(u.tasks)`, `t.user.name`).
- Sequência de `filter_by(status=X).count()` para cada valor de um enum.

**Como confirmar**
- A query está **dentro** do corpo do loop (indentação/chaves), e não logo depois dele? Heurísticas por distância de linha geram falsos positivos.
- Se possível, **meça**: conte as queries executadas numa requisição (listener do ORM, log do driver).

**Exemplo**
```python
for row in pedidos:
    cursor2.execute("SELECT * FROM itens_pedido WHERE pedido_id = ?", ...)   # +1 por pedido
    for item in itens:
        cursor3.execute("SELECT nome FROM produtos WHERE id = ?", ...)       # +1 por item
```
**Correção:** playbook → *PT-10 JOIN / eager loading / agregação*.

---

<a id="ap-11"></a>
## AP-11 · Código duplicado · MEDIUM

**Princípio:** DRY.
**O que é:** o mesmo bloco de validação, regra ou serialização copiado em vários lugares, ou uma função que já existe e não é reutilizada.

**Sinais de detecção**
- Mesmas listas literais repetidas (`['pending', 'in_progress', ...]`).
- Blocos `if "campo" not in dados: return 400` idênticos em create e update.
- Mesma condição de negócio (`due_date < now and status not in ...`) em vários arquivos.
- Método existente (ex.: `is_overdue()`) que **nunca é chamado**, enquanto a lógica é reimplementada.
- Serialização manual campo a campo repetida (dict montado igual em 2+ funções).

**Como confirmar**
- Os trechos são equivalentes em comportamento? Liste todas as ocorrências com linha.

**Exemplo**
```python
if t.due_date < datetime.utcnow() and t.status != 'done' and t.status != 'cancelled':   # 6 cópias
```
**Correção:** playbook → *PT-11 Centralizar validação/regra*.

---

<a id="ap-12"></a>
## AP-12 · Erro engolido / sem handler central / validação ausente · MEDIUM

**Princípio:** robustez, fail-fast.
**O que é:** exceções capturadas genericamente, erros de callback ignorados, detalhes internos devolvidos ao cliente, ausência de error handler global e entrada não validada que resulta em 500.

**Sinais de detecção**
- Python: `except:` (sem tipo), `except Exception as e: return jsonify({"erro": str(e)}), 500` repetido em cada função.
- JS: callbacks `(err, x) =>` onde `err` nunca é testado; ausência de middleware `(err, req, res, next)`.
- Ausência de `@app.errorhandler` / `register_error_handler` / middleware de erro.
- Conversões sem proteção (`int(request.args[...])`, comparação `priority < 1` com valor vindo do JSON) e campos obrigatórios não checados (senha opcional, e-mail sem formato).

**Como confirmar**
- Quando possível, **prove** enviando uma entrada inválida (ex.: `?priority=abc`) e observando o 500.
- Conte as ocorrências de `except` genérico.

**Exemplo**
```js
this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
  let enrPending = enrollments.length;   // se err, enrollments é undefined → crash
```
**Correção:** playbook → *PT-12 Error handler centralizado + validação na borda*.

---

<a id="ap-13"></a>
## AP-13 · Uso de API deprecated · MEDIUM

**Princípio:** manutenibilidade. A API vai parar de funcionar numa versão futura.
**O que é:** chamadas marcadas como obsoletas pela linguagem, pelo framework ou pela biblioteca. **Sempre recomende o equivalente moderno.**

**Como detectar**
1. Leia as versões instaladas/declaradas (`requirements.txt`, `package.json`, lockfiles). A depreciação depende da versão.
2. Busque os padrões da tabela abaixo.
3. **Melhor evidência:** execute a aplicação com warnings visíveis (`python -W default`, `PYTHONWARNINGS=default`, `node --trace-deprecation`) e cite a mensagem emitida. Como executar o app pode criar arquivos (ex.: banco SQLite), essa prova é feita no **baseline da Fase 3**. Na Fase 2, a detecção é estática (versão + padrão no código).

**Como confirmar**
- A versão em uso já marca a API como deprecated/legacy? Se a API é apenas "estilo antigo" mas **não** deprecated (ex.: callbacks do `sqlite3` no Node), **não** reporte como AP-13. Se relevante, trate como AP-09 ou AP-14.

### Tabela: API deprecated → equivalente moderno

**Python / Flask / SQLAlchemy**
| Deprecated / legado | Desde | Use |
|---|---|---|
| `datetime.utcnow()` | Python 3.12 | `datetime.now(timezone.utc)` |
| `datetime.utcfromtimestamp(ts)` | Python 3.12 | `datetime.fromtimestamp(ts, timezone.utc)` |
| `Model.query.get(id)` / `session.query(M).get(id)` | SQLAlchemy 2.0 (`LegacyAPIWarning`) | `db.session.get(Model, id)` |
| `Model.query.get_or_404(id)` | Flask-SQLAlchemy 3.x (legado) | `db.get_or_404(Model, id)` |
| `engine.execute(...)` / `session.execute("SQL string")` | SQLAlchemy 2.0 (removido) | `with engine.connect() as c: c.execute(text(...))` |
| `from sqlalchemy.ext.declarative import declarative_base` | SQLAlchemy 2.0 | `from sqlalchemy.orm import DeclarativeBase` |
| `@app.before_first_request` | Flask 2.3 (removido) | executar no factory `create_app()` |
| `flask.json.JSONEncoder` / `app.json_encoder` | Flask 2.3 (removido) | `app.json = CustomJSONProvider(app)` |
| `from werkzeug.urls import url_quote` | Werkzeug 3.0 (removido) | `urllib.parse.quote` |
| `import imp`, `distutils`, `asynchat`, `asyncore` | Python 3.12 (removidos) | `importlib`, `setuptools`/`packaging`, `asyncio` |
| `collections.Mapping` etc. | Python 3.10 (removido) | `collections.abc.Mapping` |
| `asyncio.get_event_loop()` fora de loop | Python 3.12 | `asyncio.run()` / `asyncio.get_running_loop()` |

**Node.js / Express**
| Deprecated / legado | Desde | Use |
|---|---|---|
| `new Buffer(x)` | Node 6 (DEP0005) | `Buffer.from(x)` / `Buffer.alloc(n)` |
| `url.parse(str)` | Node 11 (DEP0169, legado) | `new URL(str)` |
| `fs.exists(path, cb)` | Node 1 (DEP0034) | `fs.existsSync` / `fs.promises.access` |
| `util.isArray`, `util.isString`... | Node 4-22 (DEP0044+) | `Array.isArray`, `typeof x === 'string'` |
| `crypto.createCipher(alg, pwd)` | Node 10 (removido no 22) | `crypto.createCipheriv(alg, key, iv)` |
| `querystring` | legado | `URLSearchParams` |
| `String.prototype.substr` | ECMAScript Annex B | `slice` / `substring` |
| pacote `body-parser` separado para JSON | Express 4.16+ | `express.json()` / `express.urlencoded()` |
| `req.param(name)` | Express 4 (removido no 5) | `req.params` / `req.query` / `req.body` |
| `res.send(status)` com número / `res.json(status, obj)` | Express 4 | `res.sendStatus(n)` / `res.status(n).json(obj)` |
| `app.del(...)` | Express 4 | `app.delete(...)` |
| pacote `request` | deprecated (2020) | `fetch` nativo (Node 18+) / `undici` |

**Exemplo**
```python
user = User.query.get(user_id)          # LegacyAPIWarning (SQLAlchemy 2.x)
if t.due_date < datetime.utcnow():      # DeprecationWarning (Python 3.12+)
```
**Correção:** playbook → *PT-13 Substituir API deprecated*.

---

<a id="ap-14"></a>
## AP-14 · Magic numbers, nomes ruins, código morto, logging inadequado · LOW

**Princípio:** Clean Code (legibilidade).
**O que é:** problemas que não quebram nada hoje, mas tornam a leitura e a manutenção mais caras.

**Sinais de detecção**
- **Magic numbers/strings:** literais numéricos em condições de negócio (`> 10000`, `* 0.05`, `startsWith("4")`), listas de domínio inline.
- **Nomes ruins:** variáveis de 1-3 letras fora de loops curtos (`u, e, p, cc, cid`), campos de contrato abreviados (`usr`, `eml`).
- **Código morto:** funções, classes, constantes ou módulos nunca referenciados; imports sem uso. Para verificar, busque o nome em todo o projeto (fora da definição e fora de dependências).
- **Logging inadequado:** `print`/`console.log` como log de aplicação; `debug=True` fixo no código.
- **Verbosidade:** `if cond: return True else: return False`; `type(x) == list` em vez de `isinstance`.

**Como confirmar**
- Código morto: o símbolo aparece em algum import/chamada fora do próprio arquivo? Frameworks com registro dinâmico (decorators de rota, entry points) contam como uso.
- Agrupe por categoria (um finding para magic numbers, um para código morto, etc.) com contagem.

**Exemplo**
```python
if faturamento > 10000: desconto = faturamento * 0.1
elif faturamento > 5000: desconto = faturamento * 0.05
```
**Correção:** playbook → *PT-14 Constantes nomeadas, nomes claros, remoção de código morto e logging*.
