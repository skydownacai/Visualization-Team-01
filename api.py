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
    temp_file = 'tmp/knowledge_accuracy.png'
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
    temp_file = 'tmp/knowledge_accuracy_compare.png'
    plt.savefig(temp_file,dpi=300)
    plt.close()
    result = "各知识点不同班级正确率对比数据(key:知识点,value:{班级ID,value:正确率}) : " + json.dumps(knowledge_accuracies) + "\n" \
           + "结果可视化图片地址 : " + "http://localhost:3001/" + temp_file
    return result




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
    temp_file = 'tmp/time_consumption_distribution.png'
    plt.savefig(temp_file,dpi=300)
    plt.close()
    result = "各知识点答题耗时分布数据(key:知识点,value:{min,q1,median,q3,max}) : " + json.dumps(box_data_dict) + "\n" \
           + "结果可视化图片地址 : " + "http://localhost:3001/" + temp_file
    return result

def get_hard_title(knowledge="r8S3g"):
    """
    通过可视分析找出难度过高题目
    """
    if isinstance(knowledge,str) and knowledge.strip() == "":
        knowledge = "r8S3g"
    
    conn = sqlite3.connect('novaviz.db')
    
    # 获取数据
    query = """
    SELECT sr.*, ti.title_ID, ti.knowledge, ti.sub_knowledge, 
           ti.score as max_score, si.student_ID
    FROM submit_records sr
    JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
    JOIN Data_StudentInfo si ON sr.student_ID = si.student_ID
    WHERE ti.knowledge = ?
    """
    df = pd.read_sql_query(query, conn, params=([knowledge]))
    conn.close()
    
    if df.empty:
        return "Error: 未找到该知识点的相关数据"
    
    df = df.loc[:, ~df.columns.duplicated()]
    # 计算每个学生在该知识点的平均得分率
    student_scores = df.groupby('student_ID').apply(
        lambda x: (x['score'].astype(float) / x['max_score'].astype(float)).mean()
    ).to_dict()

    # 准备散点图数据
    scatter_data = []
    title_ids = df['title_ID'].unique().tolist()
    title_ids = sorted(title_ids)

    # 收集所有数据点
    for title_id in title_ids:
        title_df = df[df['title_ID'] == title_id]
        valid_students = title_df['student_ID'].unique()
        
        for student_id in valid_students:
            if student_id in student_scores:
                student_title_df = title_df[title_df['student_ID'] == student_id]
                if not student_title_df.empty:
                    score_ratio = (student_title_df['score'].astype(float) / 
                                 student_title_df['max_score'].astype(float)).mean()
                    correct_rate = (student_title_df['state'] == 'Absolutely_Correct').mean()
                    scatter_data.append({
                        'title_id': f'题目{title_id}',
                        'knowledge_score': student_scores[student_id],
                        'title_score': score_ratio,
                        'correct_rate': correct_rate
                    })

    # 转换为DataFrame
    scatter_df = pd.DataFrame(scatter_data)

    # 创建画布
    plt.figure(figsize=(10, 8))
    sns.scatterplot(data=scatter_df, 
                   x='knowledge_score', 
                   y='title_score',
                   hue='title_id',
                   s=20,
                   alpha=0.6,
                   palette='deep')

    plt.plot([0, 1], [0, 1], 'k--', alpha=0.5)  # 对角线
    plt.xlabel('学生知识点整体掌握度(平均得分率)')
    plt.ylabel('学生在具体题目上的得分率')
    plt.title(f'{knowledge}知识点掌握度散点图')
    plt.legend(title='题目', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.2)
    plt.tight_layout()

    # 保存散点图
    ut = int(time.time())
    scatter_file = f'tmp/knowledge_scatter.png'
    plt.savefig(scatter_file, dpi=300, bbox_inches='tight')
    plt.close()

    # 定义高分学生
    good_students = df[df['student_ID'].isin(
        [k for k, v in student_scores.items() if v > 0.7]
    )]

    # 创建柱状图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))

    # 1. 各题目平均正确率柱状图
    title_means = scatter_df.groupby('title_id')['correct_rate'].mean()
    bars1 = ax1.bar(title_means.index, title_means.values)
    ax1.set_title(f'{knowledge}知识点各题目平均正确率')
    ax1.set_xlabel('题目')
    ax1.set_ylabel('平均正确率')
    ax1.tick_params(axis='x', rotation=45)
    
    # 添加数值标签
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2%}',
                ha='center', va='bottom')

    # 2. 高分学生各题目正确率柱状图
    if not good_students.empty:
        title_scores_good = {}
        for title_id in title_ids:
            title_df = good_students[good_students['title_ID'] == title_id]
            if not title_df.empty:
                correct_rate = (title_df['state'] == 'Absolutely_Correct').mean()
                title_scores_good[f'题目{title_id}'] = correct_rate

        bars2 = ax2.bar(title_scores_good.keys(), title_scores_good.values())
        ax2.set_title(f'{knowledge}知识点高分学生(>70%)各题目平均正确率')
        ax2.set_xlabel('题目')
        ax2.set_ylabel('平均正确率')
        ax2.tick_params(axis='x', rotation=45)
        
        # 添加数值标签
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.2%}',
                    ha='center', va='bottom')
    else:
        ax2.text(0.5, 0.5, '没有学生的平均得分率超过70%',
                ha='center', va='center',
                transform=ax2.transAxes)

    plt.tight_layout()

    # 保存柱状图
    bars_file = f'tmp/knowledge_bars.png'
    plt.savefig(bars_file, dpi=300, bbox_inches='tight')
    plt.close()

    # 分析高分学生的题目难度
    difficult_titles = []
    if not good_students.empty:
        for title_id in title_ids:
            title_df = good_students[good_students['title_ID'] == title_id]
            if not title_df.empty:
                correct_rate = (title_df['state'] == 'Absolutely_Correct').mean()
                title_scores_good[f'题目{title_id}'] = correct_rate
                # 检查正确率是否低于60%
                if correct_rate < 0.6:
                    difficult_titles.append(title_id)
    # 创建箱线图
    plt.figure(figsize=(10, 6))  
    
    # 准备箱线图数据
    good_box_data = []
    all_box_data = []
    box_labels = []
    
    # 获取高分学生ID列表
    good_student_ids = [k for k, v in student_scores.items() if v > 0.7]
    
    # 按题目收集数据
    for title_id in title_ids:
        title_data = scatter_df[scatter_df['title_id'] == f'题目{title_id}']
        
        # 所有学生的正确率
        all_box_data.append(title_data['correct_rate'].tolist())
        
        # 高分学生的正确率
        good_student_data = title_data[title_data['knowledge_score'] > 0.7]['correct_rate'].tolist()
        good_box_data.append(good_student_data)
        
        box_labels.append(f'题目{title_id}')

    # 设置箱线图位置
    positions = np.arange(len(box_labels)) * 3
    width = 0.8

    # 绘制两组箱线图
    bp1 = plt.boxplot(all_box_data, positions=positions - width/2, widths=width,
                    patch_artist=True, labels=[''] * len(box_labels))
    bp2 = plt.boxplot(good_box_data, positions=positions + width/2, widths=width,
                    patch_artist=True, labels=[''] * len(box_labels))

    # 设置颜色
    plt.setp(bp1['boxes'], facecolor='lightblue', alpha=0.6)
    plt.setp(bp2['boxes'], facecolor='lightgreen', alpha=0.6)

    # 设置图表样式
    plt.title(f'{knowledge}知识点学生群体对比')
    plt.xlabel('题目')
    plt.ylabel('正确率')
    plt.xticks(positions, box_labels, rotation=45)
    plt.grid(True, alpha=0.2)

    # 修改图例位置到标题右侧，图表上方
    plt.legend([bp1['boxes'][0], bp2['boxes'][0]], 
              ['所有学生', '高分学生(知识掌握度>70%)'],
              loc='upper right',
              bbox_to_anchor=(1, 1.2))  # 将图例放在标题右侧上方

    # 调整布局，为图例留出空间
    plt.tight_layout()
    plt.subplots_adjust(top=0.85)  # 调整上边界，为图例留出空间

    # 保存箱线图
    boxplot_file = f'tmp/knowledge_boxplot.png'
    plt.savefig(boxplot_file, dpi=300, bbox_inches='tight')
    plt.close()


    # 生成分析结果
    analysis_result = ""
    if difficult_titles:
        analysis_result = f"根据学生知识点掌握散点图的分布与该知识点各题目平均正确率柱状图的分析，题目 {', '.join(['题目'+str(tid) for tid in difficult_titles])} 的难度相对过高,知识掌握度很高的学习者在这些题目上正确率依旧没有超过60%，意味着题目难度可能超过了能力范围，建议对这些题目进行难度调整或重新设计。"
    else:
        analysis_result = "根据学生知识点掌握散点图的分布与该知识点各题目平均正确率柱状图的分析,知识点掌握率较高的学习者在各题目上都保持着较高的正确率，因此该知识点题目难度均在合理范围内"

 
    return (f"散点图可视化地址 : http://localhost:3001/{scatter_file}\n" +
            f"柱状图可视化地址 : http://localhost:3001/{bars_file}\n" +
            f"箱线图可视化地址 : http://localhost:3001/{boxplot_file}\n" +
            f"难度分析：{analysis_result}")



def get_time_pattern_analysis(start_dt=None, end_dt=None, student_id=None, class_id=None):
    """获取用户的时间模式分析"""
    conn = sqlite3.connect('novaviz.db')
    
    # 构建基础查询
    query = """
    SELECT sr.time, sr.student_ID, sr.class
    FROM submit_records sr
    WHERE 1=1
    """
    
    # 添加过滤条件
    params = []
    if start_dt:
        start_ts = int(datetime.strptime(start_dt, '%Y-%m-%d').timestamp())
        query += " AND sr.time >= ?"
        params.append(start_ts)
    if end_dt:
        end_ts = int(datetime.strptime(end_dt, '%Y-%m-%d').timestamp())
        query += " AND sr.time <= ?"
        params.append(end_ts)
    if student_id:
        query += " AND sr.student_ID = ?"
        params.append(student_id)
    if class_id:
        class_ids = [f"Class{cid.strip()}" for cid in class_id.replace("，",",").split(',')]
        placeholders = ','.join(['?' for _ in class_ids])
        query += f" AND sr.class IN ({placeholders})"
        params.extend(class_ids)
    
    # 执行查询
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    
    if len(df) == 0:
        return "未找到符合条件的数据"
    
    # 转换时间戳为datetime
    df['datetime'] = pd.to_datetime(df['time'], unit='s')
    
    # 1. 答题高峰时段分析
    hourly_counts = df['datetime'].dt.hour.value_counts().sort_index()
    
    plt.figure(figsize=(12, 6))
    sns.barplot(x=hourly_counts.index, y=hourly_counts.values)
    plt.title('答题高峰时段分布')
    plt.xlabel('小时')
    plt.ylabel('提交次数')
    
    # 保存图片
    ut = int(time.time())
    peak_hours_file = f'tmp/peak_hours.png'
    plt.savefig(peak_hours_file, dpi=300)
    plt.close()
    
    # 2. 学习频率分析
    daily_counts = df.groupby(df['datetime'].dt.date).size()
    
    plt.figure(figsize=(12, 6))
    sns.histplot(data=daily_counts, bins=30)
    plt.title('每日提交次数分布')
    plt.xlabel('每日提交次数')
    plt.ylabel('天数')
    
    frequency_file = f'tmp/frequency.png'
    plt.savefig(frequency_file, dpi=300)
    plt.close()
    
    # 构建结果文本
    result = "## 时间模式分析\n\n"
    result += "### 答题高峰时段分析\n"
    peak_hour = hourly_counts.idxmax()
    result += f"- 最活跃的时段是 {peak_hour}:00，共有 {hourly_counts[peak_hour]} 次提交\n"
    result += f"- 查看详细分布：http://localhost:3001/{peak_hours_file}\n\n"
    
    result += "### 学习频率分析\n"
    result += f"- 平均每日提交次数：{daily_counts.mean():.2f}\n"
    result += f"- 中位数每日提交次数：{daily_counts.median():.2f}\n"
    result += f"- 查看详细分布：http://localhost:3001/{frequency_file}\n"
    
    return result

def get_db_connection():
    """获取数据库连接，并确保数据库和表存在"""
    try:
        print("尝试连接数据库...")
        conn = sqlite3.connect('novaviz.db')
        print("数据库连接成功")
        
        # 测试连接
        cursor = conn.cursor()
        print("执行表查询...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"找到的表: {tables}")
        
        if not tables:
            raise Exception("数据库中没有任何表")
        return conn
    except Exception as e:
        print(f"数据库连接错误: {str(e)}")
        raise Exception(f"无法连接到数据库: {str(e)}")

def get_available_student_info(class_id=None):
    """获取可用的学生信息"""
    try:
        print("开始获取学生信息...")
        conn = get_db_connection()
        
        # 获取学生提交记录
        query = """
        SELECT DISTINCT sr.student_ID, sr.class, COUNT(*) as submission_count
        FROM submit_records sr
        WHERE 1=1
        """
        
        params = []
        if class_id:
            class_ids = [f"Class{cid.strip()}" for cid in class_id.replace("，",",").split(',')]
            placeholders = ','.join(['?' for _ in class_ids])
            query += f" AND sr.class IN ({placeholders})"
            params.extend(class_ids)
        
        query += " GROUP BY sr.student_ID, sr.class ORDER BY submission_count DESC LIMIT 10"
        
        print(f"执行查询: {query}")
        print(f"参数: {params}")
        
        df = pd.read_sql_query(query, conn, params=params)
        print(f"查询结果: {len(df)} 条记录")
        conn.close()
        
        if len(df) == 0:
            return "未找到任何学生数据"
        
        result = "## 可用学生信息（显示前10名活跃学生）\n\n"
        result += "| 学生ID | 班级 | 提交次数 |\n"
        result += "|--------|------|----------|\n"
        
        for _, row in df.iterrows():
            result += f"| {row['student_ID']} | {row['class']} | {row['submission_count']} |\n"
        
        return result
    except Exception as e:
        print(f"获取学生信息时出错: {str(e)}")
        return f"错误：{str(e)}"

def get_knowledge_preference(student_id=None, class_id=None, start_dt=None, end_dt=None):
    """获取用户的知识点偏好分析"""
    try:
        conn = get_db_connection()
        
        # 首先验证学生ID是否存在
        if student_id:
            verify_query = "SELECT COUNT(*) as count FROM submit_records WHERE student_ID = ?"
            verify_result = pd.read_sql_query(verify_query, conn, params=[student_id])
            if verify_result['count'][0] == 0:
                conn.close()
                return f"错误：未找到学生ID '{student_id}' 的相关记录。\n\n请使用 get_available_student_info() 获取可用的学生ID列表。"
        
        # 构建基础查询，时间戳是秒级的
        query = """
        SELECT 
            datetime(CAST(time as INTEGER), 'unixepoch') as datetime,
            sr.state,
            sr.student_ID,
            sr.class,
            sr.score as achieved_score,
            ti.score as max_score,
            ti.knowledge,
            sr.timeconsume
        FROM submit_records sr
        JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
        WHERE 1=1
        """
        
        # 添加过滤条件，使用秒级时间戳
        params = []
        if start_dt:
            start_ts = int(datetime.strptime(start_dt, '%Y-%m-%d').timestamp())
            query += " AND sr.time >= ?"
            params.append(start_ts)
        if end_dt:
            end_ts = int(datetime.strptime(end_dt, '%Y-%m-%d').timestamp())
            query += " AND sr.time <= ?"
            params.append(end_ts)
        if student_id:
            query += " AND sr.student_ID = ?"
            params.append(student_id)
        if class_id:
            class_ids = [f"Class{cid.strip()}" for cid in class_id.replace("，",",").split(',')]
            placeholders = ','.join(['?' for _ in class_ids])
            query += f" AND sr.class IN ({placeholders})"
            params.extend(class_ids)
        
        # 执行查询
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if len(df) == 0:
            return "未找到符合条件的数据。\n\n请使用 get_available_student_info() 获取可用的学生ID列表。"
        
        # 计算各知识点的统计信息
        stats = []
        for knowledge in df['knowledge'].unique():
            knowledge_df = df[df['knowledge'] == knowledge]
            stats.append({
                'knowledge': knowledge,
                'submission_count': len(knowledge_df),
                'correct_rate': (knowledge_df['state'] == 'Absolutely_Correct').mean(),
                'score_rate': (knowledge_df['achieved_score'] / knowledge_df['max_score']).mean()
            })
        
        stats_df = pd.DataFrame(stats)
        stats_df = stats_df.sort_values('submission_count', ascending=False)
        stats_df = stats_df.set_index('knowledge')
        
        # 可视化部分开始
        fig = plt.figure(figsize=(15, 10))
        
        # 创建两个子图区域：上方为柱状图，下方为饼图
        gs = plt.GridSpec(2, 2, height_ratios=[1.5, 1])
        ax1 = fig.add_subplot(gs[0, :])  # 上方跨两列的柱状图
        ax2 = fig.add_subplot(gs[1, 0])  # 下方左侧的饼图
        ax3 = fig.add_subplot(gs[1, 1])  # 下方右侧的文本说明
        
        # 1. 绘制正确率和得分率对比柱状图
        x = np.arange(len(stats_df.index))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, stats_df['correct_rate'], width, label='完全正确率', color='skyblue')
        bars2 = ax1.bar(x + width/2, stats_df['score_rate'], width, label='得分率', color='lightcoral')
        
        # 设置柱状图的标题和标签
        ax1.set_title('各知识点正确率和得分率对比', pad=20, fontsize=12)
        ax1.set_xlabel('知识点')
        ax1.set_ylabel('比率')
        ax1.set_xticks(x)
        ax1.set_xticklabels(stats_df.index, rotation=45, ha='right')
        ax1.legend()
        
        # 在柱子上添加数值标签
        def autolabel(bars):
            for bar in bars:
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1%}',
                        ha='center', va='bottom')
        
        autolabel(bars1)
        autolabel(bars2)
        
        # 2. 绘制知识点分布饼图
        submission_counts = stats_df['submission_count']
        total_submissions = submission_counts.sum()
        
        # 计算每个知识点的占比并筛选出占比大于1%的部分
        percentages = submission_counts / total_submissions * 100
        significant_mask = percentages > 1  # 筛选占比大于1%的知识点
        
        # 准备饼图数据
        sizes = percentages[significant_mask]
        labels = [f'{idx}\n({val:.1f}%)' for idx, val in zip(stats_df.index[significant_mask], sizes)]
        
        # 如果有占比小于1%的知识点，将它们合并为"其他"
        if not significant_mask.all():
            other_size = percentages[~significant_mask].sum()
            sizes = pd.concat([sizes, pd.Series({'其他': other_size})])
            labels.append(f'其他\n({other_size:.1f}%)')
        
        # 绘制饼图
        wedges, texts, autotexts = ax2.pie(sizes, labels=labels, autopct='',
                                         colors=plt.cm.Pastel1(np.linspace(0, 1, len(sizes))),
                                         startangle=90)
        ax2.set_title('知识点分布', pad=20)
        
        # 3. 在右侧添加统计信息
        ax3.axis('off')  # 关闭坐标轴
        stats_text = f"总体统计信息：\n\n"
        stats_text += f"总提交次数：{total_submissions}\n"
        stats_text += f"覆盖知识点数：{len(stats_df)}\n"
        stats_text += f"整体完全正确率：{(df['state'] == 'Absolutely_Correct').mean():.1%}\n"
        stats_text += f"整体得分率：{(df['achieved_score'] / df['max_score']).mean():.1%}\n\n"
        stats_text += "主要知识点（提交次数）：\n"
        
        # 添加前5个主要知识点的统计
        for idx in stats_df.index[:5]:
            stats_text += f"{idx}: {stats_df.loc[idx, 'submission_count']}次\n"
        
        ax3.text(0, 0.5, stats_text, va='center', fontsize=10)
        
        plt.tight_layout()
        
        ut = int(time.time())
        analysis_file = f'tmp/knowledge_analysis.png'
        plt.savefig(analysis_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        # 构建结果文本
        result = "## 知识点偏好分析\n\n"
        if student_id:
            student_class = df['class'].iloc[0]
            result += f"学生ID: {student_id} (班级: {student_class})\n\n"
        
        result += "### 总体情况\n"
        result += f"- 总提交次数：{total_submissions}\n"
        result += f"- 覆盖知识点数：{len(stats_df)}\n"
        result += f"- 整体完全正确率：{(df['state'] == 'Absolutely_Correct').mean():.1%}\n"
        result += f"- 整体得分率：{(df['achieved_score'] / df['max_score']).mean():.1%}\n\n"
        
        result += "### 各知识点详细统计\n"
        for knowledge in stats_df.index:
            result += f"\n#### {knowledge}\n"
            result += f"- 提交次数：{stats_df.loc[knowledge, 'submission_count']}\n"
            result += f"- 完全正确率：{stats_df.loc[knowledge, 'correct_rate']:.1%}\n"
            result += f"- 得分率：{stats_df.loc[knowledge, 'score_rate']:.1%}\n"
        
        result += f"\n查看详细分析图表：http://localhost:3001/{analysis_file}\n"
        
        return result
    except Exception as e:
        print(f"分析知识点偏好时出错: {str(e)}")
        return f"错误：{str(e)}"

def get_ability_distribution(start_dt=None, end_dt=None, student_id=None, class_id=None):
    """获取用户的能力分布分析"""
    conn = sqlite3.connect('novaviz.db')
    
    # 构建基础查询
    query = """
    SELECT sr.state, sr.student_ID, sr.class, ti.knowledge, ti.score as max_score, sr.score as achieved_score
    FROM submit_records sr
    JOIN Data_TitleInfo ti ON sr.title_ID = ti.title_ID
    WHERE 1=1
    """
    
    # 添加过滤条件
    params = []
    if start_dt:
        start_ts = int(datetime.strptime(start_dt, '%Y-%m-%d').timestamp())
        query += " AND sr.time >= ?"
        params.append(start_ts)
    if end_dt:
        end_ts = int(datetime.strptime(end_dt, '%Y-%m-%d').timestamp())
        query += " AND sr.time <= ?"
        params.append(end_ts)
    if student_id:
        query += " AND sr.student_ID = ?"
        params.append(student_id)
    if class_id:
        class_ids = [f"Class{cid.strip()}" for cid in class_id.replace("，",",").split(',')]
        placeholders = ','.join(['?' for _ in class_ids])
        query += f" AND sr.class IN ({placeholders})"
        params.extend(class_ids)
    
    try:
        # 执行查询
        df = pd.read_sql_query(query, conn, params=params)
        conn.close()
        
        if len(df) == 0:
            return "未找到符合条件的数据"
        
        # 数据清洗和验证
        df['achieved_score'] = pd.to_numeric(df['achieved_score'], errors='coerce')
        df['max_score'] = pd.to_numeric(df['max_score'], errors='coerce')
        
        # 移除无效数据
        df = df.dropna(subset=['achieved_score', 'max_score'])
        df = df[df['max_score'] > 0]  # 避免除以零
        
        # 1. 知识掌握广度分析
        knowledge_coverage = df.groupby('student_ID')['knowledge'].nunique()
        
        # if len(knowledge_coverage) > 0:  # 确保有数据可绘制
        #     plt.figure(figsize=(10, 6))
        #     sns.histplot(data=knowledge_coverage, bins=min(20, len(knowledge_coverage.unique())))
        #     plt.title('知识点覆盖分布')
        #     plt.xlabel('覆盖知识点数')
        #     plt.ylabel('学生人数')
            
        ut = int(time.time())
        #     coverage_file = f'tmp/knowledge_coverage.png'
        #     plt.savefig(coverage_file, dpi=300)
        #     plt.close()
        # else:
        #     coverage_file = None
        
        # 2. 知识掌握深度分析
        # 根据分数划分难度：1-2分为简单，3分为中等，4分为困难
        df['difficulty'] = pd.cut(df['max_score'], 
                                bins=[0, 2, 3, float('inf')],
                                labels=['简单', '中等', '困难'])
        
        df['score_rate'] = df['achieved_score'] / df['max_score']
        df['score_rate'] = df['score_rate'].clip(0, 1)  # 限制得分率在0-1之间
        
        # 按难度和知识点分析
        difficulty_stats = df.groupby(['difficulty', 'knowledge']).agg({
            'score_rate': ['count', 'mean']
        }).round(3)
        
        if len(difficulty_stats) > 0:  # 确保有数据可绘制
            plt.figure(figsize=(15, 8))
            
            # 创建分组柱状图
            difficulty_means = df.groupby(['difficulty', 'knowledge'])['score_rate'].mean().unstack()
            difficulty_means.plot(kind='bar', width=0.8)
            
            plt.title('不同难度和知识点的得分率分布')
            plt.xlabel('难度')
            plt.ylabel('得分率')
            plt.legend(title='知识点', bbox_to_anchor=(1.05, 1), loc='upper left')
            
            # 在柱状图上添加数值标签
            for container in plt.gca().containers:
                plt.bar_label(container, fmt='%.1f%%', padding=3)
            
            plt.tight_layout()
            
            depth_file = f'tmp/difficulty_accuracy.png'
            plt.savefig(depth_file, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            depth_file = None
        
        
        
        # 构建结果文本
        result = "## 能力分布分析\n\n"
        
        result += "### 知识掌握广度\n"
        if len(knowledge_coverage) > 0:
            result += f"- 平均覆盖知识点数：{knowledge_coverage.mean():.2f}\n"
            result += f"- 中位数覆盖知识点数：{knowledge_coverage.median():.2f}\n"
            result += f"- 最大覆盖知识点数：{knowledge_coverage.max()}\n"
            result += f"- 最小覆盖知识点数：{knowledge_coverage.min()}\n"
            # if coverage_file:
            #     result += f"- 查看分布图：http://localhost:3001/{coverage_file}\n"
        else:
            result += "- 暂无有效的知识点覆盖数据\n"
        result += "\n"
        
        result += "### 知识掌握深度\n"
        if len(difficulty_stats) > 0:
            for difficulty in difficulty_stats.index:
                count = difficulty_stats.loc[difficulty, ('score_rate', 'count')]
                score_rate = difficulty_stats.loc[difficulty, ('score_rate', 'mean')] * 100
                result += f"- {difficulty}题目: {score_rate:.1f}% 平均得分率 (样本数: {count})\n"
            if depth_file:
                result += f"\n查看难度得分率对比图：http://localhost:3001/{depth_file}\n"
        else:
            result += "- 暂无有效的难度分析数据\n"
        result += "\n"

        return result
        
    except Exception as e:
        print(f"分析能力分布时出错: {str(e)}")
        return f"错误：{str(e)}"








if __name__ == "__main__":
    
    arguments = json.loads('{"knowledge":""}')
    print(get_hard_title(**arguments))
    print(arguments)
    exit()
    
    print(get_knowledge_accuracy_compare(start_dt='2023-08-31', end_dt='2023-12-31', class_id='1,2'))

    #print(get_knowledge_preference(start_dt='2023-08-31', end_dt='2024-01-25', student_id='882ccee198e25b49b30d'))
    #print(get_ability_distribution(start_dt='2023-08-31', end_dt='2024-01-25'))
    # print(get_system_data_info())
    #download_report()
