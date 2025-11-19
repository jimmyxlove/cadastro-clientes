from flask import Flask, render_template, request, redirect, url_for, flash, g, abort
import sqlite3
import os
from werkzeug.exceptions import BadRequest

DB_NAME = os.path.join(os.path.dirname(__file__), "clientes.db")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_NAME)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        telefone TEXT,
        endereco TEXT
    )""")
    db.commit()

def create_app():
    app = Flask(__name__, static_folder='static', template_folder='templates')
    app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-change-me')
    app.config['DATABASE'] = DB_NAME

    @app.before_first_request
    def _init():
        init_db()

    @app.teardown_appcontext
    def close_connection(exception):
        db = getattr(g, '_database', None)
        if db is not None:
            db.close()

    @app.route('/')
    def index():
        db = get_db()
        cur = db.execute('SELECT id, nome, email, telefone FROM clientes ORDER BY id DESC LIMIT 100')
        clientes = cur.fetchall()
        return render_template('index.html', clientes=clientes)

    def validate_cliente(data):
        nome = (data.get('nome') or '').strip()
        email = (data.get('email') or '').strip()
        if not nome:
            raise BadRequest('Nome é obrigatório.')
        if not email or '@' not in email:
            raise BadRequest('Email inválido.')
        telefone = (data.get('telefone') or '').strip()
        endereco = (data.get('endereco') or '').strip()
        return {'nome': nome, 'email': email, 'telefone': telefone, 'endereco': endereco}

    @app.route('/adicionar', methods=['GET', 'POST'])
    def adicionar():
        if request.method == 'POST':
            try:
                data = validate_cliente(request.form)
            except BadRequest as e:
                flash(str(e), 'error')
                return render_template('form.html', cliente=request.form)
            db = get_db()
            try:
                db.execute(
                    'INSERT INTO clientes (nome, email, telefone, endereco) VALUES (?,?,?,?)',
                    (data['nome'], data['email'], data['telefone'], data['endereco'])
                )
                db.commit()
                flash('Cliente adicionado com sucesso!', 'success')
                return redirect(url_for('index'))
            except sqlite3.IntegrityError:
                flash('Já existe um cliente com esse email.', 'error')
                return render_template('form.html', cliente=request.form)
        return render_template('form.html', cliente={})

    @app.route('/editar/<int:cliente_id>', methods=['GET', 'POST'])
    def editar(cliente_id):
        db = get_db()
        cur = db.execute('SELECT * FROM clientes WHERE id = ?', (cliente_id,))
        cliente = cur.fetchone()
        if not cliente:
            abort(404)
        if request.method == 'POST':
            try:
                data = validate_cliente(request.form)
            except BadRequest as e:
                flash(str(e), 'error')
                return render_template('form.html', cliente=request.form, editar=True)
            db.execute(
                'UPDATE clientes SET nome=?, email=?, telefone=?, endereco=? WHERE id=?',
                (data['nome'], data['email'], data['telefone'], data['endereco'], cliente_id)
            )
            db.commit()
            flash('Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('index'))
        return render_template('form.html', cliente=cliente, editar=True)

    @app.route('/buscar', methods=['GET'])
    def buscar():
        q = (request.args.get('q') or '').strip()
        db = get_db()
        if not q:
            return render_template('buscar.html', clientes=[])
        q_like = f'%{q}%'
        cur = db.execute(
            """SELECT id, nome, email, telefone FROM clientes
               WHERE nome LIKE ? OR email LIKE ? OR telefone LIKE ?
               ORDER BY id DESC LIMIT 100""", (q_like, q_like, q_like)
        )
        clientes = cur.fetchall()
        return render_template('buscar.html', clientes=clientes, q=q)

    @app.route('/deletar/<int:cliente_id>', methods=['POST'])
    def deletar(cliente_id):
        db = get_db()
        db.execute('DELETE FROM clientes WHERE id = ?', (cliente_id,))
        db.commit()
        flash('Cliente deletado.', 'info')
        return redirect(url_for('index'))

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
