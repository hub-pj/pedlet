import os
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, Response, flash, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from werkzeug.utils import secure_filename

load_dotenv()

db = SQLAlchemy()

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}


def normalize_database_url(url: str | None) -> str | None:
    """Ajusta a URL do Render para o driver psycopg do SQLAlchemy."""
    if not url:
        return None
    url = url.strip()
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


class Galeria(db.Model):
    __tablename__ = "galerias"

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(160), nullable=False)
    categoria = db.Column(db.String(100), nullable=True)
    turma = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    fotos = db.relationship(
        "Foto",
        backref="galeria",
        cascade="all, delete-orphan",
        order_by="Foto.ordem.asc()",
        lazy=True,
    )


class Foto(db.Model):
    __tablename__ = "fotos"

    id = db.Column(db.Integer, primary_key=True)
    galeria_id = db.Column(db.Integer, db.ForeignKey("galerias.id"), nullable=False, index=True)
    nome = db.Column(db.String(160), nullable=True)
    classificacao = db.Column(db.String(120), nullable=True)
    filename = db.Column(db.String(255), nullable=True)
    mimetype = db.Column(db.String(80), nullable=False)
    dados = db.Column(db.LargeBinary, nullable=False)
    ordem = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "pedlet-dev")

    database_url = normalize_database_url(os.environ.get("DATABASE_URL"))
    if not database_url:
        # Ajuda para teste local sem quebrar, mas no Render use PostgreSQL.
        database_url = "sqlite:///pedlet_local.db"

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_UPLOAD_MB", "30")) * 1024 * 1024

    db.init_app(app)

    app.config["DB_STARTUP_ERROR"] = None
    with app.app_context():
        try:
            db.create_all()
        except Exception as exc:
            # Não derruba o servidor no Render. A rota /saude mostra o erro real do banco.
            app.config["DB_STARTUP_ERROR"] = str(exc)

    @app.route("/healthz")
    def healthz():
        return {"status": "ok", "app": "pedlet-flask-postgres"}

    @app.route("/saude")
    def saude():
        try:
            total = Galeria.query.count()
            return {
                "status": "ok",
                "postgresql": "conectado",
                "galerias": total,
            }
        except Exception as exc:
            return {
                "status": "erro",
                "postgresql": "falha na conexão",
                "erro": str(exc),
            }, 500

    @app.route("/")
    def index():
        if app.config.get("DB_STARTUP_ERROR"):
            return render_template(
                "erro.html",
                titulo="Banco de dados não conectado",
                mensagem="Confira a variável DATABASE_URL no Render e teste novamente a rota /saude.",
                detalhe=app.config["DB_STARTUP_ERROR"],
            ), 500

        q = request.args.get("q", "").strip()
        query = Galeria.query
        if q:
            like = f"%{q}%"
            query = query.outerjoin(Foto).filter(
                or_(
                    Galeria.titulo.ilike(like),
                    Galeria.categoria.ilike(like),
                    Galeria.turma.ilike(like),
                    Galeria.descricao.ilike(like),
                    Foto.nome.ilike(like),
                    Foto.classificacao.ilike(like),
                )
            ).distinct()
        galerias = query.order_by(Galeria.created_at.desc()).all()
        return render_template("index.html", galerias=galerias, q=q)

    @app.route("/nova", methods=["GET", "POST"])
    def nova():
        if app.config.get("DB_STARTUP_ERROR"):
            return render_template(
                "erro.html",
                titulo="Banco de dados não conectado",
                mensagem="Confira a variável DATABASE_URL no Render e teste novamente a rota /saude.",
                detalhe=app.config["DB_STARTUP_ERROR"],
            ), 500

        if request.method == "POST":
            titulo = request.form.get("titulo", "").strip()
            categoria = request.form.get("categoria", "").strip()
            turma = request.form.get("turma", "").strip()
            descricao = request.form.get("descricao", "").strip()

            if not titulo:
                flash("Informe o título da galeria.", "erro")
                return redirect(url_for("nova"))

            arquivos = request.files.getlist("fotos")
            arquivos_validos = [a for a in arquivos if a and a.filename]

            if len(arquivos_validos) > 6:
                flash("Cada galeria aceita no máximo 6 fotos.", "erro")
                return redirect(url_for("nova"))

            galeria = Galeria(
                titulo=titulo,
                categoria=categoria,
                turma=turma,
                descricao=descricao,
            )
            db.session.add(galeria)
            db.session.flush()

            nomes = request.form.getlist("nome_foto")
            classificacoes = request.form.getlist("classificacao_foto")

            for idx, arquivo in enumerate(arquivos_validos):
                if not allowed_file(arquivo.filename):
                    db.session.rollback()
                    flash("Use apenas imagens PNG, JPG, JPEG, WEBP ou GIF.", "erro")
                    return redirect(url_for("nova"))

                dados = arquivo.read()
                if not dados:
                    continue

                foto = Foto(
                    galeria_id=galeria.id,
                    nome=(nomes[idx].strip() if idx < len(nomes) else ""),
                    classificacao=(classificacoes[idx].strip() if idx < len(classificacoes) else ""),
                    filename=secure_filename(arquivo.filename),
                    mimetype=arquivo.mimetype or "application/octet-stream",
                    dados=dados,
                    ordem=idx,
                )
                db.session.add(foto)

            db.session.commit()
            flash("Galeria criada com sucesso!", "sucesso")
            return redirect(url_for("detalhe", galeria_id=galeria.id))

        return render_template("nova.html")

    @app.route("/galeria/<int:galeria_id>")
    def detalhe(galeria_id: int):
        galeria = Galeria.query.get_or_404(galeria_id)
        return render_template("detalhe.html", galeria=galeria)

    @app.route("/galeria/<int:galeria_id>/editar", methods=["GET", "POST"])
    def editar(galeria_id: int):
        galeria = Galeria.query.get_or_404(galeria_id)

        if request.method == "POST":
            galeria.titulo = request.form.get("titulo", "").strip() or galeria.titulo
            galeria.categoria = request.form.get("categoria", "").strip()
            galeria.turma = request.form.get("turma", "").strip()
            galeria.descricao = request.form.get("descricao", "").strip()

            for foto in galeria.fotos:
                foto.nome = request.form.get(f"nome_{foto.id}", "").strip()
                foto.classificacao = request.form.get(f"classificacao_{foto.id}", "").strip()

            atuais = len(galeria.fotos)
            novos = [a for a in request.files.getlist("fotos") if a and a.filename]
            if atuais + len(novos) > 6:
                flash("A galeria pode ter no máximo 6 fotos no total.", "erro")
                return redirect(url_for("editar", galeria_id=galeria.id))

            for idx, arquivo in enumerate(novos, start=atuais):
                if not allowed_file(arquivo.filename):
                    flash("Use apenas imagens PNG, JPG, JPEG, WEBP ou GIF.", "erro")
                    return redirect(url_for("editar", galeria_id=galeria.id))
                dados = arquivo.read()
                if not dados:
                    continue
                foto = Foto(
                    galeria_id=galeria.id,
                    nome="",
                    classificacao="",
                    filename=secure_filename(arquivo.filename),
                    mimetype=arquivo.mimetype or "application/octet-stream",
                    dados=dados,
                    ordem=idx,
                )
                db.session.add(foto)

            db.session.commit()
            flash("Galeria atualizada com sucesso!", "sucesso")
            return redirect(url_for("detalhe", galeria_id=galeria.id))

        return render_template("editar.html", galeria=galeria)

    @app.post("/foto/<int:foto_id>/excluir")
    def excluir_foto(foto_id: int):
        foto = Foto.query.get_or_404(foto_id)
        galeria_id = foto.galeria_id
        db.session.delete(foto)
        db.session.commit()
        flash("Foto excluída.", "sucesso")
        return redirect(url_for("editar", galeria_id=galeria_id))

    @app.post("/galeria/<int:galeria_id>/excluir")
    def excluir_galeria(galeria_id: int):
        galeria = Galeria.query.get_or_404(galeria_id)
        db.session.delete(galeria)
        db.session.commit()
        flash("Galeria excluída com sucesso.", "sucesso")
        return redirect(url_for("index"))

    @app.route("/foto/<int:foto_id>")
    def foto(foto_id: int):
        foto = Foto.query.get_or_404(foto_id)
        return Response(foto.dados, mimetype=foto.mimetype)

    @app.errorhandler(413)
    def arquivo_grande(_error):
        return render_template(
            "erro.html",
            titulo="Arquivo muito grande",
            mensagem="Reduza o tamanho das imagens ou aumente MAX_UPLOAD_MB nas variáveis do Render.",
        ), 413

    @app.errorhandler(500)
    def erro_500(error):
        return render_template(
            "erro.html",
            titulo="Erro interno",
            mensagem="Verifique a variável DATABASE_URL e os logs do Render.",
            detalhe=str(error),
        ), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
