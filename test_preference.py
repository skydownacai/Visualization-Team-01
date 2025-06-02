import api
import traceback

def test_student_preference():
    """测试学生知识点偏好分析"""
    # 测试最活跃的学生
    student_id = '882ccee198e25b49b30d'  # Class10的最活跃学生
    
    print(f"开始分析学生 {student_id} 的知识点偏好...")
    try:
        # 首先测试数据库连接
        print("\n1. 测试数据库连接...")
        conn = api.get_db_connection()
        print("数据库连接成功！")
        conn.close()
        
        # 然后获取学生信息
        print("\n2. 获取学生基本信息...")
        student_info = api.get_available_student_info()
        print(student_info)
        
        # 最后进行知识点偏好分析
        print("\n3. 进行知识点偏好分析...")
        result = api.get_knowledge_preference(student_id=student_id)
        print("\n分析结果：")
        print(result)
        
    except Exception as e:
        print(f"\n错误：{str(e)}")
        print("\n详细错误信息：")
        traceback.print_exc()

if __name__ == "__main__":
    print("="*50)
    print("开始测试知识点偏好分析功能")
    print("="*50)
    test_student_preference() 