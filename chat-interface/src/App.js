import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';
import userAvatar from './assets/user-avatar.png'; // 请确保有这个图片文件
import assistantAvatar from './assets/assistant-avatar.png'; // 请确保有这个图片文件

function App() {
  const [messages, setMessages] = useState([
    { 
      role: 'assistant', 
      content: `你好！我是NovaViz助手，有什么我可以帮助你的吗？\n\n你可以尝试问我以下问题：\n- 如何创建一个React应用？\n- 解释一下JavaScript的闭包概念\n- 最近有什么科技新闻？` 
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const ws = useRef(null);
  const messagesEndRef = useRef(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // 建立WebSocket连接
    ws.current = new WebSocket('ws://localhost:3001/chat');

    ws.current.onopen = () => {
      console.log('WebSocket连接已建立');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data);
      if (data.type === 'chunk') {
        setMessages(prevMessages => {
          const lastMessage = prevMessages[prevMessages.length - 1];
          
          // 清理工具调用的函数 - 修改为不使用trim()以保持markdown格式
          const cleanToolCalls = (content) => {
            // 移除工具调用内容，但保持其他格式完整
            return content.replace(/$$start tool call$$.*?$$end tool call$$/gs, '');
          };
          
          if (lastMessage && lastMessage.role === 'assistant') {
            const newContent = lastMessage.content + data.content;
            // 清理工具调用，保持markdown格式的换行符和空格
            const cleanedContent = cleanToolCalls(newContent);
            
            return prevMessages.map((msg, index) => {
              if (index === prevMessages.length - 1) {
                return { ...msg, content: cleanedContent };
              }
              return msg;
            });
          }
          
          // 清理工具调用，保持markdown格式的换行符和空格
          const cleanedContent = cleanToolCalls(data.content);
          return [...prevMessages, { role: 'assistant', content: cleanedContent }];
        });
      } else if (data.type === 'done') {
        setIsLoading(false);
      } else if (data.type === 'error') {
        console.error('Error:', data.content);
        setIsLoading(false);
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket连接已关闭');
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    // 处理用户输入的换行符
    const processUserNewlines = (content) => {
      let processed = content.replace(/\\n/g, '<br />');
      processed = processed.replace(/\n/g, '<br />');
      return processed;
    };

    setMessages(prev => [...prev, { 
      role: 'user', 
      content: processUserNewlines(input)
    }]);
    setIsLoading(true);

    ws.current.send(JSON.stringify({
      message: input,
      history: messages
    }));

    setInput('');
  };

  // 添加清除历史记录的函数
  const handleClear = () => {
    if (window.confirm('确定要清除所有对话历史吗？')) {
      setMessages([{ 
        role: 'assistant', 
        content: `历史已清除。有什么新的问题需要帮助吗？` 
      }]);
    }
  };

  // 添加自定义图片组件
  const customComponents = {
    img: ({ node, ...props }) => (
      <img
        {...props}
        style={{
          maxWidth: '100%',
          maxHeight: '400px',
          height: 'auto',
          borderRadius: '8px',
          margin: '10px 0',
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
        }}
        alt={props.alt || '图片'}
      />
    ),
    a: ({node, ...props}) => (
      <a {...props} style={{color: '#4e6ef2'}} target="_blank" rel="noopener noreferrer" />
    ),
    blockquote: ({node, ...props}) => (
      <blockquote {...props} style={{
        borderLeft: '4px solid #4e6ef2',
        paddingLeft: '16px',
        margin: '16px 0',
        color: '#666'
      }} />
    ),
    pre: ({node, ...props}) => (
      <pre {...props} style={{
        backgroundColor: '#f8f9fa',
        padding: '16px',
        borderRadius: '8px',
        overflowX: 'auto',
        fontSize: '0.9em',
        lineHeight: '1.5',
        margin: '16px 0'
      }} />
    ),
    code: ({node, ...props}) => (
      <code {...props} style={{
        backgroundColor: '#f8f9fa',
        padding: '2px 4px',
        borderRadius: '4px',
        fontFamily: 'Consolas, Monaco, monospace'
      }} />
    ),
    table: ({node, ...props}) => (
      <table {...props} style={{
        width: '100%',
        borderCollapse: 'collapse',
        margin: '16px 0',
        boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        borderRadius: '8px',
        overflow: 'hidden'
      }} />
    ),
    th: ({node, ...props}) => (
      <th {...props} style={{
        backgroundColor: '#f1f3f5',
        textAlign: 'left',
        padding: '12px 16px',
        borderBottom: '1px solid #e0e0e0'
      }} />
    ),
    td: ({node, ...props}) => (
      <td {...props} style={{
        padding: '12px 16px',
        borderBottom: '1px solid #e0e0e0',
        backgroundColor: '#ffffff'
      }} />
    )
  };

  return (
    <div className="app-container">
      <div className="header">
        <div className="logo">NovaViz 💬</div>
        <h1>AI智能聊天助手</h1>
        <p>基于GPT技术的实时对话体验</p>
      </div>
      
      <div className="chat-app">
        <div className="messages-container">
          <div className="messages">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role}`}>
                <div className="message-header">
                  <img 
                    src={msg.role === 'user' ? userAvatar : assistantAvatar} 
                    alt={msg.role === 'user' ? '用户头像' : 'NovaViz头像'} 
                    className="avatar"
                  />
                  <div>
                    <span className="role-indicator">{msg.role === 'user' ? '你' : 'NovaViz助手'}</span>
                    <div className="message-time">{new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                  </div>
                </div>
                {msg.role === 'user' ? (
                  <div 
                    className="content"
                    dangerouslySetInnerHTML={{ __html: msg.content }}
                  />
                ) : (
                  <div className="content">
                    <ReactMarkdown components={customComponents}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>
            ))}
            
            {isLoading && (
              <div className="message assistant">
                <div className="message-header">
                  <img 
                    src={assistantAvatar} 
                    alt="NovaViz头像" 
                    className="avatar"
                  />
                  <div>
                    <span className="role-indicator">NovaViz助手</span>
                    <div className="message-time">{new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</div>
                  </div>
                </div>
                <div className="content">
                  <div className="loading">
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                    <div className="loading-dot"></div>
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        </div>
        
        <form onSubmit={handleSubmit} className="input-form">
          <div className="input-container">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="输入消息..."
              disabled={isLoading}
            />
            <div className="button-group">
              <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
                <span>发送</span>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M22 2L11 13" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M22 2L15 22L11 13L2 9L22 2Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
              <button type="button" className="clear-btn" onClick={handleClear}>
                <span>清除</span>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M18 6L6 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>
          </div>
          <div className="hint">NovaViz可能生成错误信息，请谨慎验证重要内容</div>
        </form>
      </div>
      <div className="footer">
        © {new Date().getFullYear()} NovaViz AI Assistant • 让沟通更智能
      </div>
    </div>
  );
}

export default App;
