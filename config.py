from urllib.parse import quote_plus

params = quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=DESKTOP-85VJOVQ\\SQLEXPRESS;"
    "DATABASE=newssystem;"
    "UID=sa;"
    "PWD=123"
)

SQLALCHEMY_DATABASE_URI = f"mssql+pyodbc:///?odbc_connect={params}"
