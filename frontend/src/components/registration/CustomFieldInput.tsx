import React from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Checkbox } from '@/components/ui/checkbox';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { EventCustomField } from '@/api/events/types';

interface CustomFieldInputProps {
    field: EventCustomField;
    value: any;
    onChange: (value: any) => void;
    error?: string;
}

/**
 * Renders a form input for a custom registration field.
 * Supports: text, number, date, select, checkbox field types.
 */
export function CustomFieldInput({ field, value, onChange, error }: CustomFieldInputProps) {
    const { name, field_type, is_required, options } = field;
    const fieldId = `custom-field-${field.uuid}`;

    const renderInput = () => {
        switch (field_type) {
            case 'text':
                return (
                    <Input
                        id={fieldId}
                        type="text"
                        value={value || ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={is_required}
                        placeholder={`Enter ${name.toLowerCase()}`}
                    />
                );

            case 'number':
                return (
                    <Input
                        id={fieldId}
                        type="number"
                        value={value || ''}
                        onChange={(e) => onChange(e.target.valueAsNumber || '')}
                        required={is_required}
                        placeholder={`Enter ${name.toLowerCase()}`}
                    />
                );

            case 'date':
                return (
                    <Input
                        id={fieldId}
                        type="date"
                        value={value || ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={is_required}
                    />
                );

            case 'select':
                const selectOptions = parseOptions(options);
                return (
                    <Select value={value || ''} onValueChange={onChange}>
                        <SelectTrigger>
                            <SelectValue placeholder={`Select ${name.toLowerCase()}`} />
                        </SelectTrigger>
                        <SelectContent>
                            {selectOptions.map((opt) => (
                                <SelectItem key={opt.value} value={opt.value}>
                                    {opt.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                );

            case 'checkbox':
                return (
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id={fieldId}
                            checked={!!value}
                            onCheckedChange={(checked) => onChange(checked)}
                        />
                        <Label htmlFor={fieldId} className="text-sm font-normal cursor-pointer">
                            {name}
                        </Label>
                    </div>
                );

            default:
                return (
                    <Input
                        id={fieldId}
                        type="text"
                        value={value || ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={is_required}
                    />
                );
        }
    };

    // Checkbox has its own label inline
    if (field_type === 'checkbox') {
        return (
            <div className="space-y-1">
                {renderInput()}
                {error && <p className="text-sm text-red-500">{error}</p>}
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <Label htmlFor={fieldId}>
                {name}
                {is_required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            {renderInput()}
            {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
    );
}

/**
 * Parse options from various formats into a consistent array.
 */
function parseOptions(options: any): { value: string; label: string }[] {
    if (!options) return [];

    // Already an array of objects
    if (Array.isArray(options)) {
        return options.map((opt) => {
            if (typeof opt === 'string') {
                return { value: opt, label: opt };
            }
            return { value: opt.value || opt, label: opt.label || opt.value || opt };
        });
    }

    // Object with key-value pairs
    if (typeof options === 'object') {
        return Object.entries(options).map(([key, val]) => ({
            value: key,
            label: String(val),
        }));
    }

    return [];
}

interface CustomFieldsFormProps {
    fields: EventCustomField[];
    values: Record<string, any>;
    onChange: (fieldUuid: string, value: any) => void;
    errors?: Record<string, string>;
}

/**
 * Renders all custom fields for an event registration form.
 */
export function CustomFieldsForm({ fields, values, onChange, errors = {} }: CustomFieldsFormProps) {
    if (!fields || fields.length === 0) {
        return null;
    }

    return (
        <div className="space-y-4">
            <h4 className="font-medium text-foreground">Additional Information</h4>
            {fields.map((field) => (
                <CustomFieldInput
                    key={field.uuid}
                    field={field}
                    value={values[field.uuid]}
                    onChange={(value) => onChange(field.uuid, value)}
                    error={errors[field.uuid]}
                />
            ))}
        </div>
    );
}
