import React, { useState, useEffect, useRef } from 'react';
import { v4 as uuidv4 } from 'uuid';
import toast from 'react-hot-toast';

import MessageBubble from './MessageBubble';
import FileUpload from './FileUpload';
import ModelSelector from './ModelSelector';
import ProcessIndicator from './ProcessIndicator';
import { useWebSocket } from '../hooks/useWebSocket';
import { sessionAPI, messageAPI, handleAPIError } from '../services/api';
import { Send, Loader2, AlertCircle, RefreshCw } from 'lucide-react';

const ChatInterface = () => {
  // State management
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState(null);
  
  // Process indicators
  const [processSteps, setProcessSteps] = useState([]);
  const [currentModel, setCurrentModel] = useState('llama3.2');
  const [processingTime, setProcessingTime] = useState(null);
  
  // Refs
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const handleWebSocketMessage = (data) => {
    console.log('WebSocket message:', data);

    switch (data.type) {
      case 'process_step':
        updateProcessStep(data.step, data.status, data.details);
        break;
        
      case 'tool_execution':
        handleToolExecution(data);
        break;
        
      case 'model_update':
        setCurrentModel(data.model_name);
        addSystemMessage(`Model changed to ${data.model_name}`);
        break;
        
      case 'file_update':
        handleFileUpdate(data);
        break;
        
      case 'error':
        toast.error(data.message);
        setProcessSteps([]);
        setIsLoading(false);
        break;
        
      default:
        console.log('Unknown WebSocket message type:', data.type);
    }
  };
  
  // WebSocket for real-time updates
  const {  connectionStatus, sendMessage: sendWebSocketMessage } = useWebSocket(
    sessionId,
    handleWebSocketMessage
  );

  // Initialize chat session
  useEffect(() => {
    initializeSession();
  }, []);

  // Scroll to bottom when messages change
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const initializeSession = async () => {
    try {
      setIsInitializing(true);
      setError(null);

      // Create new session
      const response = await sessionAPI.create({
        model_preference: 'llama3.2',
        expires_hours: 24,
        metadata: {
          created_from: 'web_interface',
          user_agent: navigator.userAgent
        }
      });

      const newSessionId = response.data.id;
      setSessionId(newSessionId);
      setCurrentModel(response.data.model_preference);

      console.log('Session created:', newSessionId);
      
      // Add welcome message
      addSystemMessage('Welcome! I\'m your invoice reconciliation assistant. You can upload Excel, CSV, or PDF files and ask me questions about invoice data.');
      
    } catch (error) {
      console.error('Failed to initialize session:', error);
      setError(handleAPIError(error));
      toast.error('Failed to start chat session');
    } finally {
      setIsInitializing(false);
    }
  };


  const updateProcessStep = (step, status, details) => {
    const stepNames = {
      file_processing: 'Processing file...',
      query_analysis: 'Analyzing query...',
      tool_selection: 'Selecting tools...',
      tool_execution: 'Executing operations...',
      response_generation: 'Generating response...'
    };

    setProcessSteps(prev => {
      const existing = prev.find(s => s.step === step);
      const newStep = {
        step,
        name: stepNames[step] || step.replace('_', ' '),
        status,
        details,
        timestamp: new Date()
      };

      if (existing) {
        return prev.map(s => s.step === step ? newStep : s);
      } else {
        return [...prev, newStep];
      }
    });
  };

  const handleToolExecution = (data) => {
    if (data.status === 'completed') {
      toast.success(`Tool "${data.tool_name}" executed successfully`);
    } else if (data.status === 'failed') {
      toast.error(`Tool execution failed: ${data.error || 'Unknown error'}`);
    }
  };

  const handleFileUpdate = (data) => {
    switch (data.status) {
      case 'processing':
        updateProcessStep('file_processing', 'in_progress', { filename: data.filename });
        break;
      case 'processed':
        updateProcessStep('file_processing', 'completed', { filename: data.filename });
        toast.success(`File "${data.filename}" processed successfully`);
        break;
      case 'failed':
        updateProcessStep('file_processing', 'failed', { filename: data.filename, error: data.error });
        toast.error(`File processing failed: ${data.error || 'Unknown error'}`);
        break;
      default:
      console.log('Unknown file update status:', data.status);
      break;
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !sessionId) return;

    const messageContent = inputMessage.trim();
    setInputMessage('');
    setIsLoading(true);
    setProcessSteps([]);
    setProcessingTime(null);

    // Add user message to UI immediately
    const userMessage = {
      id: uuidv4(),
      role: 'user',
      content: messageContent,
      timestamp: new Date(),
      local: true // Mark as local until confirmed by server
    };
    setMessages(prev => [...prev, userMessage]);

    const startTime = Date.now();

    try {
      // Send message to API
      const response = await messageAPI.send(sessionId, messageContent);
      
      // Remove local user message and add server response
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      
      const assistantMessage = {
        id: response.data.id,
        role: 'assistant',
        content: response.data.content,
        timestamp: new Date(response.data.created_at),
        metadata: response.data.metadata,
        toolCalls: response.data.tool_calls,
        modelUsed: response.data.model_used,
        confidence: response.data.confidence
      };

      // Add both user and assistant messages
      setMessages(prev => [
        ...prev,
        { ...userMessage, local: false },
        assistantMessage
      ]);

      const endTime = Date.now();
      setProcessingTime(endTime - startTime);

    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Remove the local user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
      
      const errorMsg = handleAPIError(error);
      toast.error(`Failed to send message: ${errorMsg}`);
      
      // Add error message
      addSystemMessage(`Error: ${errorMsg}`, 'error');
      
    } finally {
      setIsLoading(false);
      setProcessSteps([]);
    }
  };

  const addSystemMessage = (content, type = 'info') => {
    const message = {
      id: uuidv4(),
      role: 'system',
      content,
      timestamp: new Date(),
      type
    };
    setMessages(prev => [...prev, message]);
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const retryConnection = () => {
    setError(null);
    initializeSession();
  };

  const clearChat = () => {
    if (window.confirm('Are you sure you want to clear the chat history?')) {
      setMessages([]);
      addSystemMessage('Chat cleared. How can I help you with invoice reconciliation?');
    }
  };

  // Loading state
  if (isInitializing) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-primary-600" />
          <p className="text-gray-600">Initializing chat session...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !sessionId) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center max-w-md">
          <AlertCircle className="w-12 h-12 mx-auto mb-4 text-error-500" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Connection Error</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button onClick={retryConnection} className="btn-primary">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)] max-w-4xl mx-auto">
      {/* Header with model selector and connection status */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white rounded-t-lg">
        <div className="flex items-center space-x-4">
          <ModelSelector 
            sessionId={sessionId}
            currentModel={currentModel}
            onModelChange={setCurrentModel}
          />
          
          {processingTime && (
            <div className="text-sm text-gray-500">
              Last response: {processingTime}ms
            </div>
          )}
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-success-400' :
              connectionStatus === 'connecting' || connectionStatus === 'reconnecting' ? 'bg-warning-400' :
              'bg-error-400'
            }`} />
            <span className="text-sm text-gray-600 capitalize">
              {connectionStatus}
            </span>
          </div>
          
          <button
            onClick={clearChat}
            className="text-sm text-gray-500 hover:text-gray-700"
            disabled={messages.length === 0}
          >
            Clear Chat
          </button>
        </div>
      </div>

      {/* File Upload Area */}
      <FileUpload sessionId={sessionId} />

      {/* Process Indicator */}
      {processSteps.length > 0 && (
        <ProcessIndicator steps={processSteps} />
      )}

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white chat-messages">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        
        {isLoading && (
          <div className="flex justify-start">
            <div className="message-assistant flex items-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Thinking...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200 bg-white rounded-b-lg">
        <div className="flex space-x-3">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about invoice reconciliation, upload files, or request analysis..."
              className="input resize-none"
              rows={1}
              style={{
                minHeight: '2.5rem',
                maxHeight: '8rem'
              }}
              disabled={isLoading || !sessionId}
            />
          </div>
          
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading || !sessionId}
            className="btn-primary px-4 py-2 flex items-center justify-center"
            style={{ minHeight: '2.5rem' }}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
        
        <div className="mt-2 text-xs text-gray-500">
          Press Enter to send, Shift+Enter for new line
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;