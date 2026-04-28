# Pedlet Flask + PostgreSQL Render

Sistema estilo mural/Pedlet para cadastrar galerias com até 6 fotos por galeria.
As fotos são salvas diretamente no PostgreSQL em campo BYTEA, então não dependem da pasta local do Render.

## Rodar localmente no Windows

```powershell
cd C:\Users\Micro\Pictures\pedlet_flask
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python app.py
```

Acesse:

```text
http://127.0.0.1:5000
```

Observação: se estiver usando a URL interna do PostgreSQL do Render, ela geralmente só funciona dentro do Render. Para testar no PC, use a External Database URL do Render ou deixe sem DATABASE_URL para testar com SQLite local.

## Configuração no Render

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Environment Variables:

```env
DATABASE_URL=postgresql://pedlet_user:SUA_SENHA@SEU_HOST/pedlet
SECRET_KEY=troque-essa-chave
MAX_UPLOAD_MB=30
PYTHON_VERSION=3.12.8
```

## Rotas de teste

```text
/healthz
```

Verifica se o app Flask está no ar.

```text
/saude
```

Verifica se o PostgreSQL conectou.

## Recursos

- Cadastro de galeria
- Até 6 fotos por galeria
- Nome e classificação por foto
- Categoria e turma
- Busca por título, categoria, turma, nome ou classificação da foto
- Página individual da galeria
- Edição e exclusão
- Visual responsivo para celular
