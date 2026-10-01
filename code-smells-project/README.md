# code-smells-project

API de E-commerce em Python/Flask usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://localhost:5000`. O banco SQLite (`loja.db`) é criado automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas gravadas com hash).

> Se você tem um `loja.db` criado por uma versão anterior (senhas em texto puro), apague-o para que o seed seja refeito.

## Configuração

Toda a configuração vem de variáveis de ambiente (veja `.env.example`). As variáveis não são carregadas de um arquivo `.env` automaticamente; exporte-as no shell:

| Variável | Padrão | Uso |
|---|---|---|
| `SECRET_KEY` | aleatória a cada boot | chave da aplicação |
| `ADMIN_TOKEN` | vazio (rota bloqueada) | `POST /admin/reset-db` exige `Authorization: Bearer <ADMIN_TOKEN>` |
| `FLASK_DEBUG` | `false` | modo debug |
| `HOST` / `PORT` | `0.0.0.0` / `5000` | endereço do servidor |
| `DATABASE_PATH` | `loja.db` | arquivo SQLite |
| `AMBIENTE` | `producao` | valor exibido no `/health` |

## Estrutura

```
app.py              entry point: create_app()
config/settings.py  configuração lida do ambiente
database.py         conexão por requisição, schema e seed
models/             acesso a dados e regras de domínio (produto, usuario, pedido, sistema)
controllers/        fluxo de cada caso de uso e validação de entrada
views/              Blueprints: URL + método → controller
services/           notificações de pedido
middlewares/        tratamento de erros e autenticação de admin
utils/constants.py  constantes de domínio
```
