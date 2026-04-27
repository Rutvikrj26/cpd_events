import { Input } from '@/shared/ui/input';
import { Textarea } from '@/shared/ui/textarea';
import { Label } from '@/shared/ui/label';
import { Checkbox } from '@/shared/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/shared/ui/radio-group';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/ui/select';
import { EventCustomField } from '@/api/events/types';

interface CustomFieldInputProps {
    field: EventCustomField;
    value: any;
    onChange: (value: any) => void;
    error?: string;
}

export function CustomFieldInput({ field, value, onChange, error }: CustomFieldInputProps) {
    const { label, field_type, required, placeholder, help_text, options, min_value, max_value } =
        field;
    const fieldId = `custom-field-${field.uuid}`;
    const selectOptions = normalizeOptions(options);

    const renderInput = () => {
        switch (field_type) {
            case 'text':
                return (
                    <Input
                        id={fieldId}
                        type="text"
                        value={value ?? ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={required}
                        placeholder={placeholder}
                    />
                );

            case 'textarea':
                return (
                    <Textarea
                        id={fieldId}
                        value={value ?? ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={required}
                        placeholder={placeholder}
                    />
                );

            case 'number':
                return (
                    <Input
                        id={fieldId}
                        type="number"
                        value={value ?? ''}
                        min={min_value ?? undefined}
                        max={max_value ?? undefined}
                        onChange={(e) =>
                            onChange(e.target.value === '' ? '' : Number(e.target.value))
                        }
                        required={required}
                        placeholder={placeholder}
                    />
                );

            case 'date':
                return (
                    <Input
                        id={fieldId}
                        type="date"
                        value={value ?? ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={required}
                    />
                );

            case 'select':
                return (
                    <Select value={value ?? ''} onValueChange={onChange}>
                        <SelectTrigger id={fieldId}>
                            <SelectValue
                                placeholder={placeholder || `Select ${label.toLowerCase()}`}
                            />
                        </SelectTrigger>
                        <SelectContent>
                            {selectOptions.map((opt) => (
                                <SelectItem key={opt} value={opt}>
                                    {opt}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                );

            case 'multiselect': {
                const current: string[] = Array.isArray(value) ? value : [];
                return (
                    <div className="space-y-2">
                        {selectOptions.map((opt) => {
                            const optId = `${fieldId}-${opt}`;
                            const checked = current.includes(opt);
                            return (
                                <div key={opt} className="flex items-center space-x-2">
                                    <Checkbox
                                        id={optId}
                                        checked={checked}
                                        onCheckedChange={(next) => {
                                            onChange(
                                                next
                                                    ? [...current, opt]
                                                    : current.filter((v) => v !== opt),
                                            );
                                        }}
                                    />
                                    <Label htmlFor={optId} className="font-normal cursor-pointer">
                                        {opt}
                                    </Label>
                                </div>
                            );
                        })}
                    </div>
                );
            }

            case 'radio':
                return (
                    <RadioGroup value={value ?? ''} onValueChange={onChange}>
                        {selectOptions.map((opt) => {
                            const optId = `${fieldId}-${opt}`;
                            return (
                                <div key={opt} className="flex items-center space-x-2">
                                    <RadioGroupItem id={optId} value={opt} />
                                    <Label htmlFor={optId} className="font-normal cursor-pointer">
                                        {opt}
                                    </Label>
                                </div>
                            );
                        })}
                    </RadioGroup>
                );

            case 'checkbox':
                return (
                    <div className="flex items-center space-x-2">
                        <Checkbox
                            id={fieldId}
                            checked={!!value}
                            onCheckedChange={(checked) => onChange(!!checked)}
                        />
                        <Label htmlFor={fieldId} className="text-sm font-normal cursor-pointer">
                            {label}
                            {required && <span className="text-red-500 ml-1">*</span>}
                        </Label>
                    </div>
                );

            default:
                return (
                    <Input
                        id={fieldId}
                        type="text"
                        value={value ?? ''}
                        onChange={(e) => onChange(e.target.value)}
                        required={required}
                    />
                );
        }
    };

    if (field_type === 'checkbox') {
        return (
            <div className="space-y-1">
                {renderInput()}
                {help_text && <p className="text-xs text-muted-foreground">{help_text}</p>}
                {error && <p className="text-sm text-red-500">{error}</p>}
            </div>
        );
    }

    return (
        <div className="space-y-2">
            <Label htmlFor={fieldId}>
                {label}
                {required && <span className="text-red-500 ml-1">*</span>}
            </Label>
            {renderInput()}
            {help_text && <p className="text-xs text-muted-foreground">{help_text}</p>}
            {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
    );
}

function normalizeOptions(options: unknown): string[] {
    if (!options) return [];
    if (Array.isArray(options)) {
        return options.map((opt) =>
            typeof opt === 'string' ? opt : String((opt as any)?.value ?? (opt as any)?.label ?? ''),
        ).filter(Boolean);
    }
    if (typeof options === 'object') {
        return Object.values(options as Record<string, unknown>).map((v) => String(v));
    }
    return [];
}

interface CustomFieldsFormProps {
    fields: EventCustomField[];
    values: Record<string, any>;
    onChange: (fieldUuid: string, value: any) => void;
    errors?: Record<string, string>;
}

export function CustomFieldsForm({ fields, values, onChange, errors = {} }: CustomFieldsFormProps) {
    if (!fields || fields.length === 0) {
        return null;
    }

    const ordered = [...fields].sort((a, b) => a.order - b.order);
    return (
        <div className="space-y-4">
            <h4 className="font-medium text-foreground">Additional Information</h4>
            {ordered.map((field) => (
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
