import os
import pytz
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

# Importe os novos modelos de ponto de almoço
from models import db, Usuario, entradaPonto, saidaPonto, almocoPontoEntrada, almocoPontoSaida, justificativa

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///banco_ponto.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

def hora_brasilia():
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_brasilia)

# --- Decorador para Requerer um Papel Específico ---
def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'usuario_id' not in session:
                flash('Você precisa fazer login para acessar esta página.', 'warning')
                return redirect(url_for('login'))
            
            usuario = Usuario.query.get(session['usuario_id'])
            if not usuario:
                flash('Sua sessão de usuário é inválida. Faça login novamente.', 'danger')
                return redirect(url_for('login'))

            role_hierarchy = {
                'usuario': 1,
                'funcionario': 2,
                'admin': 3
            }

            required_level = role_hierarchy.get(required_role, 0)
            user_level = role_hierarchy.get(usuario.role, 0)

            if user_level < required_level:
                flash(f'Acesso negado. Você não tem permissão de {required_role}.', 'danger')
                return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Nova Rota: Página Home
@app.route('/', methods=['GET'])
@app.route('/home', methods=['GET'])
def home():
    user = None
    if 'usuario_id' in session:
        user = Usuario.query.get(session['usuario_id'])
    return render_template('home.html', user=user)

@app.route('/templates/registro.html', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']

        if Usuario.query.filter_by(nome=nome).first():
            flash('Usuário já existe.', 'warning')
            return redirect(url_for('registro'))

        novo_usuario = Usuario(nome=nome, role='usuario', estado_ponto='fora') # estado_ponto inicial 'fora'
        novo_usuario.set_senha(senha)
        db.session.add(novo_usuario)
        db.session.commit()
        flash('Registrado com sucesso. Faça login.', 'success')
        return redirect(url_for('login'))

    return render_template('registro.html')

@app.route('/templates/login.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nome = request.form['nome']
        senha = request.form['senha']

        usuario = Usuario.query.filter_by(nome=nome).first()
        if usuario and usuario.verificar_senha(senha):
            session['usuario_id'] = usuario.id
            flash('Login bem-sucedido.', 'success')
            return redirect(url_for('home')) 
        else:
            flash('E-mail ou senha incorretos!', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario_id', None)
    flash('Você saiu da sessão.', 'info')
    return redirect(url_for('home'))

# --- Rotas de Ponto ---

# Rota para Bater Ponto de Entrada
@app.route('/bater_entrada', methods=['POST'])
@role_required('funcionario') # Apenas funcionários podem bater ponto
def bater_entrada():
    usuario_logado = Usuario.query.get(session['usuario_id'])

    if usuario_logado.estado_ponto != 'fora':
        flash('Você já bateu sua entrada ou está em outro estado de ponto.', 'warning')
        return redirect(url_for('home'))

    novo_registro = entradaPonto(usuario_id=usuario_logado.id)
    db.session.add(novo_registro)
    usuario_logado.estado_ponto = 'trabalhando' # Altera o estado do usuário
    db.session.commit()
    flash(f'✅ Entrada registrada às {novo_registro.hora.strftime("%H:%M:%S")}.', 'success')
    return redirect(url_for('home'))

# Rota para Bater Ponto de Início de Almoço
@app.route('/bater_almoco_inicio', methods=['POST'])
@role_required('funcionario')
def bater_almoco_inicio():
    usuario_logado = Usuario.query.get(session['usuario_id'])

    if usuario_logado.estado_ponto != 'trabalhando':
        flash('Você precisa bater a entrada antes de iniciar o almoço.', 'warning')
        return redirect(url_for('home'))

    novo_registro = almocoPontoEntrada(usuario_id=usuario_logado.id)
    db.session.add(novo_registro)
    usuario_logado.estado_ponto = 'almoco' # Altera o estado do usuário
    db.session.commit()
    flash(f'✅ Início do almoço registrado às {novo_registro.hora.strftime("%H:%M:%S")}.', 'success')
    return redirect(url_for('home'))

# Rota para Bater Ponto de Fim de Almoço
@app.route('/bater_almoco_fim', methods=['POST'])
@role_required('funcionario')
def bater_almoco_fim():
    usuario_logado = Usuario.query.get(session['usuario_id'])

    if usuario_logado.estado_ponto != 'almoco':
        flash('Você precisa iniciar o almoço antes de finalizar.', 'warning')
        return redirect(url_for('home'))

    novo_registro = almocoPontoSaida(usuario_id=usuario_logado.id)
    db.session.add(novo_registro)
    usuario_logado.estado_ponto = 'trabalhando' # Retorna para 'trabalhando' após o almoço
    db.session.commit()
    flash(f'✅ Fim do almoço registrado às {novo_registro.hora.strftime("%H:%M:%S")}.', 'success')
    return redirect(url_for('home'))

# Rota para Bater Ponto de Saída
@app.route('/bater_saida', methods=['POST'])
@role_required('funcionario')
def bater_saida():
    usuario_logado = Usuario.query.get(session['usuario_id'])

    if usuario_logado.estado_ponto != 'trabalhando':
        flash('Você precisa bater o ponto de entrada e finalizar o almoço (se aplicável) antes de sair.', 'warning')
        return redirect(url_for('home'))

    novo_registro = saidaPonto(usuario_id=usuario_logado.id)
    db.session.add(novo_registro)
    usuario_logado.estado_ponto = 'fora' # Altera o estado para 'fora'
    db.session.commit()
    flash(f'✅ Saída registrada às {novo_registro.hora.strftime("%H:%M:%S")}. Você foi desconectado.', 'success')
    
    # Desloga o usuário após bater saída
    session.pop('usuario_id', None)
    return redirect(url_for('home'))

# --- Rotas de Páginas Específicas (mantêm o role_required) ---

@app.route('/templates/entradaPonto.html', methods=['GET'])
@role_required('funcionario') # Mantém o decorador, mas o uso mudou
def view_entrada_ponto():
    usuario_logado = Usuario.query.get(session['usuario_id'])
    registrosE = entradaPonto.query.filter_by(usuario_id=usuario_logado.id).order_by(entradaPonto.hora.desc()).all()
    return render_template('entradaPonto.html', registrosEntrada=registrosE, user=usuario_logado)

@app.route('/templates/saidaPonto.html', methods=['GET'])
@role_required('funcionario') # Mantém o decorador, mas o uso mudou
def view_saida_ponto():
    usuario_logado = Usuario.query.get(session['usuario_id'])
    registrosS = saidaPonto.query.filter_by(usuario_id=usuario_logado.id).order_by(saidaPonto.hora.desc()).all()
    return render_template('saidaPonto.html', registrosSaida=registrosS, user=usuario_logado)

# Nova rota para visualizar os pontos de almoço
@app.route('/templates/almocoPonto.html', methods=['GET'])
@role_required('funcionario')
def view_almoco_ponto():
    usuario_logado = Usuario.query.get(session['usuario_id'])
    registrosAE = almocoPontoEntrada.query.filter_by(usuario_id=usuario_logado.id).order_by(almocoPontoEntrada.hora.desc()).all()
    registrosAS = almocoPontoSaida.query.filter_by(usuario_id=usuario_logado.id).order_by(almocoPontoSaida.hora.desc()).all()
    return render_template('almocoPonto.html', registrosAlmocoEntrada=registrosAE, registrosAlmocoSaida=registrosAS, user=usuario_logado)


@app.route('/templates/justificativa.html', methods=['GET', 'POST'])
@role_required('usuario')
def justificativas():
    usuario_logado = Usuario.query.get(session['usuario_id'])
    if request.method == 'POST':
        registrosJustificativa = request.form['nome']
        if usuario_logado:
            novo_registro = justificativa(nome=registrosJustificativa, usuario_id=usuario_logado.id)
            db.session.add(novo_registro)
            db.session.commit()
            flash('Justificativa enviada com sucesso!', 'success')
        return redirect(url_for('justificativas'))

    registrosJ = justificativa.query.filter_by(usuario_id=usuario_logado.id).order_by(justificativa.hora.desc()).all()
    return render_template('justificativa.html', registrosJustificativa=registrosJ, user=usuario_logado)

@app.route('/templates/relatorio.html', methods=['GET'])
@role_required('funcionario')
def relatorio():
    usuario_logado = Usuario.query.get(session['usuario_id'])
    
    # Se o usuário é funcionario, ele vê os próprios relatórios, se for admin, vê todos
    if usuario_logado.role == 'funcionario':
        registrosE = entradaPonto.query.filter_by(usuario_id=usuario_logado.id).order_by(entradaPonto.hora.desc()).all()
        registrosS = saidaPonto.query.filter_by(usuario_id=usuario_logado.id).order_by(saidaPonto.hora.desc()).all()
        registrosAE = almocoPontoEntrada.query.filter_by(usuario_id=usuario_logado.id).order_by(almocoPontoEntrada.hora.desc()).all()
        registrosAS = almocoPontoSaida.query.filter_by(usuario_id=usuario_logado.id).order_by(almocoPontoSaida.hora.desc()).all()
        registrosJ = justificativa.query.filter_by(usuario_id=usuario_logado.id).order_by(justificativa.hora.desc()).all()
    else: # Admin (por causa da role_required('funcionario') e hierarquia)
        registrosE = entradaPonto.query.order_by(entradaPonto.hora.desc()).all()
        registrosS = saidaPonto.query.order_by(saidaPonto.hora.desc()).all()
        registrosAE = almocoPontoEntrada.query.order_by(almocoPontoEntrada.hora.desc()).all()
        registrosAS = almocoPontoSaida.query.order_by(almocoPontoSaida.hora.desc()).all()
        registrosJ = justificativa.query.order_by(justificativa.hora.desc()).all()

    return render_template('relatorio.html', 
                           registrosEntrada = registrosE, 
                           registrosSaida = registrosS, 
                           registrosAlmocoEntrada = registrosAE, # Passa para o template
                           registrosAlmocoSaida = registrosAS,   # Passa para o template
                           registrosJustificativa = registrosJ, 
                           user=usuario_logado)

@app.route('/admin/manage_users', methods=['GET', 'POST'])
@role_required('admin')
def manage_users():
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        new_role = request.form.get('new_role')
        
        user = Usuario.query.get(user_id)
        if user:
            # Proteção adicional: não permite alterar o próprio papel ou de outro admin para 'usuario'/'funcionario'
            if user.id == session['usuario_id'] and new_role != 'admin':
                flash('Você não pode alterar seu próprio papel para algo diferente de admin.', 'danger')
            elif user.role == 'admin' and new_role != 'admin': # E é outro admin (não a si mesmo)
                flash(f'Cuidado! Alterar o papel de outro admin ({user.nome}) requer atenção.', 'warning')
                user.role = new_role
                db.session.commit()
                flash(f'Papel de {user.nome} alterado para {new_role}.', 'success')
            elif new_role in ['usuario', 'funcionario', 'admin']:
                user.role = new_role
                db.session.commit()
                flash(f'Papel de {user.nome} alterado para {new_role}.', 'success')
            else:
                flash('Papel inválido fornecido.', 'danger')
        return redirect(url_for('manage_users'))

    usuarios = Usuario.query.all()
    usuario_logado = Usuario.query.get(session['usuario_id'])
    return render_template('manage_users.html', usuarios=usuarios, user=usuario_logado)

@app.errorhandler(404)
def page_not_found(e):
    flash('Rota inexistente!', 'danger')
    return redirect(url_for('home'))

migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Create a default admin user if no users exist (for initial setup)
        if not Usuario.query.first():
            admin_user = Usuario(nome="admin", role='admin', estado_ponto='fora') # admin também tem estado_ponto
            admin_user.set_senha("adminpass")
            db.session.add(admin_user)
            db.session.commit()
            print("Usuário admin criado: admin/adminpass")
    app.run(debug=True, port=5500)