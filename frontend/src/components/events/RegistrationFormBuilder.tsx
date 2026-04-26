import { useEffect, useState } from 'react';
import {
    ArrowDown,
    ArrowUp,
    GripVertical,
    Loader2,
    Plus,
    Save,
    Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import {
    createEventCustomField,
    deleteEventCustomField,
    getEventCustomFields,
    reorderEventCustomFields,
    updateEventCustomField,
} from '@/api/events';
import {
    EventCustomField,
    EventCustomFieldInput,
    EventCustomFieldType,
} from '@/api/events/types';
import { Button } from '@/shared/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Switch } from '@/shared/ui/switch';
import { Textarea } from '@/shared/ui/textarea';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/shared/ui/select';
import { ConfirmDialog } from '@/shared/ui/confirm-dialog';
import { CustomFieldInput } from '@/components/registration/CustomFieldInput';

const FIELD_TYPES: { value: EventCustomFieldType; label: string; needsOptions: boolean }[] = [
    { value: 'text', label: 'Single line text', needsOptions: false },
    { value: 'textarea', label: 'Multi-line text', needsOptions: false },
    { value: 'number', label: 'Number', needsOptions: false },
    { value: 'date', label: 'Date', needsOptions: false },
    { value: 'select', label: 'Dropdown (single choice)', needsOptions: true },
    { value: 'multiselect', label: 'Checkboxes (multiple choice)', needsOptions: true },
    { value: 'radio', label: 'Radio buttons (single choice)', needsOptions: true },
    { value: 'checkbox', label: 'Yes / No checkbox', needsOptions: false },
];

function needsOptions(type: EventCustomFieldType) {
    return FIELD_TYPES.find((t) => t.value === type)?.needsOptions ?? false;
}

function isNumeric(type: EventCustomFieldType) {
    return type === 'number';
}

type DraftField = EventCustomField & { _dirty?: boolean; _saving?: boolean };

interface RegistrationFormBuilderProps {
    eventUuid: string;
}

export function RegistrationFormBuilder({ eventUuid }: RegistrationFormBuilderProps) {
    const [fields, setFields] = useState<DraftField[]>([]);
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [pendingDelete, setPendingDelete] = useState<DraftField | null>(null);
    const [newField, setNewField] = useState<EventCustomFieldInput>({
        label: '',
        field_type: 'text',
        required: false,
        placeholder: '',
        help_text: '',
        options: [],
    });

    useEffect(() => {
        let cancelled = false;
        setLoading(true);
        getEventCustomFields(eventUuid)
            .then((data) => {
                if (cancelled) return;
                setFields(data.sort((a, b) => a.order - b.order));
            })
            .catch((err) => {
                console.error(err);
                toast.error('Failed to load registration fields');
            })
            .finally(() => !cancelled && setLoading(false));
        return () => {
            cancelled = true;
        };
    }, [eventUuid]);

    const updateLocal = (uuid: string, patch: Partial<DraftField>) => {
        setFields((prev) =>
            prev.map((f) => (f.uuid === uuid ? { ...f, ...patch, _dirty: true } : f)),
        );
    };

    const handleCreate = async () => {
        if (!newField.label.trim()) {
            toast.error('Label is required');
            return;
        }
        if (needsOptions(newField.field_type) && (!newField.options || newField.options.length === 0)) {
            toast.error('Add at least one option for this field type');
            return;
        }
        setCreating(true);
        try {
            const created = await createEventCustomField(eventUuid, {
                ...newField,
                label: newField.label.trim(),
                options: needsOptions(newField.field_type) ? newField.options : undefined,
                order: fields.length,
            });
            setFields((prev) => [...prev, created]);
            setNewField({
                label: '',
                field_type: 'text',
                required: false,
                placeholder: '',
                help_text: '',
                options: [],
            });
            toast.success('Field added');
        } catch (err) {
            console.error(err);
            toast.error('Failed to add field');
        } finally {
            setCreating(false);
        }
    };

    const handleSave = async (field: DraftField) => {
        setFields((prev) => prev.map((f) => (f.uuid === field.uuid ? { ...f, _saving: true } : f)));
        try {
            const updated = await updateEventCustomField(eventUuid, field.uuid, {
                label: field.label.trim(),
                field_type: field.field_type,
                required: field.required,
                placeholder: field.placeholder ?? '',
                help_text: field.help_text ?? '',
                options: needsOptions(field.field_type) ? field.options ?? [] : [],
                min_value: isNumeric(field.field_type) ? field.min_value ?? null : null,
                max_value: isNumeric(field.field_type) ? field.max_value ?? null : null,
            });
            setFields((prev) => prev.map((f) => (f.uuid === field.uuid ? updated : f)));
            toast.success('Field saved');
        } catch (err) {
            console.error(err);
            toast.error('Failed to save field');
            setFields((prev) =>
                prev.map((f) => (f.uuid === field.uuid ? { ...f, _saving: false } : f)),
            );
        }
    };

    const handleDelete = async (field: DraftField) => {
        try {
            await deleteEventCustomField(eventUuid, field.uuid);
            setFields((prev) => prev.filter((f) => f.uuid !== field.uuid));
            toast.success('Field removed');
        } catch (err) {
            console.error(err);
            toast.error('Failed to delete field');
        } finally {
            setPendingDelete(null);
        }
    };

    const handleMove = async (fieldUuid: string, direction: -1 | 1) => {
        const idx = fields.findIndex((f) => f.uuid === fieldUuid);
        if (idx < 0) return;
        const target = idx + direction;
        if (target < 0 || target >= fields.length) return;
        const next = [...fields];
        const [moved] = next.splice(idx, 1);
        next.splice(target, 0, moved);
        const reOrdered = next.map((f, i) => ({ ...f, order: i }));
        setFields(reOrdered);
        try {
            await reorderEventCustomFields(eventUuid, reOrdered.map((f) => f.uuid));
        } catch (err) {
            console.error(err);
            toast.error('Failed to reorder — reloading');
            getEventCustomFields(eventUuid).then((data) =>
                setFields(data.sort((a, b) => a.order - b.order)),
            );
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading form…
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
            <div className="space-y-4">
                <div>
                    <h3 className="text-lg font-semibold">Registration form</h3>
                    <p className="text-sm text-muted-foreground">
                        Core identity fields (name, email, billing) are always collected. Add custom
                        fields below to gather more from attendees.
                    </p>
                </div>

                {fields.length === 0 && (
                    <Card>
                        <CardContent className="py-8 text-center text-sm text-muted-foreground">
                            No custom fields yet. Add one on the right.
                        </CardContent>
                    </Card>
                )}

                {fields.map((field, idx) => (
                    <Card key={field.uuid}>
                        <CardHeader className="pb-3">
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <GripVertical className="h-4 w-4" />
                                    Field {idx + 1}
                                </div>
                                <div className="flex gap-1">
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        aria-label="Move up"
                                        disabled={idx === 0}
                                        onClick={() => handleMove(field.uuid, -1)}
                                    >
                                        <ArrowUp className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        aria-label="Move down"
                                        disabled={idx === fields.length - 1}
                                        onClick={() => handleMove(field.uuid, 1)}
                                    >
                                        <ArrowDown className="h-4 w-4" />
                                    </Button>
                                    <Button
                                        size="icon"
                                        variant="ghost"
                                        aria-label="Delete field"
                                        onClick={() => setPendingDelete(field)}
                                    >
                                        <Trash2 className="h-4 w-4" />
                                    </Button>
                                </div>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <Label>Label</Label>
                                    <Input
                                        value={field.label}
                                        onChange={(e) =>
                                            updateLocal(field.uuid, { label: e.target.value })
                                        }
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label>Type</Label>
                                    <Select
                                        value={field.field_type}
                                        onValueChange={(val) =>
                                            updateLocal(field.uuid, {
                                                field_type: val as EventCustomFieldType,
                                                options: needsOptions(val as EventCustomFieldType)
                                                    ? field.options ?? []
                                                    : [],
                                            })
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {FIELD_TYPES.map((t) => (
                                                <SelectItem key={t.value} value={t.value}>
                                                    {t.label}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <Label>Placeholder</Label>
                                    <Input
                                        value={field.placeholder ?? ''}
                                        onChange={(e) =>
                                            updateLocal(field.uuid, { placeholder: e.target.value })
                                        }
                                    />
                                </div>
                                <div className="space-y-1">
                                    <Label>Help text</Label>
                                    <Input
                                        value={field.help_text ?? ''}
                                        onChange={(e) =>
                                            updateLocal(field.uuid, { help_text: e.target.value })
                                        }
                                    />
                                </div>
                            </div>

                            {needsOptions(field.field_type) && (
                                <div className="space-y-1">
                                    <Label>Options (one per line)</Label>
                                    <Textarea
                                        value={(field.options ?? []).join('\n')}
                                        onChange={(e) =>
                                            updateLocal(field.uuid, {
                                                options: e.target.value
                                                    .split('\n')
                                                    .map((x) => x.trim())
                                                    .filter(Boolean),
                                            })
                                        }
                                        rows={3}
                                    />
                                </div>
                            )}

                            {isNumeric(field.field_type) && (
                                <div className="grid grid-cols-2 gap-3">
                                    <div className="space-y-1">
                                        <Label>Min value</Label>
                                        <Input
                                            type="number"
                                            value={field.min_value ?? ''}
                                            onChange={(e) =>
                                                updateLocal(field.uuid, {
                                                    min_value:
                                                        e.target.value === ''
                                                            ? null
                                                            : Number(e.target.value),
                                                })
                                            }
                                        />
                                    </div>
                                    <div className="space-y-1">
                                        <Label>Max value</Label>
                                        <Input
                                            type="number"
                                            value={field.max_value ?? ''}
                                            onChange={(e) =>
                                                updateLocal(field.uuid, {
                                                    max_value:
                                                        e.target.value === ''
                                                            ? null
                                                            : Number(e.target.value),
                                                })
                                            }
                                        />
                                    </div>
                                </div>
                            )}

                            <div className="flex items-center justify-between pt-2">
                                <div className="flex items-center gap-2">
                                    <Switch
                                        id={`req-${field.uuid}`}
                                        checked={field.required}
                                        onCheckedChange={(checked) =>
                                            updateLocal(field.uuid, { required: checked })
                                        }
                                    />
                                    <Label htmlFor={`req-${field.uuid}`} className="cursor-pointer">
                                        Mandatory
                                    </Label>
                                </div>
                                <Button
                                    size="sm"
                                    onClick={() => handleSave(field)}
                                    disabled={!field._dirty || field._saving}
                                >
                                    {field._saving ? (
                                        <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                                    ) : (
                                        <Save className="h-4 w-4 mr-1" />
                                    )}
                                    Save
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <div className="space-y-4">
                <Card>
                    <CardHeader>
                        <CardTitle className="text-base">Add a new field</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="space-y-1">
                            <Label>Label</Label>
                            <Input
                                value={newField.label}
                                placeholder="e.g., Medical license number"
                                onChange={(e) =>
                                    setNewField({ ...newField, label: e.target.value })
                                }
                            />
                        </div>
                        <div className="space-y-1">
                            <Label>Type</Label>
                            <Select
                                value={newField.field_type}
                                onValueChange={(val) =>
                                    setNewField({
                                        ...newField,
                                        field_type: val as EventCustomFieldType,
                                        options: needsOptions(val as EventCustomFieldType)
                                            ? newField.options ?? []
                                            : [],
                                    })
                                }
                            >
                                <SelectTrigger>
                                    <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                    {FIELD_TYPES.map((t) => (
                                        <SelectItem key={t.value} value={t.value}>
                                            {t.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                        </div>
                        {needsOptions(newField.field_type) && (
                            <div className="space-y-1">
                                <Label>Options (one per line)</Label>
                                <Textarea
                                    value={(newField.options ?? []).join('\n')}
                                    onChange={(e) =>
                                        setNewField({
                                            ...newField,
                                            options: e.target.value
                                                .split('\n')
                                                .map((x) => x.trim())
                                                .filter(Boolean),
                                        })
                                    }
                                    rows={3}
                                />
                            </div>
                        )}
                        <div className="flex items-center gap-2">
                            <Switch
                                id="new-required"
                                checked={!!newField.required}
                                onCheckedChange={(checked) =>
                                    setNewField({ ...newField, required: checked })
                                }
                            />
                            <Label htmlFor="new-required" className="cursor-pointer">
                                Mandatory
                            </Label>
                        </div>
                        <Button
                            className="w-full"
                            onClick={handleCreate}
                            disabled={creating || !newField.label.trim()}
                        >
                            {creating ? (
                                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                            ) : (
                                <Plus className="h-4 w-4 mr-1" />
                            )}
                            Add field
                        </Button>
                    </CardContent>
                </Card>

                {fields.length > 0 && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="text-base">Live preview</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                            {fields.map((field) => (
                                <CustomFieldInput
                                    key={field.uuid}
                                    field={field}
                                    value={undefined}
                                    onChange={() => {}}
                                />
                            ))}
                        </CardContent>
                    </Card>
                )}
            </div>

            <ConfirmDialog
                open={!!pendingDelete}
                onOpenChange={(open) => !open && setPendingDelete(null)}
                title="Remove this field?"
                description={
                    pendingDelete
                        ? `"${pendingDelete.label}" will be removed from the registration form. Existing responses are preserved but no longer visible on this form.`
                        : ''
                }
                confirmLabel="Remove"
                variant="destructive"
                onConfirm={async () => {
                    if (pendingDelete) await handleDelete(pendingDelete);
                }}
            />
        </div>
    );
}
