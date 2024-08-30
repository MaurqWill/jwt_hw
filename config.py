import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'super_secret_secrets')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+mysqlconnector://root:C0dingTemp012!@localhost/factory_db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
