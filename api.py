import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import warnings
import json
import base64
import os
import time
from collections import defaultdict

warnings.filterwarnings('ignore')

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

# 连接到SQLite数据库


def process_time_range(**kwargs):
    start_dt = kwargs.get('start_dt', None)
    end_dt = kwargs.get('end_dt', None)
    try:
        start_ts = datetime.strptime(start_dt.strip(), '%Y-%m-%d').timestamp() if start_dt else None
        start_ts = int(start_ts)
    except:
        start_ts = None
    try:
        end_ts = datetime.strptime(end_dt.strip(), '%Y-%m-%d').timestamp() if end_dt else None
        end_ts = int(end_ts)
    except:
        end_ts = None
    return start_dt,start_ts,end_dt,end_ts


def process_class_id(**kwargs):
    if kwargs.get('class_id'):
        class_ids = kwargs.get('class_id').replace("，",",").split(',')
        class_conditions = [f"'Class{class_id.strip()}'" for class_id in class_ids]
    else:
        class_ids = None
        class_conditions = None
    return class_ids,class_conditions

def get_filter_rule(only_time = False,**kwargs):

    filter_query = ""
    start_dt,start_ts,end_dt,end_ts = process_time_range(**kwargs)
    if start_ts is not None and end_ts is not None:
        filter_query += f" AND sr.time >= {start_ts} AND sr.time <= {end_ts}"

    if not only_time:
        class_ids,class_conditions = process_class_id(**kwargs)
        if class_conditions is not None:
            filter_query += f" AND sr.class IN ({','.join(class_conditions)})"
    else:
        class_ids = None
    if not only_time:
        filter_title = "({} - {},class:{})".format(start_dt if start_dt else "",end_dt if end_dt else "",",".join(class_ids) if class_ids else "all")
    else:
        filter_title = "({} - {})".format(start_dt if start_dt else "",end_dt if end_dt else "")
    return filter_query,filter_title

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

def get_knowledge_accuracy(*args,**kwargs):
    conn = sqlite3.connect('novaviz.db')
    # 获取完整数据
    
    query = """
    SELECT sr.*, ti.title_ID, ti.knowledge, ti.sub_knowledge, ti.score as max_score, si.student_ID
    FROM submit_records sr
    JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
    JOIN Data_StudentInfo si ON sr.student_ID = si.student_ID
    """
    filter_query,filter_title = get_filter_rule(**kwargs)
    query += filter_query
    df = pd.read_sql_query(query, conn)

    conn.close()
    knowledges = df['knowledge'].unique().tolist()
    knowledges = list(sorted(knowledges))
    # 创建两个子图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    timestamps = pd.to_datetime(df["time"]*1000,unit='ms')

    # 绘制知识点正确率柱状图
    knowledge_accuracies = {}
    colors = []
    for knowledge in knowledges:
        knowledge_df = df[df['knowledge']==knowledge]
        correct_num = knowledge_df[knowledge_df['state']=='Absolutely_Correct'].shape[0]
        accuracy = correct_num/knowledge_df.shape[0]
        knowledge_accuracies[knowledge] = accuracy
        colors.append(plt.cm.Set3(list(knowledges).index(knowledge)))
        
    bars1 = ax1.bar(knowledge_accuracies.keys(), knowledge_accuracies.values(), color=colors)
    ax1.set_title(f'知识点正确率{filter_title}')
    ax1.set_xlabel('知识点')
    ax1.set_ylabel('正确率')
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 在柱状图上添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1%}',
                ha='center', va='bottom')
    
    # 绘制子知识点正确率柱状图,按知识点分组
    sub_knowledge_accuracies = {}
    x_positions = []
    x_labels = []
    values = []
    colors = []
    current_pos = 0
    
    for knowledge in knowledges:
        # 获取该知识点下的所有子知识点
        knowledge_subs = df[df['knowledge']==knowledge]['sub_knowledge'].unique()
        
        for sub_knowledge in knowledge_subs:
            sub_knowledge_df = df[df['sub_knowledge']==sub_knowledge]
            correct_num = sub_knowledge_df[sub_knowledge_df['state']=='Absolutely_Correct'].shape[0]
            accuracy = correct_num/sub_knowledge_df.shape[0]
            x_positions.append(current_pos)
            x_labels.append(sub_knowledge)
            values.append(accuracy)
            colors.append(plt.cm.Set3(list(knowledges).index(knowledge)))
            current_pos += 1
            sub_knowledge_accuracies[sub_knowledge] = accuracy
        current_pos += 1  # 不同知识点之间留空
        
    bars2 = ax2.bar(x_positions, values, color=colors)
    ax2.set_xticks(x_positions)
    ax2.set_xticklabels(x_labels)
    ax2.set_title(f'子知识点正确率(按知识点分组){filter_title}')
    ax2.set_xlabel('子知识点')
    ax2.set_ylabel('正确率')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 在柱状图上添加数值标签
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1%}',
                ha='center', va='bottom')
    
    plt.tight_layout()
    
    # 保存图片到临时文件
    ut = int(time.time())
    temp_file = 'tmp/knowledge_accuracy_{}.png'.format(ut)
    plt.savefig(temp_file,dpi=300)
    plt.close()
    
    result = "知识点正确率数据数据(key:知识点,value:正确率) : " + json.dumps(knowledge_accuracies) + "\n" \
           + "子知识点正确率数据数据(key:子知识点,value:正确率) : " + json.dumps(sub_knowledge_accuracies) + "\n" \
           + "结果可视化图片地址 : " + "http://localhost:3001/" + temp_file
    
    return result

def get_knowledge_accuracy_compare(*args,**kwargs):
    conn = sqlite3.connect('novaviz.db')
    # 获取完整数据

    query = """
    SELECT sr.*, ti.title_ID, ti.knowledge, ti.sub_knowledge, ti.score as max_score, si.student_ID
    FROM submit_records sr
    JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
    JOIN Data_StudentInfo si ON sr.student_ID = si.student_ID
    """
    filter_query,filter_title = get_filter_rule(**kwargs)
    query += filter_query
    df = pd.read_sql_query(query, conn)
    conn.close()
    knowledges = df['knowledge'].unique().tolist()
    knowledges = list(sorted(knowledges))
    # 创建两个子图
    fig = plt.figure()

    # 绘制知识点正确率柱状图
    knowledge_accuracies = defaultdict(dict)
    class_ids = kwargs.get('class_id')
    if class_ids is None:
        return "Error : 请提供正确的class_id参数"    
    class_ids = class_ids.replace("，",",").split(',')
    class_conditions = [f"Class{class_id.strip()}" for class_id in class_ids]
    
    # 为每个班级分配不同颜色
    colors = plt.cm.Set3(np.linspace(0, 1, len(class_conditions)))
    
    # 设置柱状图的宽度和位置
    bar_width = 0.8 / len(class_conditions)
    x = np.arange(len(knowledges))
    

    for knowledge in knowledges:
        knowledge_df = df[df['knowledge']==knowledge]
        valid_classes = knowledge_df['class'].unique()
        for class_condition in class_conditions:
            knowledge_df_class = knowledge_df[knowledge_df['class']==class_condition]
            correct_num = knowledge_df_class[knowledge_df_class['state']=='Absolutely_Correct'].shape[0]            
            if knowledge_df_class.shape[0] > 0:
                accuracy = correct_num/knowledge_df_class.shape[0]
            else:
                accuracy = None
            knowledge_accuracies[knowledge][class_condition] = accuracy
        
        # 绘制柱状图,每个班级一个颜色
        for i, class_condition in enumerate(class_conditions):
            accuracies = [knowledge_accuracies[k][class_condition] for k in [knowledge]]
            # 过滤掉None值
            if accuracies[0] is not None:
                plt.bar(x[knowledges.index(knowledge)] + i*bar_width, accuracies[0], 
                       bar_width, label=class_condition if knowledge == knowledges[0] else "",
                       color=colors[i])
                # 添加数值标签
                plt.text(x[knowledges.index(knowledge)] + i*bar_width, accuracies[0], 
                        f'{accuracies[0]:.1%}', ha='center', va='bottom')

    plt.xlabel('知识点')
    plt.ylabel('正确率')
    plt.title('不同班级各知识点正确率对比'+filter_title)
    plt.xticks(x + bar_width*(len(class_conditions)-1)/2, knowledges, rotation=45)
    plt.legend()
    plt.tight_layout()
    # 保存图片到临时文件
    ut = int(time.time())
    temp_file = 'tmp/knowledge_accuracy_class_compare_{}.png'.format(ut)
    plt.savefig(temp_file,dpi=300)
    plt.close()
    result = "各知识点不同班级正确率对比数据(key:知识点,value:{班级ID,value:正确率}) : " + json.dumps(knowledge_accuracies) + "\n" \
           + "结果可视化图片地址 : " + "http://localhost:3001/" + temp_file
    return result

def get_top10_student_of_knowledge(*args,**kwargs):
    conn = sqlite3.connect('novaviz.db')
    # 获取完整数据

    query = """
    SELECT sr.*, ti.title_ID, ti.knowledge, ti.sub_knowledge, ti.score as max_score, si.student_ID
    FROM submit_records sr
    JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
    JOIN Data_StudentInfo si ON sr.student_ID = si.student_ID
    """
    filter_query,filter_title = get_filter_rule(**kwargs)
    query += filter_query
    df = pd.read_sql_query(query, conn)
    conn.close()
    knowledges = df['knowledge'].unique().tolist()
    knowledges = list(sorted(knowledges))
    # 创建两个子图
    fig = plt.figure()





def get_time_consumption_distribution(*args,**kwargs):
    conn = sqlite3.connect('novaviz.db')
    # 获取完整数据
    query = """
    SELECT sr.*, ti.title_ID, ti.knowledge, ti.sub_knowledge, ti.score as max_score, si.student_ID
    FROM submit_records sr
    JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
    JOIN Data_StudentInfo si ON sr.student_ID = si.student_ID
    """
    filter_query,filter_title = get_filter_rule(**kwargs)
    query += filter_query
    df = pd.read_sql_query(query, conn)
    conn.close()

    # 按知识点分组计算耗时统计
    knowledges = df['knowledge'].unique().tolist()
    knowledges = list(sorted(knowledges))

    # 创建箱线图
    plt.figure()
    box_datas = []
    box_data_dict = {}
    for k in knowledges:
        knowledge_df = df[df['knowledge']==k]
        # 过滤掉非数值型数据(如'--')并转换为float
        time_consumption = knowledge_df[knowledge_df['timeconsume'].str.match(r'^\d+\.?\d*$')]['timeconsume'].astype(float).tolist()
        box_datas.append(time_consumption)
        box_data_dict[k] = {
            'min': float(np.min(time_consumption)),
            'q1': float(np.percentile(time_consumption, 25)),
            'median': float(np.median(time_consumption)),
            'q3': float(np.percentile(time_consumption, 75)),
            'max': float(np.max(time_consumption)),
        }
    
    plt.boxplot(box_datas, labels=knowledges)
    plt.xticks(rotation=45)
    plt.title('不同知识点答题耗时分布(毫秒)'+filter_title)
    plt.ylabel('耗时(ms)')
    plt.xlabel('知识点')
    plt.tight_layout()

    # 保存图片
    ut = int(time.time())
    temp_file = 'tmp/time_consumption_distribution_{}.png'.format(ut)
    plt.savefig(temp_file,dpi=300)
    plt.close()
    result = "各知识点答题耗时分布数据(key:知识点,value:{min,q1,median,q3,max}) : " + json.dumps(box_data_dict) + "\n" \
           + "结果可视化图片地址 : " + "http://localhost:3001/" + temp_file
    return result




if __name__ == "__main__":
    get_time_consumption_distribution()

