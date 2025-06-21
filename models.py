import pytz
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def hora_brasilia():
    fuso_brasilia = pytz.timezone('America/Sao_Paulo')
    return datetime.now(fuso_brasilia)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), unique=True, nullable=False) # Nome agora é único
    senha_hash = db.Column(db.String(200), nullable=True)
    role = db.Column(db.String(50), default='usuario') # 'usuario', 'funcionario', 'admin'
    # Novo campo para rastrear o estado do ponto
    # 'fora': Não bateu entrada ou já bateu saída
    # 'trabalhando': Bateu entrada, mas não almoço ou saída
    # 'almoco': Bateu início almoço, mas não fim almoço
    estado_ponto = db.Column(db.String(50), default='fora')
    # Relacionamentos
    registrosEntrada = db.relationship('entradaPonto', backref='usuario', lazy=True)
    registrosSaida = db.relationship('saidaPonto', backref='usuario', lazy=True)
    registrosAlmocoEntrada = db.relationship('almocoPontoEntrada', backref='usuario', lazy=True) # Novo
    registrosAlmocoSaida = db.relationship('almocoPontoSaida', backref='usuario', lazy=True)     # Novo
    registrosJustificativa = db.relationship('justificativa', backref='usuario', lazy=True)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

class entradaPonto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.DateTime, default=hora_brasilia)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class saidaPonto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.DateTime, default=hora_brasilia)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class almocoPontoEntrada(db.Model): # NOVO MODELO
    id = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.DateTime, default=hora_brasilia)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class almocoPontoSaida(db.Model): # NOVO MODELO
    id = db.Column(db.Integer, primary_key=True)
    hora = db.Column(db.DateTime, default=hora_brasilia)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class justificativa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False) # Aumentei o tamanho para a justificativa
    hora = db.Column(db.DateTime, default=hora_brasilia)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)