# **NovaViz** : **NorthClass Smart Visual Analytics Platform for Programming Courses**

**authors (Team 01)**:  Liu jiacai,  He Ze, Wei Xiaoyu, Ruan Tianhao, Zhao Jiayin

**document** :  https://rg975ojk5z.feishu.cn/wiki/XIsgwjoLaiXSIhkZf2ac7n6CnHg?from=from_copylink


## Quick Start 

### 1. 前端依赖安装
1. 安装nodejs / npm，可以网上参考文章例如 https://www.cnblogs.com/zsg88/p/18266130
安装完成后保证node -v 和 npm -v 能正常输出
2. cd chat-interface 目录 后 执行 npm install 安装依赖

### 2. 安装后端依赖

```bash
pip install -r requirements.txt 
```
(这个是我本地所有依赖，可能有不需要的包，可以先直接运行)


### 3. 启动后端

运行 wb_backend.py 就可以启动后端

![image-20250602134038156](pics\1.png)

显示 WebSocket服务器启动在端口3001... 的字样就表明成功了

### 4. 启动前端

命令行cd 到 chat-interface目录后 执行 npm start 

如果提示

![image-20250602134136565](pics\2.png)

并且浏览器能打开 http://localhost:3000/ 就表明启动成功

同时请按F12（谷歌浏览器，其他浏览器可能不一样）打开浏览器控制台，如果最后一条消息提示  WebSocket连接已建立 表明和后端成功连接

![image-20250602134206538](pics\3.png)

### 4. 工具编辑和增加

找到 lm_backend.py 中的 tools 变量，如下代码块

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_system_data_info",
            "description": "获取Novaviz系统的数据库信息,返回一个markdown格式的表格"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_accuracy",
            "description": "获取学习行为数据中[知识点]与[子知识点]的整体正确率(不做不同班级之间的比较)，返回一个字符串，字符串中包含[知识点]与[子知识点]的正确率数据与可视化图链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_dt": {"type": "string", "description": "开始日期,格式为YYYY-MM-DD,如果为空，则默认使用数据库中最早的时间"},
                    "end_dt": {"type": "string", "description": "结束日期,格式为YYYY-MM-DD,如果为空，则默认使用数据库中最大的时间"},
                    "class_id": {"type": "string", "description": "需要考虑的班级ID,值为数字1到15,多个班级用英文的逗号,分开.如果为空，则默认使用所有班级"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_accuracy_compare",
            "description": "获取学习行为数据中[知识点]正确率在不同班级之间的比较，返回一个字符串，字符串中包含[知识点]的不同班级的正确率数据与可视化图链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_dt": {"type": "string", "description": "开始日期,格式为YYYY-MM-DD,如果为空，则默认使用数据库中最早的时间"},
                    "end_dt": {"type": "string", "description": "结束日期,格式为YYYY-MM-DD,如果为空，则默认使用数据库中最大的时间"},
                    "class_id": {"type": "string", "description": "需要比较的班级ID,值为数字1到15,多个班级用英文的逗号,分开.如果为空，则默认使用所有班级"}
                },
                "required": ["class_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_time_consumption_distribution",
            "description": "获取学习行为数据中不同[知识点]答题耗时分布数据(不做不同班级之间的比较)，返回一个字符串，字符串中包含不同[知识点]的答题耗时分布数据与可视化图链接。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_dt": {"type": "string", "description": "开始日期,格式为YYYY-MM-DD,如果为空，则默认使用数据库中最早的时间"},
                    "end_dt": {"type": "string", "description": "结束日期,格式为YYYY-MM-DD,如果为空，则默认使用数据库中最大的时间"},
                    "class_id": {"type": "string", "description": "需要考虑的班级ID,值为数字1到15,多个班级用英文的逗号,分开.如果为空，则默认使用所有班级"}
                }
            }
        }
    },
]
```

往这个列表里面添加字典元素即可增加llm 使用的工具，字典元素中：

type 键 一定是 对应function 值

function 键 对应一个字典，定义具体函数，字典内部：

1. name 键 对应函数名称，一定要在 api.py 中定义相同名称的函数 
2. description 键 对应函数的描述，一定要说清楚函数的功能，以及返回值，方便让llm 参考
3. parameters 键 定义函数的参数，如果函数是没有参数的，不要这个键即可

请注意： 对应的函数一定要在 api.py 中定义中进行实现，例如第一个工具 get_system_data_info，在api.py中就有如下实现：

```python
def get_system_data_info(*args,**kwargs):
    conn = sqlite3.connect('novaviz.db')
    # 获取所有表名
    tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
    tables = pd.read_sql_query(tables_query, conn)
    
    result = "## 数据库表信息\n\n"
    
    # 获取时间范围
    time_range_query = """
    SELECT 
        datetime(MIN(time), 'unixepoch') as min_time,
        datetime(MAX(time), 'unixepoch') as max_time
    FROM submit_records
    """
    time_range = pd.read_sql_query(time_range_query, conn)
    result += f"### 数据时间范围\n"
    result += f"开始时间: {time_range['min_time'][0]}\n"
    result += f"结束时间: {time_range['max_time'][0]}\n\n"
    
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
```

函数的返回值，是字符串就好，用于提示大模型可以参考的内容。如果你想让大模型输出图片，直接把图片链接贴到函数返回的文本值里面，例如**get_time_consumption_distribution** 工具对应函数的返回值为:

```python
    ut = int(time.time())
    temp_file = 'tmp/time_consumption_distribution_{}.png'.format(ut)
    plt.savefig(temp_file,dpi=300)
    plt.close()
    result = "各知识点答题耗时分布数据(key:知识点,value:{min,q1,median,q3,max}) : " + json.dumps(box_data_dict) + "\n" \
           + "结果可视化图片地址 : " + "http://localhost:3001/" + temp_file
    return result
```

图片请一定保存到 tmp/ 子目录下，提示llm的图片链接一定是 "http://localhost:3001/tmp/"+图片名称的格式

写好一个工具后，可以在运行 api.py 调试你的函数看是否返回正确, 调试函数类似于下面用法

```python

if __name__ == "__main__":
    get_time_consumption_distribution()

```

添加完工具调试也没问题后，重新运行 wb_backend.py 后端，重启后前端直接在浏览器里面重新刷新，控制台输出” WebSocket连接已建立“ 表明重新连接上了后端，然后你就可以问对应问题，看是否返回了
