from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

def get_engine():
    load_dotenv()
    db_path = os.getenv('DB_PATH', 'entegre_veritabani.db')
    engine = create_engine(f'sqlite:///{db_path}')
    return engine
