'use client';

import { useState, useEffect } from 'react';
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Brain } from 'lucide-react';

interface LLMModel {
  id: string;
  name: string;
  provider: string;
  description: string;
  is_current: boolean;
}

interface LLMSelectorProps {
  selectedModel: string | null;
  onSelectModel: (model: string) => void;
  disabled?: boolean;
}

export function LLMSelector({ selectedModel, onSelectModel, disabled = false }: LLMSelectorProps) {
  const [models, setModels] = useState<LLMModel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const response = await fetch(`${apiUrl}/system/models`);

        if (response.ok) {
          const data = await response.json();
          setModels(data.models);

          // Set default to current model if no selection yet
          if (!selectedModel && data.current) {
            onSelectModel(data.current);
          }
        }
      } catch (error) {
        console.error('Failed to fetch models:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchModels();
  }, [selectedModel, onSelectModel]);

  if (loading || models.length === 0) {
    return null;
  }

  return (
    <Select value={selectedModel || undefined} onValueChange={onSelectModel} disabled={disabled}>
      <SelectTrigger className="w-[180px] h-9">
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary shrink-0" />
          <SelectValue placeholder="Select model..." />
        </div>
      </SelectTrigger>
      <SelectContent>
        <SelectGroup>
          {models.map((model) => (
            <SelectItem key={model.id} value={model.id}>
              <span className="font-medium">{model.name}</span>
            </SelectItem>
          ))}
        </SelectGroup>
      </SelectContent>
    </Select>
  );
}
