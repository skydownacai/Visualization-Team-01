import sqlite3
import pandas as pd

conn = sqlite3.connect('novaviz.db')
query = "SELECT DISTINCT title_ID, score, knowledge FROM Data_TitleInfo"
df = pd.read_sql_query(query, conn)
print("\n题目分数分布：")
print(df['score'].value_counts().sort_index())
print("\n知识点分布：")
print(df['knowledge'].value_counts())
print("\n按知识点统计的平均分数：")
print(df.groupby('knowledge')['score'].mean().sort_values(ascending=False))
conn.close() 