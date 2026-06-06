import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { format } from 'date-fns';
import { 
  User, 
  Bot, 
  Info, 
  AlertTriangle, 
  CheckCircle,
  Clock,
  Zap,
  ChevronDown,
  ChevronRight
} from 'lucide-react';

const MessageBubble = ({ message }) => {
  const [showDetails, setShowDetails] = useState(false);
  
  const formatTimestamp = (timestamp) => {
    return format(new Date(timestamp), 'HH:mm');
  };

  const renderMessageIcon = () => {
    switch (message.role) {
      case 'user':
        return <User className="w-4 h-4" />;
      case 'assistant':
        return <Bot className="w-4 h-4" />;
      case 'system':
        switch (message.type) {
          case 'error':
            return <AlertTriangle className="w-4 h-4" />;
          case 'success':
            return <CheckCircle className="w-4 h-4" />;
          default:
            return <Info className="w-4 h-4" />;
        }
      default:
        return <Info className="w-4 h-4" />;
    }
  };

  const renderToolCalls = () => {
    if (!message.toolCalls || message.toolCalls.length === 0) return null;

    return (
      <div className="mt-3 space-y-2">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Tools Used
        </div>
        {message.toolCalls.map((tool, index) => (
          <div key={index} className="bg-gray-50 rounded p-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="font-mono text-primary-600">{tool.name}</span>
              {tool.execution_time && (
                <span className="text-gray-500 text-xs">
                  {tool.execution_time}ms
                </span>
              )}
            </div>
            
            {tool.error && (
              <div className="mt-1 text-error-600 text-xs">
                Error: {tool.error}
              </div>
            )}
            
            {showDetails && tool.arguments && Object.keys(tool.arguments).length > 0 && (
              <div className="mt-2">
                <div className="text-xs text-gray-500 mb-1">Arguments:</div>
                <pre className="text-xs bg-white p-1 rounded border overflow-x-auto">
                  {JSON.stringify(tool.arguments, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderMetadata = () => {
    if (!showDetails) return null;

    const metadata = message.metadata || {};
    const hasMetadata = Object.keys(metadata).length > 0;

    if (!hasMetadata && !message.confidence && !message.modelUsed) return null;

    return (
      <div className="mt-3 pt-3 border-t border-gray-200 space-y-2">
        <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
          Details
        </div>
        
        <div className="grid grid-cols-2 gap-2 text-xs">
          {message.modelUsed && (
            <div>
              <span className="text-gray-500">Model:</span>
              <span className="ml-1 font-mono">{message.modelUsed}</span>
            </div>
          )}
          
          {message.confidence && (
            <div>
              <span className="text-gray-500">Confidence:</span>
              <span className="ml-1">{Math.round(message.confidence * 100)}%</span>
            </div>
          )}
          
          {metadata.processing_time && (
            <div>
              <span className="text-gray-500">Processing:</span>
              <span className="ml-1">{Math.round(metadata.processing_time * 1000)}ms</span>
            </div>
          )}
          
          {message.timestamp && (
            <div>
              <span className="text-gray-500">Time:</span>
              <span className="ml-1">{formatTimestamp(message.timestamp)}</span>
            </div>
          )}
        </div>

        {hasMetadata && (
          <details className="mt-2">
            <summary className="text-xs text-gray-500 cursor-pointer">
              Raw Metadata
            </summary>
            <pre className="mt-1 text-xs bg-gray-100 p-2 rounded overflow-x-auto">
              {JSON.stringify(metadata, null, 2)}
            </pre>
          </details>
        )}
      </div>
    );
  };

  const hasDetails = message.toolCalls?.length > 0 || 
                   message.metadata || 
                   message.confidence || 
                   message.modelUsed;

  // User message
  if (message.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="message-user relative group">
          <div className="flex items-start space-x-2">
            <div className="flex-1">
              <div className="whitespace-pre-wrap break-words">
                {message.content}
              </div>
            </div>
            <div className="flex-shrink-0">
              {renderMessageIcon()}
            </div>
          </div>
          
          {message.local && (
            <div className="absolute -top-1 -right-1">
              <div className="w-2 h-2 bg-warning-400 rounded-full animate-pulse" />
            </div>
          )}
          
          <div className="text-xs text-blue-200 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {formatTimestamp(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  // Assistant message
  if (message.role === 'assistant') {
    return (
      <div className="flex justify-start">
        <div className="message-assistant relative group max-w-full">
          <div className="flex items-start space-x-2">
            <div className="flex-shrink-0 mt-1">
              {renderMessageIcon()}
            </div>
            <div className="flex-1 min-w-0">
              <div className="markdown-content">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]}
                  components={{
                    // Customize code blocks
                    code: ({ node, inline, className, children, ...props }) => {
                      if (inline) {
                        return (
                          <code className="bg-gray-100 text-gray-800 px-1 py-0.5 rounded text-sm font-mono" {...props}>
                            {children}
                          </code>
                        );
                      }
                      return (
                        <pre className="bg-gray-100 text-gray-800 p-3 rounded-lg overflow-x-auto text-sm font-mono">
                          <code {...props}>{children}</code>
                        </pre>
                      );
                    },
                    // Customize links
                    a: ({ href, children }) => (
                      <a 
                        href={href} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-primary-600 hover:text-primary-800 underline"
                      >
                        {children}
                      </a>
                    )
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
              
              {renderToolCalls()}
              {renderMetadata()}
            </div>
          </div>
          
          {hasDetails && (
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="absolute -bottom-1 -right-1 p-1 bg-white border border-gray-200 rounded-full shadow-sm hover:bg-gray-50 opacity-0 group-hover:opacity-100 transition-opacity"
              title={showDetails ? 'Hide details' : 'Show details'}
            >
              {showDetails ? (
                <ChevronDown className="w-3 h-3 text-gray-500" />
              ) : (
                <ChevronRight className="w-3 h-3 text-gray-500" />
              )}
            </button>
          )}
          
          <div className="text-xs text-gray-400 mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
            {formatTimestamp(message.timestamp)}
          </div>
        </div>
      </div>
    );
  }

  // System message
  return (
    <div className="flex justify-center">
      <div className={`message-system flex items-center space-x-2 ${
        message.type === 'error' ? 'bg-error-50 text-error-700 border-error-200' :
        message.type === 'success' ? 'bg-success-50 text-success-700 border-success-200' :
        'bg-gray-100 text-gray-600'
      }`}>
        {renderMessageIcon()}
        <span className="text-sm">{message.content}</span>
        <span className="text-xs opacity-60">
          {formatTimestamp(message.timestamp)}
        </span>
      </div>
    </div>
  );
};

export default MessageBubble;