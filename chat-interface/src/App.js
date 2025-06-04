import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './App.css';
import userAvatar from './assets/user-avatar.png';  // 请确保有这个图片文件
// 导入不同角色的头像
import assistantAvatar0 from './assets/assistant-avatar-0.png';

// 蜘蛛网背景组件
const SpiderWebBackground = () => {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);
  const mouseRef = useRef({ x: 0, y: 0 });
  const particlesRef = useRef([]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    let particles = [];

    // 调整canvas大小
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };

    // 粒子类
    class Particle {
      constructor() {
        this.x = Math.random() * canvas.width;
        this.y = Math.random() * canvas.height;
        this.vx = (Math.random() - 0.5) * 0.5;
        this.vy = (Math.random() - 0.5) * 0.5;
        this.radius = Math.random() * 2 + 1;
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;

        // 边界检测
        if (this.x < 0 || this.x > canvas.width) this.vx = -this.vx;
        if (this.y < 0 || this.y > canvas.height) this.vy = -this.vy;

        // 鼠标吸引效果
        const dx = mouseRef.current.x - this.x;
        const dy = mouseRef.current.y - this.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < 150) {
          const force = (150 - distance) / 150;
          this.vx += dx * force * 0.0003;
          this.vy += dy * force * 0.0003;
        }

        // 限制速度
        this.vx *= 0.99;
        this.vy *= 0.99;
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(102, 126, 234, 0.6)';
        ctx.fill();
      }
    }

    // 初始化粒子
    const initParticles = () => {
      particles = [];
      const particleCount = Math.min(Math.floor((canvas.width * canvas.height) / 15000), 100);
      for (let i = 0; i < particleCount; i++) {
        particles.push(new Particle());
      }
      particlesRef.current = particles;
    };

    // 绘制连接线
    const drawConnections = () => {
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < 120) {
            const opacity = 1 - distance / 120;
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            ctx.strokeStyle = `rgba(102, 126, 234, ${opacity * 0.3})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }

        // 鼠标连接线
        const dx = mouseRef.current.x - particles[i].x;
        const dy = mouseRef.current.y - particles[i].y;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < 150) {
          const opacity = 1 - distance / 150;
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(mouseRef.current.x, mouseRef.current.y);
          ctx.strokeStyle = `rgba(118, 75, 162, ${opacity * 0.4})`;
          ctx.lineWidth = 1;
          ctx.stroke();
        }
      }
    };

    // 动画循环
    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      particles.forEach(particle => {
        particle.update();
        particle.draw();
      });
      
      drawConnections();
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    // 鼠标移动事件
    const handleMouseMove = (e) => {
      mouseRef.current.x = e.clientX;
      mouseRef.current.y = e.clientY;
    };

    // 初始化
    resizeCanvas();
    initParticles();
    animate();

    // 事件监听
    window.addEventListener('resize', () => {
      resizeCanvas();
      initParticles();
    });
    window.addEventListener('mousemove', handleMouseMove);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      window.removeEventListener('resize', resizeCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="spider-web-canvas"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: -1,
        background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
        pointerEvents: 'none'
      }}
    />
  );
};

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isReportGenerating, setIsReportGenerating] = useState(false);
  const [downloadStatus, setDownloadStatus] = useState(null);
  const ws = useRef(null);

  // 角色配置
  const roleConfig = {
    0: {
      name: 'NovaViz',
      avatar: assistantAvatar0,
      className: 'role-default'
    }
  };

  useEffect(() => {
    // 建立WebSocket连接
    ws.current = new WebSocket('ws://localhost:3001/chat');

    ws.current.onopen = () => {
      console.log('WebSocket连接已建立');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log(data);
      
      if (data.type === 'report_start') {
        setIsReportGenerating(true);
        return;
      } else if (data.type === 'report_end') {
        setIsReportGenerating(false);
        return;
      } else if (data.type === 'file_download') {
        // 处理文件下载
        try {
          const blob = new Blob([data.content], { 
            type: data.file_type === 'html' ? 'text/html' : 'text/markdown' 
          });
          const url = window.URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.style.display = 'none';
          a.href = url;
          a.download = data.filename;
          document.body.appendChild(a);
          a.click();
          window.URL.revokeObjectURL(url);
          document.body.removeChild(a);
          
          // 设置下载成功状态
          setDownloadStatus(`文件 ${data.filename} 下载成功！`);
          // 3秒后清除提示
          setTimeout(() => {
            setDownloadStatus(null);
          }, 3000);
          
          console.log(`文件 ${data.filename} 下载成功`);
        } catch (error) {
          console.error('文件下载失败:', error);
          setDownloadStatus(`文件下载失败: ${error.message}`);
          // 3秒后清除提示
          setTimeout(() => {
            setDownloadStatus(null);
          }, 3000);
        }
        return;
      } else if (data.type === 'chunk') {
        setIsLoading(true);  // 接收到chunk数据时设置为loading状态
        setMessages(prevMessages => {
          const lastMessage = prevMessages[prevMessages.length - 1];
          
          // 清理工具调用的函数 - 修改为不使用trim()以保持markdown格式
          const cleanToolCalls = (content) => {
            // 移除工具调用内容，但保持其他格式完整
            return content.replace(/\[start tool call\].*?\[end tool call\]/gs, '');
          };
          
          // 检查最后一条消息是否为assistant且未完成
          if (lastMessage && lastMessage.role === 'assistant' && !lastMessage.isCompleted) {
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
          
          // 创建新的assistant消息
          // 清理工具调用，保持markdown格式的换行符和空格
          const cleanedContent = cleanToolCalls(data.content);
          return [...prevMessages, { 
            role: 'assistant', 
            content: cleanedContent,
            assistantRole: data.role || 0,  // 保存assistant的具体角色
            isCompleted: false  // 标记消息未完成
          }];
        });
      } else if (data.type === 'done') {
        setIsLoading(false);
        // 标记最后一条assistant消息为已完成
        setMessages(prevMessages => {
          return prevMessages.map((msg, index) => {
            if (index === prevMessages.length - 1 && msg.role === 'assistant') {
              return { ...msg, isCompleted: true };
            }
            return msg;
          });
        });
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
    if (!input.trim() || isLoading || isReportGenerating) return;

    // 移除对用户输入换行符的HTML处理，让markdown自然处理
    setMessages(prev => [...prev, { 
      role: 'user', 
      content: input  // 直接使用原始输入，不做HTML转换
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
    ),
    // 添加表格相关的自定义组件
    table: ({ node, ...props }) => (
      <div className="table-container">
        <table {...props} />
      </div>
    ),
    th: ({ node, ...props }) => (
      <th {...props} />
    ),
    td: ({ node, ...props }) => (
      <td {...props} />
    )
  };

  return (
    <div className="app-wrapper">
      <SpiderWebBackground />
      <div className="chat-container">
        {/* 添加标题区域 */}
        <div className="header-section">
          <h1 className="main-title">NovaViz -- NorthClass智能可视交互平台</h1>
          <h2 className="sub-title">基于deepseek的实时对话体验</h2>
        </div>
        
        <div className="messages">
          {messages.map((msg, index) => {
            // 获取当前消息的角色配置
            const currentRoleConfig = msg.role === 'assistant' && msg.assistantRole !== undefined 
              ? roleConfig[msg.assistantRole] 
              : null;
            
            return (
              <div key={index} className={`message ${msg.role} ${msg.role === 'user' ? 'role-user' : ''} ${currentRoleConfig ? currentRoleConfig.className : ''}`}>
                <div className="message-header">
                  <img 
                    src={msg.role === 'user' 
                      ? userAvatar 
                      : (currentRoleConfig ? currentRoleConfig.avatar : assistantAvatar0)
                    } 
                    alt={msg.role === 'user' 
                      ? 'User Avatar' 
                      : `${currentRoleConfig ? currentRoleConfig.name : 'NovaViz'} Avatar`
                    } 
                    className="avatar"
                  />
                  <span className="role-indicator">
                    {msg.role === 'user' 
                      ? 'User' 
                      : (currentRoleConfig ? currentRoleConfig.name : 'NovaViz')
                    }
                  </span>
                </div>
                <div className="content">
                  <ReactMarkdown 
                    components={customComponents}
                    remarkPlugins={[remarkGfm]}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            );
          })}
          {isLoading && <div className="loading">正在输入中...</div>}
          {isReportGenerating && (
            <div className="report-generating">
              <div className="report-loading-animation">
                <div className="spinner"></div>
                <span>报告生成中...</span>
              </div>
            </div>
          )}
        </div>
        
        {/* 下载状态提示 */}
        {downloadStatus && (
          <div className="download-status">
            {downloadStatus}
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入消息..."
            disabled={isLoading || isReportGenerating}
          />
          <button type="submit" disabled={isLoading || isReportGenerating}>
            发送
          </button>
          <button type="button" onClick={handleClear}>
            清除历史
          </button>
        </form>
      </div>
    </div>
  );
}

export default App; 