from openai import OpenAI
import json
import api as Funcs
from abc import ABC, abstractmethod


client = OpenAI(
    api_key="sk-8e81464b09884584b7aba4204fd10565",
    base_url="https://api.deepseek.com",
)

class Agent(object):
    def __init__(self, name, system_prompt, tools = None):
        self.name = name
        self.system_prompt = system_prompt
        if isinstance(tools,list) and len(tools) >= 1:
            self.tools = tools
        else:
            self.tools = None
        self._debug = False
        self.history = []

    def get_message_stream(self, messages):
        kwargs = {
            "model" : "deepseek-chat",
            "messages" : messages,
            "stream" : True,
            "temperature" : 0
        }
        if self.tools:
            kwargs["tools"] = self.tools

        response = client.chat.completions.create(**kwargs)
        one_tool_finished = False
        agg_tools = {}
        for chunk in response:
            delta = chunk.choices[0].delta
            if chunk.choices[0].finish_reason:
                self.print("agg_tools:",agg_tools)
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

    def debug(self):
        self._debug = True

    def clear(self):
        self.history = []

    def print(self,*args,**kwargs):
        if self._debug:
            print(*args,**kwargs)

    def get_model_response(self,query,use_history=True):

        messages = [{"role":"system","content":self.system_prompt}]
        self.history.append(query)
        for idx,msg in enumerate(self.history):
            role = "user" if idx % 2 == 0 else "assistant"
            messages.append({"role":role,"content":msg})

        self.print("Agent Input Messages: \n",query)

        if not use_history:
            messages_input =  [{"role":"system","content":self.system_prompt},{"role":"user","content":query}]
        else:
            messages_input = messages
        print("messages_input: ",messages_input)
        stream = self.get_message_stream(messages_input)
        output = ""

        for chunk in stream:
            if isinstance(chunk,dict):
                tool_calls = chunk  #模型要求的tool_calls
            else:
                output += chunk
                self.print(chunk,flush=True,end="")
                yield chunk 
        #print("User:\n",query)
        #print("Tool Calls:\n",tool_calls)
        #print()
        if len(tool_calls) == 0 and "[start tool call]" in output and "[end tool call]" in output:
            possible_tool_call = output.split("[start tool call]")[-1].split("[end tool call]")[0].strip()
            try:
                possible_tool_call = json.loads(possible_tool_call)
                tool_calls.append(possible_tool_call)
            except:
                possible_tool_call = {}

        if len(tool_calls) == 0:
            self.history.append(output)
            return 
        
        self.print("Agent Invoked Tools: \n",json.dumps(tool_calls,indent=4))
        self.print(json.dumps(tool_calls,indent=4))

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
            self.print("function call : ",_name,"\narguments : ",_arguments) 
            if isinstance(_arguments,str):
                _arguments = json.loads(_arguments)
            try:
                func_callback = getattr(Funcs, _name)
                response = func_callback(**_arguments)
            except Exception as e:
                self.print("Error: Tool call failed",e)
                response = "Error: Tool call failed"

            self.print("function response : ",json.dumps(response))
            messages_copy.append({
                "tool_call_id": _id,
                "role": "tool",
                "content": response,
                "name" : _name
            })
        self.print("function call finished")
        stream = self.get_message_stream(messages_copy)
        for chunk in stream:
            if isinstance(chunk,str):
                self.print(chunk,flush=True,end="")
                output += chunk
                yield chunk
        self.history.append(output)
    
    @abstractmethod
    def finish(self):
        pass
    
SYSTEM_PROMPT = "你是Novaviz的智能助手，掌管了15个班级从2023年8月31日到2024年1月25日共148天的学习行为模拟数据。"\
                "包括学习者基本信息（共1364名）、题目基本信息（共44条）和学习者答题行为日志记录（共232818条）。"\
                "你可以用提供的工具获取来帮助你回答用户的问题。"\
                "你的输出需要保持markdown格式，因为你的输出需要插入到markdown中，因此请使用markdown语法。同时为了内容尽可能的生动，你可以使用emoji来丰富你的内容。"\
                "(请注意，如果工具返回了图片链接，你也需要以markdown格式将图片贴在回复的合适地方)"\
                "为了方便你更好的回答用户问题,下面是你的工具使用提示:\n"\
                "1. 当你需要获取系统的数据库信息时，请使用 get_system_data_info工具。\n"\
                "2. 当你需要获得有关知识点掌握度评估的信息时, 请调用:"\
                "get_knowledge_accuracy,get_time_consumption_distribution 这两个工具\n"\
                "3. 当你需要获得不同班级的知识点掌握度信息时，请调用: "\
                "get_knowledge_accuracy_compare 这一个工具\n"\
                "4. 当你需要获得学习者画像相关的信息时,请同时调用:"\
                "get_time_pattern_analysis,get_knowledge_preference,get_knowledge_preference 这三个工具。\n"\
                "5. 当你需要对题目难度合理性进行分析的时候,请调用: get_hard_title 这一个工具。\n"\
                "如果当用户明确提出需要下载报告的时候(请不要你自己揣测，需要用户自己说出来)，请你输出 <download_report>*</download_report>"\
                "其中*是json格式字典,有3个键:"\
                "1.type, 值为html或者pdf(默认pdf),"\
                "2.title, 值为报告的标题，"\
                "3.requirement，值为用户需要下载的报告的具体内容要求。如果用户没有任何要求，请设置为None。"\

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
            "description": "获取学习者行为数据中不同[知识点]答题耗时分布数据(不做不同班级之间的比较)，返回一个字符串，字符串中包含不同[知识点]的答题耗时分布数据与可视化图链接。",
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
            "name": "get_time_pattern_analysis",
            "description": "获取学习者的时间模式分析，包括答题高峰时段（按小时统计）和学习频率（每日提交次数）的数据与可视化图表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_dt": {"type": "string", "description": "开始日期,格式为YYYY-MM-DD"},
                    "end_dt": {"type": "string", "description": "结束日期,格式为YYYY-MM-DD"},
                    "student_id": {"type": "string", "description": "学生ID，如果为空则分析所有学生"},
                    "class_id": {"type": "string", "description": "班级ID，如果为空则分析所有班级"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_knowledge_preference",
            "description": "获取学习者的题型偏好分析，包括各题型（选择题/编程题）的正确率对比数据与可视化图表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_dt": {"type": "string", "description": "开始日期,格式为YYYY-MM-DD"},
                    "end_dt": {"type": "string", "description": "结束日期,格式为YYYY-MM-DD"},
                    "student_id": {"type": "string", "description": "学生ID，如果为空则分析所有学生"},
                    "class_id": {"type": "string", "description": "班级ID，如果为空则分析所有班级"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_ability_distribution",
            "description": "获取学习者的能力分布分析，包括知识掌握广度（覆盖知识点数）和深度（高难度题目正确率）的数据与可视化图表。",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_dt": {"type": "string", "description": "开始日期,格式为YYYY-MM-DD"},
                    "end_dt": {"type": "string", "description": "结束日期,格式为YYYY-MM-DD"},
                    "student_id": {"type": "string", "description": "学生ID，如果为空则分析所有学生"},
                    "class_id": {"type": "string", "description": "班级ID，如果为空则分析所有班级"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_hard_title",
            "description": "获取学习者行为数据中[知识点]各题目的难度分析，返回[知识点]掌握度散点图，各题目正确率柱状图，高分学生（知识掌握度大于0.7）的平均正确率柱状图以及答题正确率箱线图链接以及难度分析结论（是否有哪道题难度过高）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "knowledge": {"type": "string", "description": "需要分析的知识点,共8个，分别是r8S3g,t5V9e,m3D1v,y9W5d,k4W1c,s8Y2f,g7R2j,b3C9s,多个知识点用英文的逗号,分开.如果为空，则默认使用所有知识点"}
                }
            }
        }
    },
]




def get_download_requirement(history):
    if "<download_report>" in history[-1] and "</download_report>" in history[-1]:
        requirement = history[-1].split("<download_report>")[1].split("</download_report>")[0]
    if "```json" in history[-1] and "```" in history[-1]:
        requirement = history[-1].split("```json")[1].split("```")[0]

    try:
        requirement = json.loads(requirement)
    except:
        requirement = {"type":"pdf","requirement":"整理输出所有分析"}
    return requirement

def download_report(history=None):
    with open("agent_response_history.json","r",encoding="utf-8") as f:
        history = json.loads(f.read())
    requirement = get_download_requirement(history)
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
        query += "现在用户需要将助手输出的分析整理成html格式的报告，报告的内容要求是:"+requirement["requirement"] + ". 现在请你输出html代码(请不要输出```html来标识html代码),"
        filename = "report.html"
    elif requirement["type"] == "pdf":
        query += "现在用户需要将助手输出的分析整理成markdown格式的报告，报告的内容要求是:"+requirement["requirement"] + ". 现在请你输出markdown代码,"
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






if __name__ == "__main__":
    #download_report()

    if  "[start tool call]" in output and "[end tool call]" in output:
        possible_tool_call = output.split("[start tool call]")[-1].split("[end tool call]")[0].strip()
        possible_tool_call = json.loads(possible_tool_call)

    print(possible_tool_call)
    #func_callback = getattr(Funcs, _name)
    #response = func_callback(**_arguments)