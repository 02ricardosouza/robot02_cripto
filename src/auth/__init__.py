from flask_login import LoginManager
from flask_bcrypt import Bcrypt

login_manager = LoginManager()
bcrypt = Bcrypt()

def init_auth(app):
    # Inicializa o gerenciador de login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página'
    login_manager.login_message_category = 'info'
    
    # Inicializa o bcrypt
    bcrypt.init_app(app)
    
    # Registra o blueprint de autenticação
    from .routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Configura o callback de carregamento de usuário
    from .models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(int(user_id))
    
    # Inicializa o banco de dados de usuários
    User.init_db()
    
    # Cria o usuário admin padrão se não existir
    admin = User.get_by_username('admin')
    if not admin:
        password_hash = bcrypt.generate_password_hash('admin').decode('utf-8')
        User.create_user('admin', password_hash, is_admin=True) 