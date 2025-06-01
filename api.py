import sqlite3
import pandas as pd

# 连接到SQLite数据库

def get_system_data_info(*args,**kwargs):
    conn = sqlite3.connect('novaviz.db')
    # 获取所有表名
    tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
    tables = pd.read_sql_query(tables_query, conn)
    
    result = "## 数据库表信息\n\n"
    
    for table in tables['name']:
        # 获取表结构
        schema_query = f"PRAGMA table_info('{table}')"
        schema = pd.read_sql_query(schema_query, conn)
        
        # 获取数据量
        count_query = f"SELECT COUNT(*) as count FROM {table}"
        count = pd.read_sql_query(count_query, conn)['count'][0]
        
        # 构建表格
        result += f"### {table}\n"
        result += "| 字段名 | 类型 | 是否可空 | 默认值 |\n"
        result += "|--------|------|----------|--------|\n"
        
        for _, row in schema.iterrows():
            result += f"| {row['name']} | {row['type']} | {'是' if row['notnull']==0 else '否'} | {row['dflt_value'] if row['dflt_value'] else '-'} |\n"
            
        result += f"\n总数据量: {count} 条记录\n\n"
    
    conn.close()
    return result
print(get_system_data_info())


