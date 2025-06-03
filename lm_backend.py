from openai import OpenAI
import pickle
import os
import json
import api as API
import asyncio
import websockets

client = OpenAI(
    api_key="sk-8e81464b09884584b7aba4204fd10565",
    base_url="https://api.deepseek.com",
)

def send_messages(messages,tools = None):
    kwargs = {
        "model" : "deepseek-chat",
        "messages" : messages,
    }
    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    return response.choices[0]

def messages_stream(messages,tools):
    kwargs = {
        "model" : "deepseek-chat",
        "messages" : messages,
        "stream" : True
    }
    if tools:
        kwargs["tools"] = tools

    response = client.chat.completions.create(**kwargs)
    one_tool_finished = False
    agg_tools = {}
    for chunk in response:
        delta = chunk.choices[0].delta
        if chunk.choices[0].finish_reason:
            if len(agg_tools) > 0:
                yield '}'+"\n[end tool call]\n"
                one_tool_finished = True
            yield agg_tools
        elif delta.tool_calls:
            for idx, tool_call in enumerate(delta.tool_calls):
                if tool_call.id : 
                    if not one_tool_finished :
                        yield "[start tool call]\n"
                        one_tool_finished = True
                    else:
                        agg_tools[tool_call_id]["arguments"] = json.loads(agg_tools[tool_call_id]["arguments"])
                        yield '}\n'
                    tool_call_id = tool_call.id
                    yield "{'id':" + "'" + tool_call_id + "'" + "," + "'name':" + "'" + tool_call.function.name + "'" + "," + "'arguments':"
    
                    if tool_call_id not in agg_tools:
                        agg_tools[tool_call_id] = {"name":tool_call.function.name,"arguments": ""}
                else:
                    agg_tools[tool_call_id]["arguments"] += tool_call.function.arguments
                    yield  tool_call.function.arguments
                    
        else:
            yield delta.content
        
def get_model_response(messages,tools,debug = False):

    stream = messages_stream(messages,tools)
    for chunk in stream:
        if isinstance(chunk,dict):
            tool_calls = chunk
        else:
            #content data 
            if debug:
                print(chunk,flush=True,end="")
            yield chunk 
    if len(tool_calls) == 0:
        return 
    if debug:
        print(json.dumps(tool_calls,indent=4))
    #如果存在tool_calls，则需要调用工具
    assistant_message = {
        "role": "assistant",
        "content" : None,
        "tool_calls" : []
    }
    messages_copy = messages.copy()
    messages_copy.append(assistant_message)
    for _id,tool_call in tool_calls.items():
        _name = tool_call["name"]
        _arguments = tool_call["arguments"]
        assistant_message["tool_calls"].append({
            "id": _id,
            "type": "function",
            "function": {
                "name": _name,
                "arguments": json.dumps(_arguments)
            }
        })
        #get response from tool    
        print("function call : ",_name,"\narguments : ",_arguments) 
        if isinstance(_arguments,str):
            _arguments = json.loads(_arguments)
        try:
            func_callback = getattr(API, _name)
            response = func_callback(**_arguments)
        except Exception as e:
            print("Error: Tool call failed",e)
            response = "Error: Tool call failed"

        print("response : ",json.dumps(response))
        messages_copy.append({
            "tool_call_id": _id,
            "role": "tool",
            "content": response,
            "name" : _name
        })
    print("function call finished")
    stream = messages_stream(messages_copy,tools)
    for chunk in stream:
        if isinstance(chunk,str):
            if debug:
                print(chunk,flush=True,end="")
            yield chunk

SYSTEM_PROMPT = "你是Novaviz的智能助手，掌管了15个班级从2023年8月31日到2024年1月25日共148天的学习行为模拟数据。"\
                "包括学习者基本信息（共1364名）、题目基本信息（共44条）和学习者答题行为日志记录（共232818条）。"\
                "你可以用提供的工具获取来帮助你回答用户的问题。(请注意，如果工具返回了图片链接，你也需要以markdown格式将图片贴在回复的合适地方)"


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
    {
        "type": "function",
        "function": {
            "name": "get_hard_title",
            "description": "获取学习行为数据中[知识点]各题目的难度分析，返回[知识点]掌握度散点图，各题目正确率柱状图，高分学生（知识掌握度大于0.7）的平均正确率柱状图以及答题正确率箱线图链接以及难度分析结论（是否有哪道题难度过高）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge": {"type": "string", "description": "需要分析的知识点,共8个，分别是r8S3g,t5V9e,m3D1v,y9W5d,k4W1c,s8Y2f,g7R2j,b3C9s,多个知识点用英文的逗号,分开.如果为空，则默认使用所有知识点"}
                }
            }
        }
    },
]
if __name__ == "__main__":
    messages = [
        {"role": "user", "content": "你好，我想知道2023年8月31日到2024年1月25日共148天的学习行为数据。"}
    ]
    get_model_response(messages,tools,debug=True)

