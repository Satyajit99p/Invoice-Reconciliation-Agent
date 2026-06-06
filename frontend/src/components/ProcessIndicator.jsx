import React from 'react';
import { 
  Loader2, 
  CheckCircle, 
  XCircle, 
  Clock,
  FileSearch,
  Search,
  Zap,
  MessageSquare,
  PlayCircle
} from 'lucide-react';
import { format } from 'date-fns';

const ProcessIndicator = ({ steps }) => {
  const getStepIcon = (step, status) => {
    const iconClass = "w-4 h-4";
    
    // Status-based icons
    switch (status) {
      case 'starting':
        return <PlayCircle className={`${iconClass} text-warning-600`} />;
      case 'in_progress':
        return <Loader2 className={`${iconClass} text-primary-600 animate-spin`} />;
      case 'completed':
        return <CheckCircle className={`${iconClass} text-success-600`} />;
      case 'failed':
        return <XCircle className={`${iconClass} text-error-600`} />;
      default:
        return <Clock className={`${iconClass} text-gray-400`} />;
    }
  };

  const getStepName = (step) => {
    const stepNames = {
      file_processing: 'Processing Files',
      query_analysis: 'Analyzing Query',
      tool_selection: 'Selecting Tools',
      tool_execution: 'Executing Operations',
      response_generation: 'Generating Response'
    };

    return stepNames[step] || step.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  const getStepDetails = (step, details) => {
    if (!details) return null;

    const detailTexts = [];

    switch (step.step) {
      case 'query_analysis':
        if (details.predicted_tool) {
          detailTexts.push(`Tool: ${details.predicted_tool}`);
        }
        if (details.confidence) {
          detailTexts.push(`Confidence: ${Math.round(details.confidence * 100)}%`);
        }
        break;
      
      case 'tool_execution':
        if (details.tools_executed) {
          detailTexts.push(`${details.tools_executed} tool(s) executed`);
        }
        break;
      
      case 'file_processing':
        if (details.filename) {
          detailTexts.push(`File: ${details.filename}`);
        }
        break;
      
      default:
        // Generic details handling
        Object.entries(details).forEach(([key, value]) => {
          if (typeof value === 'string' || typeof value === 'number') {
            detailTexts.push(`${key}: ${value}`);
          }
        });
    }

    return detailTexts.length > 0 ? detailTexts.join(' • ') : null;
  };

  const getStepProgress = (steps) => {
    const completedSteps = steps.filter(s => s.status === 'completed').length;
    const totalSteps = steps.length;
    const hasFailedStep = steps.some(s => s.status === 'failed');
    
    return {
      percentage: totalSteps > 0 ? (completedSteps / totalSteps) * 100 : 0,
      completed: completedSteps,
      total: totalSteps,
      failed: hasFailedStep
    };
  };

  const formatDuration = (startTime, endTime) => {
    if (!startTime) return null;
    
    const start = new Date(startTime);
    const end = endTime ? new Date(endTime) : new Date();
    const duration = end - start;
    
    if (duration < 1000) {
      return `${duration}ms`;
    } else if (duration < 60000) {
      return `${(duration / 1000).toFixed(1)}s`;
    } else {
      return `${Math.round(duration / 60000)}m ${Math.round((duration % 60000) / 1000)}s`;
    }
  };

  const progress = getStepProgress(steps);

  if (steps.length === 0) {
    return null;
  }

  return (
    <div className="border-b border-gray-200 bg-gray-50 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-medium text-gray-900">Processing Status</h4>
        
        <div className="flex items-center space-x-2">
          <div className="text-xs text-gray-500">
            {progress.completed}/{progress.total} steps
          </div>
          
          {/* Progress bar */}
          <div className="w-20 bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-500 ${
                progress.failed ? 'bg-error-500' : 'bg-success-500'
              }`}
              style={{ width: `${progress.percentage}%` }}
            />
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {steps.map((step, index) => {
          const details = getStepDetails(step, step.details);
          const duration = formatDuration(step.timestamp);
          
          return (
            <div
              key={`${step.step}-${index}`}
              className={`process-step ${
                step.status === 'starting' ? 'process-step-starting' :
                step.status === 'in_progress' ? 'process-step-in-progress' :
                step.status === 'completed' ? 'process-step-completed' :
                step.status === 'failed' ? 'process-step-failed' :
                'bg-gray-50 text-gray-500'
              }`}
            >
              <div className="flex items-center justify-between w-full">
                <div className="flex items-center space-x-3">
                  {getStepIcon(step.step, step.status)}
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className="font-medium text-sm">
                        {getStepName(step.step)}
                      </span>
                      
                      {step.status === 'in_progress' && (
                        <div className="flex space-x-1">
                          <div className="w-1 h-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                          <div className="w-1 h-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                          <div className="w-1 h-1 bg-current rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                        </div>
                      )}
                    </div>
                    
                    {details && (
                      <div className="text-xs opacity-75 mt-1">
                        {details}
                      </div>
                    )}
                    
                    {step.status === 'failed' && step.details?.error && (
                      <div className="text-xs mt-1 font-medium">
                        Error: {step.details.error}
                      </div>
                    )}
                  </div>
                </div>
                
                {duration && (
                  <div className="text-xs opacity-60 font-mono">
                    {duration}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Overall status indicator */}
      {progress.failed && (
        <div className="mt-3 p-2 bg-error-50 border border-error-200 rounded text-error-700 text-sm">
          ⚠️ Processing encountered errors. Some operations may have failed.
        </div>
      )}
      
      {progress.percentage === 100 && !progress.failed && (
        <div className="mt-3 p-2 bg-success-50 border border-success-200 rounded text-success-700 text-sm">
          ✅ All processing steps completed successfully.
        </div>
      )}
    </div>
  );
};

export default ProcessIndicator;