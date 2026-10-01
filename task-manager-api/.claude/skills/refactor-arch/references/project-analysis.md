# Análise de Projeto: heurísticas da Fase 1

Referência da **Fase 1 (Análise)**. Objetivo: entender o projeto **sem modificar nada** e produzir (a) o resumo impresso ao usuário e (b) o **inventário de endpoints**, que é a base da validação da Fase 3.

Siga os passos na ordem. Cada passo diz **onde olhar** e **o que concluir**. Aplique o escopo de busca do catálogo: ignore `.venv/`, `venv/`, `node_modules/`, `__pycache__/`, `dist/`, `build/`, `.git/`, lockfiles, `*.db` e `.claude/`.

---

## Passo 1: Linguagem

Olhe primeiro os **manifestos** (mais confiáveis) e depois as **extensões** dos arquivos-fonte.

| Manifesto encontrado | Linguagem |
|---|---|
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile` | Python |
| `package.json` (+ `tsconfig.json` → TypeScript) | JavaScript / TypeScript |
| `pom.xml`, `build.gradle` | Java / Kotlin |
| `go.mod` | Go |
| `Gemfile` | Ruby |
| `composer.json` | PHP |
| `*.csproj` | C# |

Se houver mais de uma, a linguagem principal é a que tem mais linhas de código-fonte. Informe a versão do runtime se estiver declarada (`python_requires`, `engines.node`, `.nvmrc`, `.python-version`).

---

## Passo 2: Framework e versão

1. Leia as dependências diretas do manifesto.
2. Confirme pelo uso no código (imports + criação do app).

| Framework | Sinal no manifesto | Sinal no código |
|---|---|---|
| Flask | `flask` | `Flask(__name__)`, `@app.route`, `Blueprint(`, `add_url_rule` |
| FastAPI | `fastapi` | `FastAPI()`, `@app.get`, `APIRouter` |
| Django | `django` | `manage.py`, `urls.py`, `settings.py` |
| Express | `express` | `require('express')`, `express()`, `app.get/post`, `Router()` |
| Fastify | `fastify` | `fastify()`, `fastify.get` |
| NestJS | `@nestjs/core` | `@Controller`, `@Module` |
| Koa | `koa` | `new Koa()` |
| Spring Boot | `spring-boot-starter-web` | `@RestController` |

**Versão:** use a versão fixada (`flask==3.1.1`). Se o manifesto declara um *range* (`"express": "^4.18.2"`), informe o range e, se instalado, a versão real (`node_modules/express/package.json`, `pip show flask`). A versão importa para o AP-13 (deprecated).

---

## Passo 3: Dependências

Liste as **dependências diretas** (não as transitivas do lockfile), separando:
- **Framework/web:** flask, express, flask-cors...
- **Dados:** sqlite3, flask-sqlalchemy, pg, mongoose...
- **Outras:** marshmallow, requests, python-dotenv...

Anote dependências **declaradas e nunca importadas**. Elas são candidatas a AP-14 (ex.: `marshmallow` no manifesto sem nenhum `import marshmallow`).

---

## Passo 4: Banco de dados

| Sinal | Conclusão |
|---|---|
| `import sqlite3`, `sqlite3.connect(` | SQLite via driver cru (SQL manual) |
| `flask_sqlalchemy`, `SQLAlchemy(`, `db.Model` | ORM SQLAlchemy |
| `require('sqlite3')`, `new sqlite3.Database(` | SQLite no Node (API de callbacks) |
| `pg`, `mysql2`, `psycopg2`, `pymysql` | PostgreSQL / MySQL |
| `mongoose`, `pymongo` | MongoDB |
| `prisma`, `sequelize`, `typeorm` | ORM Node |

Registre também:
- **Onde fica:** arquivo (`loja.db`, `sqlite:///tasks.db`) ou memória (`:memory:`, que perde os dados a cada boot).
- **Tabelas/entidades:** `CREATE TABLE <nome>`, `__tablename__ = '<nome>'`, classes `db.Model`, schemas do ORM.
- **Como os dados iniciais são criados:** seed no boot, script separado (`seed.py`) ou nenhum. Isso define o passo de preparação da validação.

---

## Passo 5: Entry point e execução

Descubra **como o projeto roda hoje**. A refatoração tem que manter isso funcionando.

| Onde olhar | O que extrair |
|---|---|
| `README.md` do projeto | Comandos de instalação, seed e execução |
| `package.json` → `scripts.start`, `main` | Comando Node e arquivo de entrada |
| `if __name__ == "__main__":` + `app.run(` | Entry point Python, host, porta, debug |
| `app.listen(` / `config.port` | Porta Node |
| Scripts auxiliares que importam o app | Ex.: `seed.py` com `from app import app, db`. Esses imports precisam continuar válidos |

Resultado esperado: *comando de execução*, *porta*, *pré-requisitos* (ex.: "rodar `python seed.py` antes").

---

## Passo 6: Inventário de endpoints

Liste **todas** as rotas: método, caminho, handler e `arquivo:linha`.

| Framework | Padrões de rota |
|---|---|
| Flask | `@app.route("/x", methods=[...])`, `@bp.route(...)`, `@bp.get/post/put/delete(...)`, `app.add_url_rule("/x", "nome", func, methods=[...])` |
| Express | `app.get/post/put/patch/delete('/x', ...)`, `router.<método>(...)`, `app.use('/prefixo', router)` |
| FastAPI | `@app.get("/x")`, `@router.post(...)`, `include_router(prefix=...)` |

Cuidados:
- **Prefixos:** some o prefixo do Blueprint/Router (`url_prefix=`, `app.use('/api', router)`) ao caminho.
- **Método padrão:** no Flask, `@route` sem `methods` é `GET`.
- **Rotas definidas fora do módulo de rotas** (no entry point, como `/health` ou `/`) também entram.
- **Exemplos de requisição:** arquivos `*.http`, `*.rest`, coleções Postman e o README trazem payloads válidos. Use-os para montar as chamadas de validação.

Formato do inventário (reutilizado na Fase 3):
```
| Método | Rota                  | Handler                        | Local              |
|--------|-----------------------|--------------------------------|--------------------|
| GET    | /produtos             | controllers.listar_produtos    | app.py:11          |
| POST   | /api/checkout         | AppManager.setupRoutes (anon.) | src/AppManager.js:28 |
```
Marque rotas **destrutivas** (ex.: reset do banco, delete em massa). Na validação, elas só são chamadas por último ou num banco descartável.

---

## Passo 7: Mapa da arquitetura atual

1. Liste os arquivos-fonte com a contagem de linhas.
2. Para cada arquivo, anote **quais responsabilidades** ele contém:

| Responsabilidade | Sinais |
|---|---|
| Config | `app.config[...] =`, objeto `config`, `os.environ`, `process.env` |
| Conexão/schema | `connect(`, `CREATE TABLE`, `db.create_all()`, seed |
| Acesso a dados | SQL, `cursor.execute`, `Model.query`, `db.session`, `db.get/all/run` |
| Regra de negócio | cálculos, limiares, decisões de domínio |
| Validação de entrada | checagem de campos do body/query |
| Roteamento/HTTP | definição de rotas, `request`, `req/res`, `jsonify` |
| Integração externa | SMTP, gateway, HTTP client |
| Tratamento de erro | `try/except`, middlewares de erro |

3. Classifique a arquitetura (isso define a estratégia da Fase 3; veja `mvc-guidelines.md` §6):

| Classificação | Critério |
|---|---|
| **A) Monolítica / God Class** | Poucos arquivos com 3+ responsabilidades de camadas diferentes cada; sem pastas de camada, ou com "camadas" só no nome do arquivo |
| **B) Parcialmente em camadas** | Existem pastas `models/`, `routes/`, `services/`..., mas rotas contêm SQL/regra, faltam camadas (ex.: controllers) ou existem camadas não usadas |
| **C) Em camadas** | Cada arquivo tem uma responsabilidade coerente com a sua pasta |

Descreva a classificação numa frase com evidência. Ex.: *"Monolítica: tudo em 4 arquivos; `models.py` concentra SQL de 4 domínios e regra de desconto."*

**Atenção:** nomes de arquivo não provam arquitetura. Um `controllers.py` que acessa o banco direto não é um controller MVC.

---

## Passo 8: Domínio da aplicação

Deduza o domínio de negócio a partir de: nomes das **tabelas/entidades**, **prefixos das rotas**, README e mensagens de texto. Descreva numa linha, com as entidades principais.

Exemplos: *"E-commerce API (produtos, pedidos, usuários)"*, *"LMS com checkout (cursos, matrículas, pagamentos)"*, *"Task Manager (tarefas, usuários, categorias, relatórios)"*.

---

## Saída da Fase 1

Imprima exatamente neste formato (valores alinhados), e depois o inventário de endpoints:

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <linguagem + versão do runtime, se declarada>
Framework:     <framework + versão>
Dependencies:  <dependências diretas relevantes, separadas por vírgula>
Database:      <engine + driver/ORM + local (arquivo/memória)>
Domain:        <domínio + entidades principais>
Architecture:  <classificação A/B/C + frase de evidência>
Entry point:   <arquivo + comando de execução + porta>
Source files:  <N files analyzed | ~L lines>
DB tables:     <tabelas separadas por vírgula>
Endpoints:     <N endpoints (lista abaixo)>
================================
```

Regras:
- **Source files** conta só código-fonte da aplicação (sem manifestos, lockfiles, README, `.http`, dependências). Scripts auxiliares (seed) entram, e isso deve ser dito.
- Não invente: se um item não pode ser determinado, escreva `não identificado` e o motivo.
- Nenhum arquivo é criado ou alterado nesta fase.
