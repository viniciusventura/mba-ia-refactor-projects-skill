# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo. Bancos antigos são migrados no boot (colunas de soft delete em `produtos`, senhas em texto puro convertidas para hash).

## Configuração

Variáveis de ambiente (veja `.env.example`):

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | aleatória por processo | assina os tokens de login; defina em produção |
| `FLASK_DEBUG` | `false` | modo debug do Flask |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | endereço do servidor |
| `DB_PATH` | `loja.db` | arquivo do banco SQLite |
| `TOKEN_MAX_AGE` | `3600` | validade do token, em segundos |
| `APP_ENV` | `producao` | valor de `ambiente` no `/health` |

## Autenticação

`POST /login` devolve `dados.token`. Envie-o nas rotas protegidas como `Authorization: Bearer <token>`.

| Acesso | Rotas |
|---|---|
| Público | `GET /`, `GET /health`, `GET /produtos`, `GET /produtos/busca`, `GET /produtos/<id>`, `POST /usuarios`, `POST /login` |
| Admin | `POST /produtos`, `PUT /produtos/<id>`, `DELETE /produtos/<id>`, `GET /usuarios`, `GET /pedidos`, `PUT /pedidos/<id>/status`, `GET /relatorios/vendas`, `POST /admin/reset-db` |
| Próprio usuário ou admin | `GET /usuarios/<id>`, `GET /pedidos/usuario/<id>`, `POST /pedidos` (`usuario_id` do body) |

Sem token: 401. Sem o papel ou sem ser o dono do recurso: 403. Usuários de exemplo: `admin@loja.com` / `admin123` (admin), `joao@email.com` / `123456` (cliente).

`DELETE /produtos/<id>` é soft delete: o produto some do catálogo, mas continua no banco (`removido`, `removido_em`, `removido_por`) e no histórico de pedidos.

## Estrutura

```
app.py            # entry point: create_app()
config/           # Settings lidas do ambiente
database.py       # conexão por requisição, schema, migrações e seed
models/           # SQL parametrizado e regras de domínio, um arquivo por domínio
controllers/      # fluxo de cada caso de uso
views/            # Blueprints: URL -> controller
services/         # notificações (simuladas em log)
middlewares/      # tratamento de erro e autenticação
utils/            # constantes
```
