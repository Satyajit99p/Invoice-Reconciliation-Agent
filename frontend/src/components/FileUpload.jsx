import React, { useState, useCallback, useRef } from 'react';
import { useDropzone } from 'react-dropzone';
import toast from 'react-hot-toast';
import { 
  Upload, 
  File, 
  FileText, 
  FileSpreadsheet,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  Download
} from 'lucide-react';

import { fileAPI, handleAPIError } from '../services/api';

const FileUpload = ({ sessionId }) => {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef(null);

  // Accepted file types
  const acceptedTypes = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    'application/vnd.ms-excel': ['.xls'],
    'text/csv': ['.csv'],
    'application/pdf': ['.pdf']
  };

  const maxFileSize = 10 * 1024 * 1024; // 10MB

  const getFileIcon = (mimeType, fileName) => {
    if (mimeType?.includes('spreadsheet') || fileName?.endsWith('.xlsx') || fileName?.endsWith('.xls')) {
      return <FileSpreadsheet className="w-5 h-5 text-green-600" />;
    }
    if (mimeType?.includes('csv') || fileName?.endsWith('.csv')) {
      return <FileSpreadsheet className="w-5 h-5 text-blue-600" />;
    }
    if (mimeType?.includes('pdf') || fileName?.endsWith('.pdf')) {
      return <FileText className="w-5 h-5 text-red-600" />;
    }
    return <File className="w-5 h-5 text-gray-600" />;
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file) => {
    // Check file size
    if (file.size > maxFileSize) {
      return `File too large. Maximum size is ${formatFileSize(maxFileSize)}.`;
    }

    // Check file type
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    const isValidType = Object.values(acceptedTypes).some(extensions => 
      extensions.includes(fileExtension)
    );

    if (!isValidType) {
      return 'Invalid file type. Please upload Excel (.xlsx, .xls), CSV (.csv), or PDF files.';
    }

    return null;
  };

  const uploadFile = async (file) => {
    const fileId = Math.random().toString(36).substr(2, 9);
    
    // Validate file before upload
    const validationError = validateFile(file);
    if (validationError) {
      toast.error(validationError);
      return;
    }

    // Add file to state with pending status
    const fileInfo = {
      id: fileId,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      progress: 0
    };

    setUploadedFiles(prev => [...prev, fileInfo]);
    setIsUploading(true);

    try {
      // Upload file with progress tracking
      const response = await fileAPI.upload(
        sessionId,
        file,
        (progress) => {
          setUploadProgress(prev => ({
            ...prev,
            [fileId]: progress
          }));
          
          setUploadedFiles(prev =>
            prev.map(f => 
              f.id === fileId 
                ? { ...f, progress }
                : f
            )
          );
        }
      );

      // Update file status on success
      setUploadedFiles(prev =>
        prev.map(f => 
          f.id === fileId 
            ? { 
                ...f, 
                id: response.data.id,
                status: response.data.processing_status || 'processing',
                progress: 100,
                serverData: response.data
              }
            : f
        )
      );

      toast.success(`File "${file.name}" uploaded successfully`);

    } catch (error) {
      console.error('File upload failed:', error);
      const errorMessage = handleAPIError(error);
      
      // Update file status on error
      setUploadedFiles(prev =>
        prev.map(f => 
          f.id === fileId 
            ? { ...f, status: 'failed', error: errorMessage }
            : f
        )
      );

      toast.error(`Upload failed: ${errorMessage}`);
    } finally {
      setIsUploading(false);
      setUploadProgress(prev => {
        const newProgress = { ...prev };
        delete newProgress[fileId];
        return newProgress;
      });
    }
  };

  const onDrop = useCallback(async (acceptedFiles) => {
    if (!sessionId) {
      toast.error('No active session. Please refresh the page.');
      return;
    }

    for (const file of acceptedFiles) {
      await uploadFile(file);
    }
  }, [sessionId]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: acceptedTypes,
    maxSize: maxFileSize,
    multiple: true,
    disabled: !sessionId
  });

  const removeFile = async (fileId) => {
    try {
      const file = uploadedFiles.find(f => f.id === fileId);
      if (file?.serverData?.id) {
        await fileAPI.delete(sessionId, file.serverData.id);
      }
      
      setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
      toast.success('File removed');
    } catch (error) {
      console.error('Failed to remove file:', error);
      toast.error('Failed to remove file');
    }
  };

  const downloadFile = async (file) => {
    try {
      if (!file.serverData?.id) {
        toast.error('File not available for download');
        return;
      }

      const response = await fileAPI.download(sessionId, file.serverData.id);
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', file.name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('File downloaded');
    } catch (error) {
      console.error('Failed to download file:', error);
      toast.error('Failed to download file');
    }
  };

  const renderFileStatus = (file) => {
    switch (file.status) {
      case 'uploading':
        return (
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
            <span className="text-sm text-primary-600">
              Uploading... {file.progress || 0}%
            </span>
          </div>
        );
      
      case 'processing':
      case 'pending':
        return (
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-warning-600" />
            <span className="text-sm text-warning-600">Processing...</span>
          </div>
        );
      
      case 'processed':
        return (
          <div className="flex items-center space-x-2">
            <CheckCircle className="w-4 h-4 text-success-600" />
            <span className="text-sm text-success-600">Ready</span>
          </div>
        );
      
      case 'failed':
        return (
          <div className="flex items-center space-x-2">
            <AlertCircle className="w-4 h-4 text-error-600" />
            <span className="text-sm text-error-600">Failed</span>
          </div>
        );
      
      default:
        return null;
    }
  };

  return (
    <div className="border-b border-gray-200 bg-gray-50 p-4">
      {/* Upload Area */}
      <div
        {...getRootProps()}
        className={`file-upload-area cursor-pointer ${
          isDragActive ? 'drag-active' : ''
        } ${!sessionId ? 'opacity-50 cursor-not-allowed' : ''}`}
      >
        <input {...getInputProps()} ref={fileInputRef} />
        
        <div className="flex flex-col items-center space-y-2">
          <Upload className={`w-8 h-8 ${
            isDragActive ? 'text-primary-600' : 'text-gray-400'
          }`} />
          
          <div className="text-center">
            <p className="text-sm font-medium text-gray-900">
              {isDragActive ? 'Drop files here...' : 'Upload invoice files'}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Drag & drop or click to browse • Excel, CSV, PDF • Max {formatFileSize(maxFileSize)}
            </p>
          </div>
        </div>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-4 space-y-2">
          <h4 className="text-sm font-medium text-gray-900">Uploaded Files</h4>
          
          <div className="space-y-2">
            {uploadedFiles.map((file) => (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 bg-white border border-gray-200 rounded-lg"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  {getFileIcon(file.type, file.name)}
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </p>
                    {file.error && (
                      <p className="text-xs text-error-600 mt-1">
                        {file.error}
                      </p>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0">
                    {renderFileStatus(file)}
                  </div>
                </div>

                <div className="flex items-center space-x-2 ml-4">
                  {file.status === 'processed' && (
                    <button
                      onClick={() => downloadFile(file)}
                      className="p-1 text-gray-400 hover:text-gray-600"
                      title="Download file"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  )}
                  
                  <button
                    onClick={() => removeFile(file.id)}
                    className="p-1 text-gray-400 hover:text-error-600"
                    title="Remove file"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload Progress */}
      {isUploading && Object.keys(uploadProgress).length > 0 && (
        <div className="mt-4 p-3 bg-primary-50 rounded-lg">
          <div className="flex items-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-primary-600" />
            <span className="text-sm text-primary-800 font-medium">
              Uploading files...
            </span>
          </div>
        </div>
      )}
    </div>
  );
};

export default FileUpload;