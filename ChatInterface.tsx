import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Moon, Sun, LogOut } from 'lucide-react';
import logo from "../images/zeitlogo.png"

interface Message {
  sender: 'bot' | 'user';
  text: string;
  timestamp: Date;
}

interface ChatInterfaceProps {
  onLogout: () => void;
  isDarkMode: boolean;
  setIsDarkMode: (darkMode: boolean) => void;
}

export default function ChatInterface({ onLogout, isDarkMode, setIsDarkMode }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([
    { 
      sender: "bot", 
      text: "Hello! 👋 I'm your AI assistant. I'm here to help you with any questions or tasks you have. What would you like to know today?",
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      sender: "user",
      text: input.trim(),
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: input.trim(),
          top_k: 3
        }),
      });

      if (!response.ok) {
        throw new Error("API request failed");
      }

      const data = await response.json();
      
      const botMessage: Message = {
        sender: "bot",
        text: data.answer || "I apologize, but I couldn't process your request. Please try again.",
        timestamp: new Date()
      };

      setMessages(prev => [...prev, botMessage]);
    } catch (error: any) {
      console.error("Error:", error);
      
      let errorText = "I'm sorry, I'm having trouble connecting to the server right now.";
      
      if (error.name === 'TypeError' && error.message === 'Failed to fetch') {
        errorText = "🔌 Backend server is not running. Please start your backend server at http://127.0.0.1:8000 to enable AI responses.";
      } else if (error.message === 'API request failed') {
        errorText = "The server responded with an error. Please try again in a moment.";
      }
      
      const errorMessage: Message = {
        sender: "bot",
        text: errorText,
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  };

  const themeClasses = {
    background: isDarkMode ? 'bg-green-700' : 'bg-green-50',
    headerBg: isDarkMode ? 'bg-green-700 border-green-700' : 'bg-white border-green-700',
    headerText: isDarkMode ? 'text-green' : 'text-green-800',
    chatBg: isDarkMode ? 'bg-gray-900' : 'bg-gray-50',
    inputBg: isDarkMode ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200',
    inputText: isDarkMode ? 'text-white placeholder-gray-400' : 'text-gray-800 placeholder-gray-500',
    userBubble: 'bg-gradient-to-r from-green-700 to-green-700 text-white',
    botBubble: isDarkMode ? 'bg-green-800 text-white border border-green-500' : 'bg-grren text-green-800 border border-green-200',
    timestamp: isDarkMode ? 'text-gray-500' : 'text-gray-400'
  };

  return (
    <div className={`flex flex-col h-screen ${themeClasses.background} transition-colors duration-300`}>
      {/* Header */}
      <div className={`${themeClasses.headerBg} ${themeClasses.headerText} px-6 py-2 border-b shadow-sm`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo (adjusted) */}
            <div className="h-12 w-12 flex items-center justify-center">
              <img 
                src={logo} 
                alt="logo.png" 
                className="h-12 w-auto object-contain scale-[3.5]"
              />
            </div>
            
          </div>

          {/* Theme + Logout buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsDarkMode(!isDarkMode)}
              className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-green-700' : 'hover:bg-green-100'}`}
            >
              {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button
              onClick={onLogout}
              className={`p-2 rounded-lg transition-colors ${isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100'}`}
              title="Logout"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className={`flex-1 overflow-y-auto ${themeClasses.chatBg} px-4 py-6`}>
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex gap-3 ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} animate-fadeIn`}
            >
              {msg.sender === 'bot' && (
                <div className="w-8 h-8 bg-gradient-to-r from-green-700 to-green-700 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-green" />
                </div>
              )}
              
              <div className={`max-w-2xl ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}>
                <div
                  className={`inline-block px-4 py-3 rounded-2xl shadow-sm ${
                    msg.sender === 'user' 
                      ? themeClasses.userBubble 
                      : themeClasses.botBubble
                  } ${msg.sender === 'user' ? 'rounded-br-md' : 'rounded-bl-md'}`}
                >
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                </div>
                <p className={`text-xs mt-1 ${themeClasses.timestamp}`}>
                  {formatTime(msg.timestamp)}
                </p>
              </div>

              {msg.sender === 'user' && (
                <div className="w-8 h-8 bg-green-700 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                  <User className="w-4 h-4 text-white" />
                </div>
              )}
            </div>
          ))}
          
          {/* Loading indicator */}
          {isLoading && (
            <div className="flex gap-3 justify-start animate-fadeIn">
              <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-green-600 rounded-full flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-white" />
              </div>
              <div className={`px-4 py-3 rounded-2xl rounded-bl-md ${themeClasses.botBubble}`}>
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className={`${themeClasses.inputBg} border-t px-4 py-4`}>
        <div className="max-w-4xl mx-auto">
          <div className="relative flex items-end gap-3">
            <div className="flex-1">
              <div className="relative">
                <input
                  ref={inputRef}
                  type="text"
                  className={`w-full px-4 py-3 pr-12 rounded-2xl border focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-none transition-all ${themeClasses.inputBg} ${themeClasses.inputText} border-green-300`}
                  placeholder="Type your message..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  disabled={isLoading}
                />
              </div>
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="bg-gradient-to-r from-gray-900 to-green-600 hover:from-green-900 hover:to-green-700 disabled:from-gray-700 disabled:to-gray-400 text-white p-3 rounded-2xl transition-all duration-200 flex items-center justify-center disabled:cursor-not-allowed transform hover:scale-105 active:scale-95"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
          <p className={`text-xs mt-2 text-center ${themeClasses.timestamp}`}>
            OUR TIME YOUR SERVICE
          </p>
        </div>
      </div>
    </div>
  );
}
