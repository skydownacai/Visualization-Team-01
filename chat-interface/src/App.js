import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';
import userAvatar from './assets/user-avatar.png';  // 请确保有这个图片文件
import assistantAvatar from './assets/assistant-avatar.png';  // 请确保有这个图片文件

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const ws = useRef(null);

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
            return content.replace(/\[start tool call\].*?\[end tool call\]/gs, '');
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
    setMessages([]);
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
          margin: '10px 0'
        }}
        alt={props.alt || '图片'}
      />
    )
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.role}`}>
            <div className="message-header">
              <img 
                src={msg.role === 'user' ? userAvatar : assistantAvatar} 
                alt={msg.role === 'user' ? 'User Avatar' : 'NovaViz Avatar'} 
                className="avatar"
              />
              <span className="role-indicator">{msg.role === 'user' ? 'User' : 'NovaViz'}</span>
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
        {isLoading && <div className="loading">正在输入中...</div>}
      </div>
      
      <form onSubmit={handleSubmit} className="input-form">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          发送
        </button>
        <button type="button" onClick={handleClear}>
          清除历史
        </button>
      </form>
    </div>
  );
}

export default App; 