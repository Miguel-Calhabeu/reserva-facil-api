"""
Módulo de conexão com o banco de dados.
"""
import psycopg2
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env para a sessão atual.
# Isso permite que a configuração do banco de dados seja gerenciada fora do código.
load_dotenv()

def get_db_connection():
    """
    Estabelece e retorna uma nova conexão com o banco de dados PostgreSQL.

    As credenciais de conexão são lidas a partir das variáveis de ambiente.
    Levanta uma exceção se as variáveis não estiverem configuradas.

    Returns:
        psycopg2.connection: Um objeto de conexão com o banco de dados.
    """
    conn = psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", 5432)
    )
    return conn
