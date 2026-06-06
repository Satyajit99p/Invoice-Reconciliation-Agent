import React, { useState, useEffect } from 'react';
import { Fragment } from 'react';
import { Listbox, Transition } from '@headlessui/react';
import { ChevronDown, Check, Wifi, WifiOff } from 'lucide-react';
import toast from 'react-hot-toast';
import clsx from 'clsx';

import { modelAPI, handleAPIError } from '../services/api';

const ModelSelector = ({ sessionId, currentModel, onModelChange }) => {
  const [availableModels, setAvailableModels] = useState({ ollama: [], openai: [], anthropic: [] });
  const [selectedModel, setSelectedModel] = useState({ name: currentModel, provider: 'ollama' });
  const [isLoading, setIsLoading] = useState(true);
  const [isChanging, setIsChanging] = useState(false);
  const [modelHealth, setModelHealth] = useState({});

  useEffect(() => {
    loadAvailableModels();
    checkModelHealth();
  }, []);

  useEffect(() => {
    if (currentModel !== selectedModel.name) {
      setSelectedModel(prev => ({
        ...prev,
        name: currentModel
      }));
    }
  }, [currentModel]);

  const loadAvailableModels = async () => {
    try {
      setIsLoading(true);
      const response = await modelAPI.list();
      setAvailableModels(response.data.models);
      
      // Update selected model provider if needed
      const allModels = flattenModels(response.data.models);
      const current = allModels.find(m => m.name === currentModel);
      if (current) {
        setSelectedModel({ name: currentModel, provider: current.provider });
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      toast.error('Failed to load available models');
    } finally {
      setIsLoading(false);
    }
  };

  const checkModelHealth = async () => {
    try {
      const response = await modelAPI.checkHealth();
      setModelHealth(response.data.providers || {});
    } catch (error) {
      console.error('Failed to check model health:', error);
    }
  };

  const flattenModels = (models) => {
    const flattened = [];
    Object.entries(models).forEach(([provider, modelList]) => {
      modelList.forEach(model => {
        flattened.push({
          ...model,
          provider,
          displayName: `${model.name} (${provider})`,
          id: `${provider}:${model.name}`
        });
      });
    });
    return flattened;
  };

  const handleModelChange = async (newModel) => {
    if (newModel.name === selectedModel.name && newModel.provider === selectedModel.provider) {
      return;
    }

    setIsChanging(true);
    
    try {
      await modelAPI.select(sessionId, newModel.name, newModel.provider);
      
      setSelectedModel(newModel);
      onModelChange?.(newModel.name);
      
      toast.success(`Switched to ${newModel.name}`);
    } catch (error) {
      console.error('Failed to change model:', error);
      toast.error(`Failed to switch model: ${handleAPIError(error)}`);
    } finally {
      setIsChanging(false);
    }
  };

  const getModelIcon = (provider, available) => {
    const iconClass = "w-4 h-4";
    
    if (!available) {
      return <WifiOff className={clsx(iconClass, "text-gray-400")} />;
    }

    switch (provider) {
      case 'ollama':
        return <div className={clsx("w-4 h-4 rounded bg-blue-500")} />;
      case 'openai':
        return <div className={clsx("w-4 h-4 rounded bg-green-500")} />;
      case 'anthropic':
        return <div className={clsx("w-4 h-4 rounded bg-orange-500")} />;
      default:
        return <Wifi className={clsx(iconClass, "text-gray-500")} />;
    }
  };

  const getProviderStatus = (provider) => {
    return modelHealth[provider] === true;
  };

  const allModels = flattenModels(availableModels);
  const currentSelectedModel = allModels.find(m => 
    m.name === selectedModel.name && m.provider === selectedModel.provider
  ) || allModels[0];

  if (isLoading) {
    return (
      <div className="flex items-center space-x-2">
        <div className="w-4 h-4 bg-gray-300 rounded animate-pulse" />
        <span className="text-sm text-gray-500">Loading models...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-3">
      <span className="text-sm font-medium text-gray-700">Model:</span>
      
      <Listbox value={currentSelectedModel} onChange={handleModelChange} disabled={isChanging}>
        <div className="relative">
          <Listbox.Button className="relative w-48 cursor-pointer rounded-lg bg-white py-2 pl-3 pr-10 text-left border border-gray-300 focus:outline-none focus-visible:border-primary-500 focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-opacity-75 focus-visible:ring-offset-2 focus-visible:ring-offset-primary-300 sm:text-sm">
            <span className="flex items-center space-x-2 truncate">
              {currentSelectedModel && (
                <>
                  {getModelIcon(currentSelectedModel.provider, currentSelectedModel.available)}
                  <span className="text-sm">
                    {currentSelectedModel.name}
                  </span>
                  <span className="text-xs text-gray-500">
                    ({currentSelectedModel.provider})
                  </span>
                </>
              )}
            </span>
            <span className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-2">
              {isChanging ? (
                <div className="w-4 h-4 border-2 border-gray-300 border-t-primary-600 rounded-full animate-spin" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-400" aria-hidden="true" />
              )}
            </span>
          </Listbox.Button>
          
          <Transition
            as={Fragment}
            leave="transition ease-in duration-100"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Listbox.Options className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none sm:text-sm">
              {Object.entries(availableModels).map(([provider, models]) => {
                const providerHealthy = getProviderStatus(provider);
                
                return (
                  <Fragment key={provider}>
                    {/* Provider Header */}
                    <div className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase tracking-wide bg-gray-50 border-b">
                      <div className="flex items-center justify-between">
                        <span>{provider}</span>
                        <div className={clsx(
                          "w-2 h-2 rounded-full",
                          providerHealthy ? "bg-green-400" : "bg-gray-300"
                        )} />
                      </div>
                    </div>
                    
                    {/* Models for this provider */}
                    {models.length === 0 ? (
                      <div className="px-3 py-2 text-sm text-gray-400 italic">
                        No models available
                      </div>
                    ) : (
                      models.map((model) => (
                        <Listbox.Option
                          key={`${provider}:${model.name}`}
                          className={({ active }) =>
                            clsx(
                              'relative cursor-pointer select-none py-2 pl-10 pr-4',
                              active ? 'bg-primary-100 text-primary-900' : 'text-gray-900',
                              !model.available && 'opacity-50 cursor-not-allowed'
                            )
                          }
                          value={{ name: model.name, provider }}
                          disabled={!model.available}
                        >
                          {({ selected }) => (
                            <>
                              <span
                                className={clsx(
                                  'block truncate',
                                  selected ? 'font-medium' : 'font-normal'
                                )}
                              >
                                <div className="flex items-center space-x-2">
                                  <span>{model.name}</span>
                                  {!model.available && (
                                    <span className="text-xs text-gray-400">(unavailable)</span>
                                  )}
                                </div>
                                {model.description && (
                                  <div className="text-xs text-gray-500 truncate">
                                    {model.description}
                                  </div>
                                )}
                              </span>
                              
                              {selected ? (
                                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-primary-600">
                                  <Check className="h-5 w-5" aria-hidden="true" />
                                </span>
                              ) : (
                                <span className="absolute inset-y-0 left-0 flex items-center pl-3">
                                  {getModelIcon(provider, model.available)}
                                </span>
                              )}
                            </>
                          )}
                        </Listbox.Option>
                      ))
                    )}
                  </Fragment>
                );
              })}
              
              {/* Refresh Option */}
              <div className="border-t mt-1 pt-1">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    loadAvailableModels();
                    checkModelHealth();
                  }}
                  className="w-full px-3 py-2 text-left text-sm text-gray-500 hover:bg-gray-50 focus:bg-gray-50"
                >
                  🔄 Refresh models
                </button>
              </div>
            </Listbox.Options>
          </Transition>
        </div>
      </Listbox>
      
      {/* Health indicators */}
      <div className="flex items-center space-x-1">
        {Object.entries(modelHealth).map(([provider, healthy]) => (
          <div
            key={provider}
            className={clsx(
              "w-2 h-2 rounded-full",
              healthy ? "bg-green-400" : "bg-red-400"
            )}
            title={`${provider}: ${healthy ? 'healthy' : 'unavailable'}`}
          />
        ))}
      </div>
    </div>
  );
};

export default ModelSelector;