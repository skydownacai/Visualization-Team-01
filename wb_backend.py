from openai import OpenAI
import pickle
import os
import json
import api as API
import asyncio
import websockets

import tornado.ioloop
import tornado.web
import tornado.websocket
import time
from agent import *
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
        self.agent = Agent("Novaviz",SYSTEM_PROMPT,tools)
        self.agent.debug()
        self.write_message({"type":"chunk","content":""})
        for chunk in self.agent.get_model_response("请介绍下你自己（不需要告诉用户你有具体哪些工具)"):
            self.write_message({"type":"chunk","content":chunk})
        self.write_message({"type":"done"})
        self.agent.clear()
        

    def on_message(self, message):
        try:
            data = json.loads(message)
            if len(data["history"]) == 0:
                self.agent.clear()
            query = data["message"]
            use_history = "报告" in query
            print("use history: ",use_history)
            for chunk in self.agent.get_model_response(query,use_history=use_history):
                self.write_message({"type":"chunk","content":chunk})

            with open("history.json","w",encoding="utf-8") as f:
                f.write(json.dumps(self.agent.history,ensure_ascii=False))

            self.write_message({"type":"done"})
            if "download_report" in self.agent.history[-1]:
                self.download_report(self.agent.history)

                
        except Exception as e:
            print(f"错误: {str(e)}")
            self.write_message({"type":"error","content":str(e)})

    def on_close(self):
        print("WebSocket连接已关闭")

    def get_download_requirement(self,history):
        if "<download_report>" in history[-1] and "</download_report>" in history[-1]:
            requirement = history[-1].split("<download_report>")[1].split("</download_report>")[0]
        if "```json" in history[-1] and "```" in history[-1]:
            requirement = history[-1].split("```json")[1].split("```")[0]
        try:
            requirement = json.loads(requirement)
        except:
            requirement = {"type":"pdf","requirement":"整理输出所有分析"}
        return requirement

    def download_report(self,history=None):
        requirement = self.get_download_requirement(history)
        print("download report")
        self.write_message({"type":"report_start","content":""})
        system_prompt = "你是一个非常得力的助手，能帮组用户整理提交的文本内容并输出成他想要的格式"
        agent = Agent("report_downloader",system_prompt=system_prompt)
        query = "下面是用户和一个名为是Novaviz的智能助手对话历史，每一轮对话中，用户会提出一个需求，Novaviz会根据用户的需求输出用户想要的分析。"\
                "下面以<user_query>开头，以</user_query>结尾的文本是用户的需求，以<assistant_response>开头，以</assistant_response>结尾的文本是Novaviz的回答。\n"
        
        for role,msg in enumerate(history[:-2]):
            msg = msg.replace("[end tool calls]","[end tool call]")
            if "[start tool call]" in msg:
                msg = msg.split("[end tool call]")[-1]

            if role % 2 == 0:
                query += "<user_query>\n"+msg.strip()+"\n</user_query>\n\n"
            else:
                query += "<assistant_response>\n"+msg.strip()+"\n</assistant_response>\n\n"   

        if requirement["type"] == "html":
            query += "现在用户需要将助手输出的分析整理成html格式的报告,报告的标题是:"+requirement["title"] + ". 报告的内容要求是:"+requirement["requirement"] + ". 现在请你输出html代码(请不要输出```html来标识html代码),"
            filename = "report.html"
        elif requirement["type"] == "pdf":
            query += "现在用户需要将助手输出的分析整理成markdown格式的报告，报告的标题是:"+requirement["title"] + ". 报告的内容要求是:"+requirement["requirement"] + ". 现在请你输出markdown代码,"
            filename = "report.md"

        query += "将助手输出的分析整理成用户想要的报告。\n请注意，你需要完全遵循用户的要求。如果用户没有对内容进行要求，你需要整理输出该助手输出的所有分析。你需要尽可能保证内容的完整，不能遗漏。你可以根据助手的分析，进一步完善用户想要的内容。"
        query += "\n 下面请你直接开始输出代码,不要添加任何的解释说明。"
        f = open(filename,"w",encoding="utf-8")
        f.close()
        f = open(filename,"a",encoding="utf-8")
        for chunk in agent.get_model_response(query):
            print(chunk,flush=True,end="")
            f.write(chunk)
            f.flush()
        f.close()
        
        # 读取生成的文件内容并通过websocket发送给前端
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # 发送文件内容
            self.write_message({
                "type": "file_download",
                "filename": filename,
                "content": file_content,
                "file_type": requirement["type"]
            })
            print(f"文件 {filename} 已通过WebSocket发送")
        except Exception as e:
            print(f"发送文件时出错: {str(e)}")
            self.write_message({
                "type": "error",
                "content": f"发送文件时出错: {str(e)}"
            })
        
        self.write_message({"type":"report_end","content":""})
        

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
