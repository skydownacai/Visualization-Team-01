import api
import sqlite3

def test_db_connection():
    """测试数据库连接"""
    try:
        conn = sqlite3.connect('novaviz.db')
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print("数据库中的表：")
        for table in tables:
            print(f"- {table[0]}")
        
        # 检查Data_TitleInfo表的结构
        cursor.execute("PRAGMA table_info(Data_TitleInfo)")
        columns = cursor.fetchall()
        print("\nData_TitleInfo表结构：")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
            
        # 获取题目类型相关的示例数据
        cursor.execute("""
            SELECT DISTINCT title_ID, knowledge, sub_knowledge, difficulty, score
            FROM Data_TitleInfo
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\n题目信息示例（前5条）：")
        for sample in samples:
            print(f"- 题目ID: {sample[0]}")
            print(f"  知识点: {sample[1]}")
            print(f"  子知识点: {sample[2]}")
            print(f"  难度: {sample[3]}")
            print(f"  分值: {sample[4]}")
        
        # 检查submit_records表的结构
        cursor.execute("PRAGMA table_info(submit_records)")
        columns = cursor.fetchall()
        print("\nsubmit_records表结构：")
        for col in columns:
            print(f"- {col[1]} ({col[2]})")
        
        # 获取一些示例数据
        cursor.execute("""
            SELECT student_ID, class, COUNT(*) as count 
            FROM submit_records 
            GROUP BY student_ID, class 
            ORDER BY count DESC 
            LIMIT 5
        """)
        samples = cursor.fetchall()
        print("\n示例学生数据（前5条）：")
        for sample in samples:
            print(f"- 学生ID: {sample[0]}, 班级: {sample[1]}, 提交次数: {sample[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"错误：{str(e)}")

if __name__ == "__main__":
    print("测试数据库连接和结构：")
    print("-" * 50)
    test_db_connection() 