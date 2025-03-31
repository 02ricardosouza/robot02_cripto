from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from .models import User

auth_bp = Blueprint('auth', __name__)
bcrypt = Bcrypt()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # API JSON request
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            user = User.get_by_username(username)
            
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return jsonify({
                    'success': True,
                    'message': 'Login realizado com sucesso',
                    'is_admin': user.is_admin
                })
            
            return jsonify({
                'success': False,
                'message': 'Usuário ou senha inválidos'
            }), 401
        
        # Form submission
        else:
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.get_by_username(username)
            
            if user and bcrypt.check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('index'))
            
            flash('Usuário ou senha inválidos', 'danger')
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    # Apenas administradores podem registrar novos usuários
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        is_admin = request.form.get('is_admin') == 'on'
        
        if not username or not password or not confirm_password:
            flash('Todos os campos são obrigatórios', 'danger')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('As senhas não coincidem', 'danger')
            return render_template('register.html')
        
        existing_user = User.get_by_username(username)
        if existing_user:
            flash('Nome de usuário já está em uso', 'danger')
            return render_template('register.html')
        
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User.create_user(username, password_hash, is_admin)
        
        if user:
            flash('Usuário criado com sucesso', 'success')
            return redirect(url_for('auth.register'))
        else:
            flash('Erro ao criar usuário', 'danger')
    
    return render_template('register.html')

@auth_bp.route('/api/check-auth')
def check_auth():
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'username': current_user.username,
            'is_admin': current_user.is_admin
        })
    
    return jsonify({
        'authenticated': False
    }), 401

# API para gerenciamento de usuários (apenas admin)
@auth_bp.route('/api/users', methods=['GET'])
@login_required
def get_users():
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    # Obter todos os usuários do banco
    conn = User.get_db_connection()
    conn.row_factory = User.dict_factory
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, is_admin FROM users')
    users = cursor.fetchall()
    
    conn.close()
    
    return jsonify(users)

@auth_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Acesso não autorizado'}), 403
    
    # Não permitir deletar a si mesmo
    if current_user.id == user_id:
        return jsonify({'error': 'Não é possível excluir seu próprio usuário'}), 400
    
    conn = User.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Usuário excluído com sucesso'})

# Adicionar rota para alteração de senha
@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not current_password or not new_password or not confirm_password:
            flash('Todos os campos são obrigatórios', 'danger')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('As senhas não coincidem', 'danger')
            return render_template('change_password.html')
        
        # Verificar senha atual
        if not bcrypt.check_password_hash(current_user.password, current_password):
            flash('Senha atual incorreta', 'danger')
            return render_template('change_password.html')
        
        # Atualizar senha
        conn = User.get_db_connection()
        cursor = conn.cursor()
        
        password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cursor.execute('UPDATE users SET password = ? WHERE id = ?', (password_hash, current_user.id))
        
        conn.commit()
        conn.close()
        
        flash('Senha alterada com sucesso', 'success')
        return redirect(url_for('index'))
    
    return render_template('change_password.html') 