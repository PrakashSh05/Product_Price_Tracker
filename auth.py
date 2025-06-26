from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegistrationForm
from extensions import mongo
from datetime import datetime

# Initialize LoginManager
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, email):
        self.email = email
    
    def get_id(self):
        return self.email
    
    @staticmethod
    def get(email):
        user_data = mongo.db.users.find_one({'email': email})
        if not user_data:
            return None
        return User(email=user_data['email'])

# User loader function
@login_manager.user_loader
def load_user(email):
    return User.get(email)

# Create auth blueprint
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = LoginForm()
    if form.validate_on_submit():
        user = mongo.db.users.find_one({'email': form.email.data})
        if user and check_password_hash(user['password'], form.password.data):
            user_obj = User(user['email'])
            login_user(user_obj, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.index'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', title='Login', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data)
        user = {
            'username': form.username.data,
            'email': form.email.data,
            'password': hashed_password,
            'created_at': datetime.utcnow()
        }
        mongo.db.users.insert_one(user)
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', title='Register', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))
