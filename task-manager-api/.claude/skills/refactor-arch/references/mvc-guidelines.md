# Guidelines de Arquitetura: MVC alvo

Referência da **Fase 3**. Define **para onde** o código vai: as camadas, o que cada uma pode e não pode fazer, a direção das dependências e a estrutura de pastas por stack. Os padrões de transformação (o **como**) estão em `refactoring-playbook.md`.

---

## 1. MVC aplicado a uma API

Numa API REST não há templates HTML. As três camadas ficam assim:

| Camada | Papel numa API | Pergunta que responde |
|---|---|---|
| **Model** | Dados e regras de domínio: acesso ao banco (SQL/ORM), entidades, cálculos e invariantes do negócio | *"O que é verdade no domínio e como persisto isso?"* |
| **View** | Borda HTTP: rotas (URL + método → controller) e representação da saída (serialização) | *"Qual URL chama o quê, e como o dado sai?"* |
| **Controller** | Fluxo do caso de uso: lê a requisição, valida a entrada, chama models/services e decide a resposta | *"O que acontece quando esta requisição chega?"* |

Camadas de apoio (não substituem as três principais):

| Apoio | Papel |
|---|---|
| **Config** | Única fonte de configuração, lida do ambiente (PT-02) |
| **Database** | Criação/fechamento de conexão, schema e seed |
| **Services** | Integrações externas: e-mail, SMS, pagamento, APIs de terceiros |
| **Middlewares** | Preocupações transversais: tratamento de erro, autenticação, CORS, logging de requisição |
| **Utils** | Funções puras e constantes compartilhadas (sem estado, sem I/O) |
| **Entry point** | Composition root: cria o app, injeta dependências, registra rotas e middlewares, sobe o servidor |

---

## 2. Responsabilidades: pode × não pode

### Model
| ✅ Pode | ❌ Não pode |
|---|---|
| Executar SQL parametrizado / usar ORM | Importar `request`, `req`, `res`, `jsonify` ou qualquer objeto HTTP |
| Definir entidades, colunas, relacionamentos | Devolver status HTTP ou respostas |
| Implementar regras de domínio (`is_overdue()`, `calcular_desconto()`) | Ler configuração de rota ou headers |
| Serializar a si mesmo **sem** campos sensíveis (`to_dict`) | Chamar serviços externos (e-mail, pagamento) |
| Receber a conexão/sessão como parâmetro | Criar a própria conexão global (AP-08) |

### Controller
| ✅ Pode | ❌ Não pode |
|---|---|
| Ler e validar entrada (body, query, params) | Conter SQL ou montar queries |
| Chamar models e services; controlar a transação do caso de uso | Duplicar regra de domínio que pertence ao model |
| Levantar erros tipados (`NotFoundError`, `ValidationError`) | Ter `try/except` genérico devolvendo `str(e)` (vai para o middleware) |
| Montar a resposta (corpo + status) no formato do contrato | Registrar rotas |
| Registrar log de negócio (via `logging`, não `print`) | Guardar estado entre requisições |

### View (rotas)
| ✅ Pode | ❌ Não pode |
|---|---|
| Mapear URL + método → função do controller | Conter lógica de negócio, validação ou SQL |
| Aplicar middlewares/decorators por rota (auth) | Acessar o banco |
| Agrupar rotas por domínio (Blueprint, Router) | Ter corpo de handler com mais que a delegação |

### Services
| ✅ Pode | ❌ Não pode |
|---|---|
| Encapsular uma integração externa (envio, cobrança) | Conhecer HTTP da própria API (request/response) |
| Receber configuração/credenciais injetadas | Ter credencial hardcoded |

### Middlewares
| ✅ Pode | ❌ Não pode |
|---|---|
| Converter exceções em respostas no formato do projeto | Conter regra de negócio |
| Autenticar/autorizar e anexar o usuário ao contexto | Engolir erros sem log |

---

## 3. Direção das dependências

```
Entry point (composition root)
   │ cria e injeta
   ▼
View (rotas) ──▶ Controller ──▶ Model ──▶ Database
                     │
                     └──────▶ Service ──▶ (sistema externo)

Middlewares: registrados pelo entry point, envolvem as rotas
Config/Utils: podem ser importados por qualquer camada
```

Regras:
1. Dependências apontam **para dentro**: View → Controller → Model. Nunca o contrário (um model não importa controller; um controller não importa view).
2. Model **não conhece HTTP**. Deveria funcionar igual se chamado por um script ou uma fila.
3. Só o **entry point** conhece todas as peças.
4. Evite import circular: o objeto de banco (`db = SQLAlchemy()`, helper de conexão) fica num módulo próprio importado por models e entry point.

---

## 4. Estrutura alvo por stack

### Python / Flask

Pacotes na **raiz do projeto**, para manter `python app.py` e scripts auxiliares (`seed.py`) funcionando sem mudar o `PYTHONPATH`:

```
<projeto>/
├── app.py                      # entry point: create_app() + app = create_app() + if __name__ == "__main__"
├── config/
│   ├── __init__.py
│   └── settings.py             # Settings lidas do ambiente
├── database.py                 # conexão por requisição (sqlite3 + flask.g) OU db = SQLAlchemy(); schema/seed
├── models/
│   ├── __init__.py
│   └── <dominio>_model.py      # um arquivo por domínio (produto, usuario, pedido...)
├── controllers/
│   ├── __init__.py
│   └── <dominio>_controller.py
├── views/                      # ou routes/, se o projeto já usa esse nome (ver §6)
│   ├── __init__.py             # register_blueprints(app)
│   └── <dominio>_routes.py     # Blueprint por domínio
├── services/                   # somente se houver integração externa
├── middlewares/
│   ├── __init__.py
│   ├── error_handler.py        # AppError + register_error_handlers
│   └── auth.py                 # somente se houver rotas protegidas
├── utils/                      # constants.py, time.py (utc_now)...
├── requirements.txt
└── .env.example
```

Entry point de referência:
```python
# app.py
import logging
from flask import Flask
from flask_cors import CORS
from config.settings import Settings
import database
from views import register_blueprints
from middlewares.error_handler import register_error_handlers

def create_app(settings=Settings):
    app = Flask(__name__)
    app.config.from_object(settings)
    CORS(app)
    database.init_app(app)
    register_blueprints(app)
    register_error_handlers(app)
    return app

app = create_app()                       # mantém "from app import app" funcionando

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host=Settings.HOST, port=Settings.PORT, debug=Settings.DEBUG)
```

Rotas de referência (a View só delega):
```python
# views/produto_routes.py
from flask import Blueprint
from controllers import produto_controller

produto_bp = Blueprint("produtos", __name__)
produto_bp.get("/produtos")(produto_controller.listar_produtos)
produto_bp.get("/produtos/busca")(produto_controller.buscar_produtos)
produto_bp.get("/produtos/<int:id>")(produto_controller.buscar_produto)
produto_bp.post("/produtos")(produto_controller.criar_produto)
```

### Node.js / Express

Tudo dentro de `src/`, mantendo o `main`/`start` do `package.json`:

```
<projeto>/
├── package.json                 # "start": "node src/app.js" (inalterado)
├── .env.example
└── src/
    ├── app.js                   # composition root
    ├── config/index.js
    ├── database/
    │   ├── connection.js        # abre conexão + helpers promisificados + transaction()
    │   └── schema.js            # CREATE TABLE + seed
    ├── models/<entidade>Model.js
    ├── controllers/<dominio>Controller.js
    ├── routes/index.js          # View: Router por domínio
    ├── services/<integracao>Service.js
    ├── middlewares/
    │   ├── errorHandler.js
    │   └── auth.js
    └── utils/
```

Convenções Node: CommonJS se o projeto usa `require` (não migrar para ESM); controllers como *factory* que recebe dependências (`module.exports = ({ db }) => ({ ... })`); handlers async envolvidos por `asyncHandler` para que erros cheguem ao middleware (Express 4).

---

## 5. Nomenclatura

- **Idioma:** siga o do projeto. Domínio em português → `produto_model.py`, `criar_pedido`. Domínio em inglês → `task_controller.py`, `create_task`.
- **Arquivos:** Python em `snake_case` com sufixo da camada (`_model`, `_controller`, `_routes`); JS em `camelCase` com sufixo (`userModel.js`, `checkoutController.js`).
- **Um domínio por arquivo** em cada camada. Um arquivo que atende vários domínios é o que levou ao AP-06.
- **Nomes de funções do controller** podem manter os nomes originais dos handlers. Isso facilita comparar antes/depois e manter os `endpoint` names do Flask.

---

## 6. Adaptação ao nível de organização do projeto

A Fase 1 classifica a arquitetura atual. A Fase 3 escolhe a estratégia:

### A) Monolito / God Class (tudo em 1-4 arquivos, sem camadas)
Decomposição completa (PT-06):
1. Mapear cada função/rota do(s) arquivo(s) para a camada de destino (tabela *origem → destino*).
2. Criar a estrutura da §4 e mover código **por domínio**.
3. Reduzir o arquivo original a entry point. Arquivos antigos esvaziados (ex.: `controllers.py`, `models.py` na raiz) são **removidos**, para não coexistirem com os pacotes novos de mesmo nome.

### B) Parcialmente em camadas (pastas existem, responsabilidades misturadas)
Evolução, não reescrita:
1. **Mantenha o que está correto:** models ORM, Blueprints, nomes de pastas existentes. Se a camada de View já se chama `routes/`, mantenha `routes/`. O papel é o mesmo de `views/`; documente a equivalência no resumo.
2. **Crie a camada que falta.** Tipicamente `controllers/`: o corpo das rotas vai para o controller, e o blueprint fica só com a delegação.
3. **Mova regra de domínio para o model** e **reutilize** métodos já existentes (ex.: `Task.is_overdue()`).
4. **Reorganize rotas no domínio errado** (ex.: CRUD de categorias dentro de `report_routes.py` → `category_routes.py`) **sem mudar as URLs**.
5. **Conecte ou remova** camadas mortas (`services/` nunca importado, `utils` sem uso).
6. Adicione o que falta de infraestrutura: `config/`, `middlewares/error_handler.py`, app factory.

### C) Já adequado
Se a estrutura já segue esta guideline, a Fase 3 se limita aos findings de código (segurança, performance, deprecated, legibilidade). Não mova arquivos só por mover.

---

## 7. Checklist de conformidade (usado na validação da Fase 3)

- [ ] Existe módulo de **config** e nenhum segredo literal no código
- [ ] **Models** por domínio; nenhum model importa objetos HTTP
- [ ] **Views/rotas** apenas delegam (sem SQL, sem regra, sem validação)
- [ ] **Controllers** concentram o fluxo; nenhum controller contém SQL
- [ ] **Error handling centralizado** (um handler/middleware); nenhum `except` genérico devolvendo `str(e)`
- [ ] **Entry point** claro, que só compõe as peças (app factory / composition root)
- [ ] Integrações externas isoladas em **services**
- [ ] Nenhum estado global mutável compartilhado entre requisições
- [ ] Comandos originais de execução continuam funcionando (`python app.py`, `npm start`, scripts auxiliares)
