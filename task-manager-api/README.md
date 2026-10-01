# task-manager-api

API de Task Manager em Python/Flask usada como entrada do desafio `refactor-arch`. Organizada em camadas MVC: `routes/` (view: URL → controller), `controllers/` (fluxo e validação de entrada), `models/` (ORM e regras de domínio), `middlewares/` (erros e autenticação), `config/` (configuração vinda do ambiente) e `utils/` (constantes e funções puras).

## Como rodar

```bash
pip install -r requirements.txt
cp .env.example .env        # opcional: ajuste SECRET_KEY, PORT, FLASK_DEBUG...
python seed.py
python app.py
```

A aplicação sobe em `http://localhost:5000`. O `seed.py` recria o banco SQLite (`instance/tasks.db`) com usuários, categorias e tasks de exemplo. **Rode-o antes do primeiro boot**, caso contrário os endpoints vão retornar listas vazias.

## Variáveis de ambiente

| Variável | Default | Uso |
|---|---|---|
| `SECRET_KEY` | aleatória por boot | Assinatura dos tokens de login. Defina-a para que os tokens sobrevivam a um restart |
| `DATABASE_URL` | `sqlite:///tasks.db` | URI do SQLAlchemy |
| `FLASK_DEBUG` | `false` | Modo debug do Flask |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | Endereço do servidor |
| `TOKEN_MAX_AGE` | `3600` | Validade do token, em segundos |

## Autenticação

`POST /login` devolve um `token` assinado. Envie-o como `Authorization: Bearer <token>` nas rotas protegidas:

- `DELETE /tasks/<id>`: qualquer usuário autenticado;
- `DELETE /users/<id>` e `DELETE /categories/<id>`: somente `admin`;
- `POST /users` com `role` diferente de `user`, e `PUT /users/<id>` com `role` ou `active`: somente `admin`.

Usuário admin do seed: `joao@email.com` / `1234`.

## Exclusão (soft delete)

Os `DELETE` não apagam registros: marcam `deleted`, `deleted_at` e `deleted_by` (quem removeu). Registros removidos somem das leituras de negócio (404 por id), mas continuam nos relatórios (`/reports/*`). Remover um usuário marca também as tasks dele. O e-mail de um usuário removido continua reservado. Bancos criados antes dessas colunas são migrados automaticamente no boot.
