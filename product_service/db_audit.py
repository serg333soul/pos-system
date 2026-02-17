import os
from sqlalchemy import create_engine, inspect

# Отримуємо URL бази з оточення (як у проекті)
USER = os.getenv("POSTGRES_USER", "user")
PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
DB_NAME = os.getenv("POSTGRES_DB", "products_db")
HOST = os.getenv("DB_HOST", "pos_postgres") # Для локального запуску поза Docker змініть на localhost

SQLALCHEMY_DATABASE_URL = f"postgresql://{USER}:{PASSWORD}@{HOST}/{DB_NAME}"

def audit_schema():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    inspector = inspect(engine)
    
    output_file = "db_schema_audit.txt"
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("📊 АУДИТ СТРУКТУРИ БАЗИ ДАНИХ POS-СИСТЕМИ\n")
        f.write("="*40 + "\n\n")
        
        for table_name in inspector.get_table_names():
            f.write(f"📋 ТАБЛИЦЯ: {table_name}\n")
            f.write("-" * 30 + "\n")
            
            columns = inspector.get_columns(table_name)
            for column in columns:
                col_name = column['name']
                col_type = column['type']
                nullable = "NULL" if column['nullable'] else "NOT NULL"
                default = f" DEFAULT {column['default']}" if column.get('default') else ""
                
                f.write(f"  🔹 {col_name:20} | {str(col_type):15} | {nullable}{default}\n")
            f.write("\n")
            
    print(f"✅ Аудит завершено! Результат записано у файл: {output_file}")

if __name__ == "__main__":
    audit_schema()