import os
from datetime import datetime, timezone

import certifi
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import (
    Flask,
    Response,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from gridfs import GridFS
from pymongo import MongoClient, DESCENDING
from werkzeug.utils import secure_filename

load_dotenv()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_PHOTOS_PER_GALLERY = 6


def create_app():
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "troque-esta-chave-em-producao")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "30")) * 1024 * 1024
    app.config["JSON_AS_ASCII"] = False

    mongo_uri = os.getenv("MONGO_URI", "").strip()
    if not mongo_uri:
        # No Render é melhor o app subir e mostrar o erro em /saude,
        # em vez de quebrar durante a inicialização.
        mongo_uri = "mongodb://localhost:27017"

    db_name = os.getenv("MONGO_DB", "pedlet").strip() or "pedlet"

    client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=8000,
        connectTimeoutMS=8000,
        socketTimeoutMS=8000,
        tlsCAFile=certifi.where(),
    )
    db = client[db_name]
    fs = GridFS(db)
    galerias = db["galerias"]
    categorias = db["categorias"]
    indexes_ready = False

    def allowed_file(filename: str) -> bool:
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def ensure_indexes():
        """Cria índices apenas quando o MongoDB estiver autenticado corretamente."""
        nonlocal indexes_ready
        if indexes_ready:
            return True, None
        try:
            client.admin.command("ping")
            galerias.create_index([("created_at", DESCENDING)])
            galerias.create_index([("titulo", "text"), ("categoria", "text"), ("turma", "text")])
            categorias.create_index("nome", unique=True)
            indexes_ready = True
            return True, None
        except Exception as exc:
            return False, str(exc)

    def get_categories():
        ok, erro = ensure_indexes()
        if not ok:
            return []
        try:
            nomes = [c.get("nome") for c in categorias.find().sort("nome", 1)]
            return [n for n in nomes if n]
        except Exception:
            return []

    def parse_object_id(value: str):
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            abort(404)

    def render_db_error(erro: str):
        return render_template("erro_banco.html", erro=erro), 500

    @app.context_processor
    def inject_globals():
        return {
            "max_photos": MAX_PHOTOS_PER_GALLERY,
            "ano_atual": datetime.now().year,
        }

    @app.route("/healthz")
    def healthz():
        # Usado pelo Render para saber se o Flask subiu.
        # Não testa MongoDB, porque senha errada não deve derrubar o deploy.
        return {"status": "ok", "app": "pedlet"}

    @app.route("/saude")
    def saude():
        try:
            client.admin.command("ping")
            ok, erro = ensure_indexes()
            if not ok:
                return {"status": "erro", "mongodb": "falha ao criar indices", "mensagem": erro}, 500
            return {"status": "ok", "mongodb": "conectado", "banco": db_name}
        except Exception as exc:
            return {"status": "erro", "mongodb": "desconectado", "mensagem": str(exc)}, 500

    @app.route("/")
    def index():
        ok, erro = ensure_indexes()
        if not ok:
            return render_db_error(erro)

        q = request.args.get("q", "").strip()
        categoria = request.args.get("categoria", "").strip()

        filtro = {}
        if categoria:
            filtro["categoria"] = categoria
        if q:
            filtro["$or"] = [
                {"titulo": {"$regex": q, "$options": "i"}},
                {"turma": {"$regex": q, "$options": "i"}},
                {"categoria": {"$regex": q, "$options": "i"}},
                {"descricao": {"$regex": q, "$options": "i"}},
                {"fotos.nome": {"$regex": q, "$options": "i"}},
            ]

        try:
            docs = list(galerias.find(filtro).sort("created_at", DESCENDING))
        except Exception as exc:
            return render_db_error(str(exc))

        return render_template(
            "index.html",
            galerias=docs,
            categorias=get_categories(),
            q=q,
            categoria_atual=categoria,
        )

    @app.route("/nova", methods=["GET", "POST"])
    def nova_galeria():
        ok, erro = ensure_indexes()
        if not ok:
            return render_db_error(erro)

        if request.method == "GET":
            return render_template("nova.html", categorias=get_categories())

        titulo = request.form.get("titulo", "").strip()
        categoria = request.form.get("categoria", "").strip()
        nova_categoria = request.form.get("nova_categoria", "").strip()
        turma = request.form.get("turma", "").strip()
        descricao = request.form.get("descricao", "").strip()

        if nova_categoria:
            categoria = nova_categoria

        if not titulo:
            flash("Informe o título da galeria.", "danger")
            return redirect(url_for("nova_galeria"))

        fotos_salvas = []
        arquivos_recebidos = 0
        gridfs_ids_salvos = []

        try:
            for posicao in range(1, MAX_PHOTOS_PER_GALLERY + 1):
                arquivo = request.files.get(f"foto{posicao}")
                nome_foto = request.form.get(f"nome{posicao}", "").strip()

                if not arquivo or not arquivo.filename:
                    continue

                arquivos_recebidos += 1
                if not allowed_file(arquivo.filename):
                    flash(f"Arquivo inválido na foto {posicao}. Use PNG, JPG, JPEG, GIF ou WEBP.", "danger")
                    return redirect(url_for("nova_galeria"))

                filename = secure_filename(arquivo.filename)
                content_type = arquivo.content_type or "application/octet-stream"
                file_id = fs.put(
                    arquivo.stream,
                    filename=filename,
                    content_type=content_type,
                    metadata={
                        "titulo_galeria": titulo,
                        "nome_foto": nome_foto,
                        "posicao": posicao,
                        "created_at": datetime.now(timezone.utc),
                    },
                )
                gridfs_ids_salvos.append(file_id)
                fotos_salvas.append(
                    {
                        "file_id": file_id,
                        "filename": filename,
                        "content_type": content_type,
                        "nome": nome_foto or f"Foto {posicao}",
                        "posicao": posicao,
                    }
                )

            if arquivos_recebidos == 0:
                flash("Adicione pelo menos uma foto.", "danger")
                return redirect(url_for("nova_galeria"))

            doc = {
                "titulo": titulo,
                "categoria": categoria or "Sem categoria",
                "turma": turma,
                "descricao": descricao,
                "fotos": fotos_salvas,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
            resultado = galerias.insert_one(doc)

            if categoria:
                categorias.update_one(
                    {"nome": categoria},
                    {"$setOnInsert": {"nome": categoria, "created_at": datetime.now(timezone.utc)}},
                    upsert=True,
                )
        except Exception as exc:
            # Se falhar depois de subir fotos, tenta limpar para não deixar arquivo solto no GridFS.
            for file_id in gridfs_ids_salvos:
                try:
                    fs.delete(file_id)
                except Exception:
                    pass
            return render_db_error(str(exc))

        flash("Galeria criada com sucesso!", "success")
        return redirect(url_for("ver_galeria", galeria_id=str(resultado.inserted_id)))

    @app.route("/galeria/<galeria_id>")
    def ver_galeria(galeria_id):
        ok, erro = ensure_indexes()
        if not ok:
            return render_db_error(erro)

        oid = parse_object_id(galeria_id)
        galeria = galerias.find_one({"_id": oid})
        if not galeria:
            abort(404)
        return render_template("galeria.html", galeria=galeria)

    @app.route("/galeria/<galeria_id>/excluir", methods=["POST"])
    def excluir_galeria(galeria_id):
        ok, erro = ensure_indexes()
        if not ok:
            return render_db_error(erro)

        oid = parse_object_id(galeria_id)
        galeria = galerias.find_one({"_id": oid})
        if not galeria:
            abort(404)

        for foto in galeria.get("fotos", []):
            try:
                fs.delete(foto["file_id"])
            except Exception:
                pass

        galerias.delete_one({"_id": oid})
        flash("Galeria excluída com sucesso.", "success")
        return redirect(url_for("index"))

    @app.route("/imagem/<file_id>")
    def imagem(file_id):
        oid = parse_object_id(file_id)
        try:
            grid_file = fs.get(oid)
        except Exception:
            abort(404)

        return Response(
            grid_file.read(),
            mimetype=grid_file.content_type or "application/octet-stream",
            headers={"Cache-Control": "public, max-age=86400"},
        )

    @app.errorhandler(413)
    def arquivo_muito_grande(_):
        flash("Arquivo muito grande. Reduza as imagens ou aumente MAX_UPLOAD_MB no .env.", "danger")
        return redirect(url_for("nova_galeria"))

    @app.template_filter("data_br")
    def data_br(value):
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%d/%m/%Y %H:%M")
        return str(value)

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=debug)
