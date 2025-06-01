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
        




def get_model_response(messages,tools):

    stream = messages_stream(messages,tools)
    for chunk in stream:
        if isinstance(chunk,dict):
            tool_calls = chunk
        else:
            #content data 
            yield chunk 
    if len(tool_calls) == 0:
        return 
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
        try:
            func_callback = getattr(API, _name)
            response = func_callback(**json.loads(_arguments))
        except:
            response = "Error: Tool call failed"
        messages_copy.append({
            "tool_call_id": _id,
            "role": "tool",
            "content": response,
            "name" : _name
        })
    stream = messages_stream(messages_copy,tools)
    for chunk in stream:
        if isinstance(chunk,str):
            yield chunk



SYSTEM_PROMPT = "你是Novaviz的智能助手，掌管着15个班级学生的学习数据以及对应的学生和题目信息，请根据用户的问题和提供工具的给出回答。"
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
            "name": "get_class_data_info",
            "description": "获取Novaviz系统的班级数据信息,需要传入班级序号，返回一个markdown格式的表格",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "班级序号,从1开始,最大5",
                    }
                },
                "required": ["id"]
            },
        }
    },
]

import tornado.ioloop
import tornado.web
import tornado.websocket
import time
messages = [{"role":"system","content":SYSTEM_PROMPT}] 

class WebSocketHandler(tornado.websocket.WebSocketHandler):
    def check_origin(self, origin):
        return True  # 允许跨域访问，生产环境中应该更严格

    def open(self):
        print("WebSocket连接已建立")
        self.messages = messages.copy()  # 为每个连接创建独立的消息历史

    def on_message(self, message):

        try:
            # 解析接收到的消息
            data = json.loads(message)
            messages = [{"role":"system","content":SYSTEM_PROMPT}] + data["history"] + [{"role":"user","content":data["message"]}]
            assert len(messages) % 2 == 0
            #print("messages:",messages)

            # 获取流式响应并发送
            for chunk in get_model_response(messages, tools):
                if chunk is not None:
                    print("chunk:",json.dumps(chunk))
                    self.write_message({"type":"chunk","content":chunk})
            self.write_message({"type":"done"})
            #for chunk in get_model_response(self.messages, tools):
            #    if chunk is not None:
            #        self.write_message(chunk)
            
            
        except Exception as e:
            print(f"错误: {str(e)}")
            self.write_message({"type":"error","content":str(e)})

    def on_close(self):
        print("WebSocket连接已关闭")

application = tornado.web.Application([
    (r'/chat', WebSocketHandler),  # 修改路由为更具体的路径
])

if __name__ == '__main__':
    print("WebSocket服务器启动在端口3001...")
    application.listen(3001)
    tornado.ioloop.IOLoop.instance().start()

