from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
from datetime import datetime
import os
from supabase import create_client
from src.controllers.b2_utils import get_b2_file_url


# Carregar variáveis do .env
load_dotenv()


app = Flask(__name__)
app.jinja_env.globals['get_b2_file_url'] = get_b2_file_url

# Carrega as configurações do .env
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.jinja_env.globals.update(enumerate=enumerate)


SUPABASE_DB_URL = os.getenv("SUPABASE_DB_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_DB_URL, SUPABASE_KEY)

# Configuração do diretório de uploads
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png'}

# Extensões
database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'alert-info'

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow}

from src import routes
app.supabase = supabase

