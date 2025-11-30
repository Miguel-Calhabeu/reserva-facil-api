"""
Módulo principal da API FastAPI para o sistema de gestão de eventos.

Este módulo define os endpoints da API, os modelos de dados Pydantic para validação
e a lógica de negócio para interagir com o banco de dados PostgreSQL.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, model_validator
import psycopg2
from database import get_db_connection
from utils import load_sql_query
from typing import Optional, List
from fastapi.middleware.cors import CORSMiddleware
from datetime import date, datetime
import re

# --- Inicialização da Aplicação FastAPI ---
app = FastAPI(
    title="API de Gestão de Eventos",
    description="API para gerenciar cadastros e pedidos de eventos, utilizando PostgreSQL e Psycopg2.",
    version="1.0.0"
)

# --- Middleware ---
# Habilita o Cross-Origin Resource Sharing (CORS) para permitir que o frontend
# (executando em uma origem diferente, ex: http://localhost:5173) faça requisições para esta API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos os métodos HTTP (GET, POST, etc.).
    allow_headers=["*"],  # Permite todos os cabeçalhos.
)

# --- Modelos de Dados (Pydantic) ---
# Os modelos Pydantic são usados para definir a estrutura dos dados das requisições (JSON bodies),
# garantindo a tipagem e a validação automática dos dados de entrada.

class PedidoCreate(BaseModel):
    """Modelo para a criação de um novo pedido, recebido do frontend."""
    nomeeventoproposto: Optional[str] = None
    localproposto: Optional[str] = None
    datainicioproposto: Optional[date] = None
    datafimproposto: Optional[date] = None
    descricao: Optional[str] = None
    usuario: str
    analista: str
    gerente: str

    @model_validator(mode='after')
    def check_dates(self):
        """Validador Pydantic para garantir a consistência das datas do pedido."""
        if self.datainicioproposto and self.datainicioproposto < date.today():
            raise ValueError('A data de início não pode ser no passado.')
        if self.datainicioproposto and self.datafimproposto and self.datafimproposto < self.datainicioproposto:
            raise ValueError('A data de fim deve ser após a data de início.')
        return self

class UsuarioCreate(BaseModel):
    """Modelo para a criação de um novo usuário, com validações complexas."""
    ndoc: str
    tipodoc: str
    email: EmailStr  # Utiliza o tipo EmailStr do Pydantic para validação automática de formato de e-mail.
    nome: Optional[str] = None
    datanasc: Optional[date] = None
    rg: Optional[str] = None
    razaosocial: Optional[str] = None

    @model_validator(mode='after')
    def check_fields(self):
        """
        Validador Pydantic que executa após a validação dos campos individuais.
        Ideal para regras de negócio que dependem de múltiplos campos.
        """
        tipodoc = self.tipodoc
        ndoc = self.ndoc
        nome = self.nome
        razaosocial = self.razaosocial
        rg = self.rg

        # 1. Validação do tipo de documento.
        if tipodoc not in ['CPF', 'CNPJ']:
            raise ValueError('Tipo de documento deve ser CPF ou CNPJ.')

        # 2. Validação do formato do documento e campos condicionais.
        digits_only_ndoc = re.sub(r'\D', '', ndoc)
        if tipodoc == 'CPF':
            if len(digits_only_ndoc) != 11:
                raise ValueError('CPF deve conter 11 dígitos.')
            if not nome:
                raise ValueError('Nome é obrigatório para CPF.')

            # Validação do RG (apenas para CPF).
            if rg:
                digits_only_rg = re.sub(r'\D', '', rg)
                if not (7 <= len(digits_only_rg) <= 9):
                    raise ValueError('RG deve conter entre 7 e 9 dígitos.')

        elif tipodoc == 'CNPJ':
            if len(digits_only_ndoc) != 14:
                raise ValueError('CNPJ deve conter 14 dígitos.')
            if not razaosocial:
                raise ValueError('Razão Social é obrigatória para CNPJ.')

        # 3. Validação da idade (mínimo de 18 anos).
        if self.datanasc:
            today = date.today()
            # Calcula a idade de forma precisa, considerando o dia e mês de aniversário.
            age = today.year - self.datanasc.year - ((today.month, today.day) < (self.datanasc.month, self.datanasc.day))
            if age < 18:
                raise ValueError('Usuário deve ter pelo menos 18 anos.')

        return self

class ItemFilter(BaseModel):
    """Modelo para os parâmetros de filtro da consulta de itens."""
    search: Optional[str] = None
    tiporecursofisico: Optional[str] = None
    statusitem: Optional[str] = None
    qualidade: Optional[str] = None
    armazem: Optional[str] = None

# --- Endpoints da API ---

# GET Endpoints (Leitura de Dados)
@app.get("/users", summary="Lista todos os usuários")
async def get_users():
    """Endpoint para obter uma lista de todos os usuários cadastrados."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_users")
        cur.execute(query)
        users = cur.fetchall()
        cur.close()
        conn.close()
        # Formata a saída para um JSON mais legível.
        return [{"ndoc": user[0], "nome": user[1], "email": user[2]} for user in users]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {e}")

@app.get("/analysts", summary="Lista todos os analistas")
async def get_analysts():
    """Endpoint para obter uma lista de todos os analistas."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_analysts")
        cur.execute(query)
        analysts = cur.fetchall()
        cur.close()
        conn.close()
        return [{"cpf": analyst[0], "nome": analyst[1]} for analyst in analysts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analysts: {e}")

@app.get("/managers", summary="Lista todos os gerentes")
async def get_managers():
    """Endpoint para obter uma lista de todos os gerentes."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_managers")
        cur.execute(query)
        managers = cur.fetchall()
        cur.close()
        conn.close()
        return [{"cpf": manager[0], "nome": manager[1]} for manager in managers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch managers: {e}")

# POST Endpoints (Criação de Dados)
@app.post("/pedidos", summary="Cria um novo pedido de evento")
async def create_pedido(pedido: PedidoCreate):
    """
    Cria um novo pedido, aplicando validações e gerando dados no servidor.
    - Valida a existência de chaves estrangeiras (usuário, analista, gerente).
    - Gera um ID único para o pedido no formato PED-{ANO}-{NNN}.
    - Define a data de submissão e o status inicial no backend.
    - Utiliza controle transacional (commit/rollback).
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Validação da existência das chaves estrangeiras antes de inserir.
        cur.execute("SELECT ndoc FROM USUARIO WHERE ndoc = %s", (pedido.usuario,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Usuário com documento '{pedido.usuario}' não encontrado.")

        cur.execute("SELECT cpf FROM ANALISTA WHERE cpf = %s", (pedido.analista,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Analista com CPF '{pedido.analista}' não encontrado.")

        cur.execute("SELECT cpf FROM GERENTE WHERE cpf = %s", (pedido.gerente,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail=f"Gerente com CPF '{pedido.gerente}' não encontrado.")

        # 2. Geração de dados pelo servidor.
        # Lógica para criar um ID sequencial por ano.
        current_year = datetime.now().year
        cur.execute(
            "SELECT IDPEDIDO FROM PEDIDO WHERE IDPEDIDO LIKE %s ORDER BY IDPEDIDO DESC LIMIT 1",
            (f"PED-{current_year}-%",)
        )
        last_id = cur.fetchone()

        if last_id:
            last_number = int(last_id[0].split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1

        idpedido = f"PED-{current_year}-{new_number:03d}"
        datasubmissao = date.today()
        status = "Em Análise"

        # 3. Inserção no banco de dados.
        query = load_sql_query("insert_pedido")
        # Substituição dos placeholders do arquivo .sql pelo formato do psycopg2.
        # Esta abordagem, embora funcional, pode ser melhorada para evitar a manipulação de strings.
        # Uma alternativa seria ter o SQL completo com '%s' diretamente no código ou em um formato mais estruturado.
        query = query.replace("'{idpedido}'", "%s")
        query = query.replace("'{nomeeventoproposto}'", "%s")
        query = query.replace("'{status}'", "%s")
        query = query.replace("'{localproposto}'", "%s")
        query = query.replace("'{datainicioproposto}'", "%s")
        query = query.replace("'{datafimproposto}'", "%s")
        query = query.replace("'{datasubmissao}'", "%s")
        query = query.replace("'{descricao}'", "%s")
        query = query.replace("'{usuario}'", "%s")
        query = query.replace("'{analista}'", "%s")
        query = query.replace("'{gerente}'", "%s")

        # Execução da query parametrizada para prevenir SQL Injection.
        cur.execute(query, (
            idpedido,
            pedido.nomeeventoproposto,
            status,
            pedido.localproposto,
            pedido.datainicioproposto,
            pedido.datafimproposto,
            datasubmissao,
            pedido.descricao,
            pedido.usuario,
            pedido.analista,
            pedido.gerente
        ))
        conn.commit()  # Confirma a transação.

        return {"message": "Pedido criado com sucesso!", "idpedido": idpedido}
    except (HTTPException, ValueError) as e:
        if conn:
            conn.rollback()  # Desfaz a transação em caso de erro de validação ou HTTP.
        if isinstance(e, ValueError):
            raise HTTPException(status_code=400, detail=str(e))
        raise e
    except Exception as e:
        if conn:
            conn.rollback()  # Desfaz a transação para qualquer outro erro.
        raise HTTPException(status_code=500, detail=f"Ocorreu um erro interno: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

@app.post("/usuarios", summary="Cria um novo usuário")
async def create_usuario(usuario: UsuarioCreate):
    """
    Cria um novo usuário, aplicando validações de dados e de unicidade.
    - As validações de formato (CPF, CNPJ, e-mail, idade) são feitas pelo Pydantic.
    - A validação de unicidade (documento e e-mail) é feita com consulta ao banco.
    - Utiliza controle transacional (commit/rollback).
    """
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # 1. Validação de unicidade (conflito de dados).
        cur.execute("SELECT ndoc FROM USUARIO WHERE ndoc = %s", (usuario.ndoc,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"Documento '{usuario.ndoc}' já cadastrado.")

        cur.execute("SELECT email FROM USUARIO WHERE email = %s", (str(usuario.email),))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail=f"E-mail '{usuario.email}' já cadastrado.")

        # 2. Inserção no banco de dados.
        query = load_sql_query("insert_usuario")
        query = query.replace("'{ndoc}'", "%s")
        query = query.replace("'{tipodoc}'", "%s")
        query = query.replace("'{email}'", "%s")
        query = query.replace("{nome}", "%s")
        query = query.replace("{datanasc}", "%s")
        query = query.replace("{rg}", "%s")
        query = query.replace("{razaosocial}", "%s")

        cur.execute(query, (
            usuario.ndoc,
            usuario.tipodoc,
            str(usuario.email),
            usuario.nome,
            usuario.datanasc,
            usuario.rg,
            usuario.razaosocial
        ))
        conn.commit()

        return {"message": "Usuário cadastrado com sucesso!", "ndoc": usuario.ndoc}
    except HTTPException as e:
        if conn:
            conn.rollback()
        raise e
    except Exception as e:
        if conn:
            conn.rollback()
        # Captura erros de validação do Pydantic e outros erros inesperados.
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        if conn:
            cur.close()
            conn.close()

# GET Endpoints com Filtros
@app.get("/items", summary="Lista e filtra os itens do patrimônio")
async def get_items(
    search: Optional[str] = None,
    tiporecursofisico: Optional[str] = None,
    statusitem: Optional[str] = None,
    qualidade: Optional[str] = None,
    armazem: Optional[str] = None
):
    """
    Endpoint para consulta de itens com filtros dinâmicos.
    A query SQL é construída dinamicamente no backend com base nos parâmetros
    fornecidos pelo usuário, utilizando uma query base do arquivo `filter_items.sql`.
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        base_query = load_sql_query("filter_items")

        params = []
        where_clauses = []

        # Adiciona cláusulas WHERE e parâmetros conforme os filtros são aplicados.
        if tiporecursofisico and tiporecursofisico != "all":
            where_clauses.append("trf.IDTIPORECURSO = %s")
            params.append(tiporecursofisico)
        if statusitem and statusitem != "all":
            where_clauses.append("i.STATUSITEM = %s")
            params.append(statusitem)
        if qualidade and qualidade != "all":
            where_clauses.append("i.QUALIDADE = %s")
            params.append(qualidade)
        if armazem and armazem != "all":
            where_clauses.append("a.IDARMAZEM = %s")
            params.append(armazem)
        if search:
            where_clauses.append("i.NROPATRIMONIO ILIKE %s")
            params.append(f"%{search}%")

        # Constrói a query final.
        if where_clauses:
            final_query = base_query + " WHERE " + " AND ".join(where_clauses)
        else:
            final_query = base_query

        cur.execute(final_query, tuple(params))
        items = cur.fetchall()
        cur.close()
        conn.close()

        # Mapeia o resultado da tupla para um dicionário JSON.
        result = []
        for item in items:
            result.append({
                "nropatrimonio": item[0],
                "statusitem": item[1],
                "qualidade": item[2],
                "tamanho": item[3],
                "tiporecursofisico": {"nome": item[4]},
                "armazem": {"idarmazem": item[5], "endereco": item[6]} if item[5] else None,
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch items: {e}")

@app.get("/tipos-recurso", summary="Lista os tipos de recurso físico")
async def get_tipos_recurso():
    """Endpoint para obter os tipos de recursos físicos disponíveis para os filtros."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_tiporecursofisico")
        cur.execute(query)
        tipos = cur.fetchall()
        cur.close()
        conn.close()
        return [{"idtiporecurso": tipo[0], "nome": tipo[1]} for tipo in tipos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch resource types: {e}")

@app.get("/armazens", summary="Lista os armazéns")
async def get_armazens():
    """Endpoint para obter os armazéns disponíveis para os filtros."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        query = load_sql_query("get_all_armazem")
        cur.execute(query)
        armazens = cur.fetchall()
        cur.close()
        conn.close()
        return [{"idarmazem": armazem[0], "endereco": armazem[1]} for armazem in armazens]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch warehouses: {e}")
