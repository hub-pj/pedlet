# Pedlet Flask - Galerias com MongoDB

Sistema estilo mural/Padlet para criar galerias com até 6 fotos, nomear/classificar cada foto e salvar tudo no MongoDB Atlas usando GridFS.

## Rodar localmente

```bash
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

## Configurar MongoDB localmente

No `.env`, coloque sua conexão do MongoDB Atlas.

Importante: se a senha tiver o caractere `@`, troque por `%40`.

```env
MONGO_URI=mongodb+srv://USUARIO:SENHA@pedlet.utqpcwm.mongodb.net/?retryWrites=true&w=majority&appName=pedlet
MONGO_DB=pedlet
SECRET_KEY=troque-esta-chave
MAX_UPLOAD_MB=30
```

## Subir no Render

O projeto já vem com:

- `gunicorn` no `requirements.txt`
- `render.yaml`
- `.python-version`
- `Procfile`
- rota de saúde `/saude`

Veja o passo a passo no arquivo:

```text
README_RENDER.md
```

## O que o sistema faz

- Cria galeria com título, categoria, turma e descrição.
- Permite até 6 fotos por galeria.
- Cada foto pode receber um nome/classificação.
- Salva fotos no MongoDB usando GridFS.
- Lista todas as galerias em formato de mural.
- Busca por título, turma, categoria, descrição ou nome da foto.
- Filtra por categoria.
- Abre página individual de cada galeria.
- Exclui galeria e as fotos salvas no banco.

## Segurança

Não coloque a conexão real do MongoDB no código. Use variáveis de ambiente no Render.
