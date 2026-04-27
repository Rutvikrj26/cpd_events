import React from 'react';
import { Label } from '@/shared/ui/label';
import { Textarea } from '@/shared/ui/textarea';

interface RubricEditorProps {
    value: string;
    onChange: (value: string) => void;
}

export function RubricEditor({ value, onChange }: RubricEditorProps) {
    return (
        <div className="space-y-2">
            <Label htmlFor="assignment-rubric">Rubric (JSON, optional)</Label>
            <Textarea
                id="assignment-rubric"
                value={value}
                onChange={(e) => onChange(e.target.value)}
                placeholder='{"criteria": []}'
                className="min-h-[100px] font-mono text-sm"
            />
            <p className="text-xs text-muted-foreground">
                Paste a JSON rubric object. Must be valid JSON if provided.
            </p>
        </div>
    );
}
