from openai import OpenAI
import pickle
import os
import json
import api as API
import asyncio
import websockets
from lm_backend import *

import tornado.ioloop
import tornado.web
import tornado.websocket
import time
messages = [{"role":"system","content":SYSTEM_PROMPT}] 

class ImageHandler(tornado.web.StaticFileHandler):
    def set_extra_headers(self, path):
        # 允许跨域访问
        self.set_header("Access-Control-Allow-Origin", "*")

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
            print(json.dumps(messages,indent=4))
            assert len(messages) % 2 == 0
            #print("messages:",messages)

            # 获取流式响应并发送
            for chunk in get_model_response(messages, tools):
                if chunk is not None:
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
    (r'/chat', WebSocketHandler),  # WebSocket路由
    (r'/tmp/(.*)', ImageHandler, {'path': 'tmp'}),  # 静态文件路由,用于访问tmp目录下的图片
])

if __name__ == '__main__':
    # 确保tmp目录存在
    if not os.path.exists('tmp'):
        os.makedirs('tmp')
    print("WebSocket服务器启动在端口3001...")
    application.listen(3001)
    tornado.ioloop.IOLoop.instance().start()
