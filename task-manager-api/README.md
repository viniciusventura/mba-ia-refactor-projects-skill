# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Refatorada para MVC em camadas (`routes/` → `controllers/` → `models/`), com config por ambiente, autenticação por token e soft delete.

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env        # opcional: defina SECRET_KEY
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` popula o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo — **rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

## Variáveis de ambiente

| Variável | Default | Uso |
|---|---|---|
| `SECRET_KEY` | aleatória a cada boot | assina os tokens de login |
| `DATABASE_URL` | `sqlite:///tasks.db` | URI do banco |
| `TOKEN_MAX_AGE` | `3600` | validade do token (s) |
| `DEBUG` | `false` | modo debug do Flask |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | bind do servidor |

## Autenticação

`POST /login` devolve `token`. Envie-o em `Authorization: Bearer <token>`.

| Rota | Exige |
|---|---|
| `POST /tasks` | autenticado |
| `PUT/DELETE /tasks/<id>` | admin, manager ou dono da task |
| `GET /users`, `GET /users/<id>`, `GET /users/<id>/tasks`, `GET /reports/*` | autenticado |
| `PUT /users/<id>` | o próprio usuário ou admin (`role`/`active`: só admin) |
| `DELETE /users/<id>`, `POST/PUT/DELETE /categories` | admin |
| `POST /users` | público para `role: user`; outros papéis exigem admin |

## Exclusões

`DELETE` faz soft delete (`deleted`, `deleted_at`, `deleted_by`): o registro some das leituras, mas continua no banco e nos relatórios (`/reports/*`). Remover um usuário marca também as tasks dele. O e-mail de um usuário removido continua ocupado. Bancos antigos recebem as colunas novas automaticamente no boot.
