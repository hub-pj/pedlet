# Pedlet Flask + MongoDB Atlas pronto para Render

Este projeto já está configurado para Render com Flask, Gunicorn e MongoDB Atlas/GridFS.
As imagens ficam dentro do MongoDB, então não somem quando o Render reiniciar.

## 1. Arquivos importantes

Suba estes arquivos para o GitHub:

- `app.py`
- `requirements.txt`
- `render.yaml`
- `.python-version`
- `Procfile`
- `templates/`
- `static/`

Não envie o arquivo `.env` com senha real para o GitHub.

## 2. Configuração no Render

No Render, crie um **Web Service** conectado ao seu GitHub.

Build Command:

```bash
pip install -r requirements.txt
```

Start Command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

Health Check Path:

```text
/healthz
```

## 3. Variáveis de ambiente

Em **Environment**, coloque:

```env
MONGO_URI=mongodb+srv://bicudo:bicudo2026%40@pedlet.utqpcwm.mongodb.net/?retryWrites=true&w=majority&appName=pedlet
MONGO_DB=pedlet
MAX_UPLOAD_MB=30
PYTHON_VERSION=3.12.8
SECRET_KEY=coloque-uma-chave-grande-aqui
```

Atenção: se sua senha real for `bicudo2026@`, dentro da URI ela precisa ficar `bicudo2026%40`.

Errado:

```text
mongodb+srv://bicudo:bicudo2026@@pedlet.utqpcwm.mongodb.net/
```

Certo:

```text
mongodb+srv://bicudo:bicudo2026%40@pedlet.utqpcwm.mongodb.net/
```

## 4. Liberar o MongoDB Atlas

No MongoDB Atlas:

1. Vá em **Database Access** e confira se o usuário `bicudo` existe.
2. Clique em editar usuário e redefina a senha, se necessário.
3. Vá em **Network Access**.
4. Clique em **Add IP Address**.
5. Para testar no Render, use:

```text
0.0.0.0/0
```

6. Salve e aguarde alguns minutos.

## 5. Testes

No navegador, abra:

```text
https://SEU-SITE.onrender.com/healthz
```

Deve aparecer:

```json
{"app":"pedlet","status":"ok"}
```

Depois teste o MongoDB:

```text
https://SEU-SITE.onrender.com/saude
```

Deve aparecer:

```json
{"banco":"pedlet","mongodb":"conectado","status":"ok"}
```

## 6. Rodar localmente no Windows

Abra o PowerShell dentro da pasta `pedlet_flask` e use:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
copy .env.example .env
python app.py
```

Se a pasta `.venv` já existir e der erro de cópia, apague a pasta `.venv` e rode de novo:

```powershell
rmdir /s /q .venv
python -m venv .venv
```

## 7. Observações importantes

- Não digite `Build Command:` no PowerShell. Isso é só o nome do campo no Render.
- Não digite `https://seu-site.onrender.com/saude` direto no PowerShell. Abra no navegador ou use:

```powershell
start https://SEU-SITE.onrender.com/saude
```

- Se aparecer `bad auth : Authentication failed`, o problema está no usuário, senha ou URI do MongoDB Atlas.
