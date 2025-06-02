import os
import pandas as pd
import sqlite3
from pathlib import Path

# 将csv数据写入sqlite3 数据库 novaviz.db


# 连接到SQLite数据库
conn = sqlite3.connect('novaviz.db')

# 获取datas根目录下所有csv文件
data_dir = Path('datas')
csv_files = list(data_dir.glob('*.csv')) + list(data_dir.glob('*.xlsx'))

for csv_file in csv_files:
    try:
        # 读取CSV文件
        df = pd.read_csv(csv_file)
        
        # 使用文件名(不含扩展名)作为表名
        table_name = csv_file.stem
        
        # 将数据写入SQLite数据库
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"成功导入 {csv_file} 到表 {table_name}")
        
    except Exception as e:
        print(f"处理 {csv_file} 时出错: {str(e)}")

# 关闭数据库连接
conn.close()



# 处理Data_SubmitRecord目录下的提交记录数据
submit_record_dir = Path('datas/Data_SubmitRecord')
submit_record_files = list(submit_record_dir.glob('*.csv'))

# 创建一个空的DataFrame用于存储合并后的数据
merged_df = pd.DataFrame()

# 连接数据库
conn = sqlite3.connect('novaviz.db')

for submit_file in submit_record_files:
    try:
        # 从文件名中提取班级ID
        class_id = submit_file.stem
        
        # 读取CSV文件
        df = pd.read_csv(submit_file)
        
        # 合并到主DataFrame
        if merged_df.empty:
            merged_df = df
        else:
            merged_df = pd.concat([merged_df, df], ignore_index=True)
            
        print(f"成功处理班级 {class_id} 的提交记录")
        
    except Exception as e:
        print(f"处理 {submit_file} 时出错: {str(e)}")

# 将合并后的数据写入数据库
if not merged_df.empty:
    merged_df.to_sql('submit_records', conn, if_exists='replace', index=False)
    print("成功将所有提交记录合并并导入到数据库")

# 关闭数据库连接
conn.close()
