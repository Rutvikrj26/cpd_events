import React, { useState, useRef, useEffect } from "react";
import { Move, ZoomIn, ZoomOut, Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogFooter,
    DialogDescription,
} from "@/components/ui/dialog";
import { updateBadgeTemplate } from "@/api/badges";
import { toast } from "sonner";
import { BadgeTemplate } from "@/api/badges/types";

interface DraggableField {
    id: string;
    label: string;
    x: number;
    y: number;
    fontSize: number;
    color: string;
}

interface BadgeDesignerProps {
    open: boolean;
    onClose: () => void;
    template: BadgeTemplate;
    onSave: () => void;
}

const DEFAULT_FIELDS: DraggableField[] = [
    { id: "attendee_name", label: "Attendee Name", x: 50, y: 50, fontSize: 24, color: "#000000" },
    { id: "event_title", label: "Event Title", x: 50, y: 100, fontSize: 18, color: "#000000" },
    { id: "issued_date", label: "Issue Date", x: 50, y: 150, fontSize: 14, color: "#000000" },
];

export function BadgeDesigner({
    open,
    onClose,
    template,
    onSave,
}: BadgeDesignerProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [fields, setFields] = useState<DraggableField[]>([]);
    const [selectedField, setSelectedField] = useState<string | null>(null);
    const [dragging, setDragging] = useState<string | null>(null);
    const [scale, setScale] = useState(1);
    const [saving, setSaving] = useState(false);

    // Initialize fields
    useEffect(() => {
        if (!template) return;

        const initFields = DEFAULT_FIELDS.map((field) => {
            const saved = template.field_positions?.[field.id] || {};
            return {
                ...field,
                x: saved.x ?? field.x,
                y: saved.y ?? field.y,
                fontSize: saved.fontSize ?? field.fontSize,
                color: saved.color ?? field.color,
            };
        });
        setFields(initFields);
    }, [template, open]);

    const handleMouseDown = (fieldId: string, e: React.MouseEvent) => {
        e.stopPropagation();
        e.preventDefault();
        setDragging(fieldId);
        setSelectedField(fieldId);
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!dragging || !containerRef.current) return;

        const rect = containerRef.current.getBoundingClientRect();
        // Calculate position relative to image
        // Scale is handled visually, but logical coords should be relative to unscaled image?
        // Actually simplest is: logical coords = pixels on original image.
        // Screen coords = logical * scale.

        const x = (e.clientX - rect.left) / scale;
        const y = (e.clientY - rect.top) / scale;

        setFields((prev) =>
            prev.map((f) =>
                f.id === dragging
                    ? { ...f, x: Math.max(0, x), y: Math.max(0, y) }
                    : f
            )
        );
    };

    const handleMouseUp = () => {
        setDragging(null);
    };

    const updateFieldProperty = (fieldId: string, prop: keyof DraggableField, value: any) => {
        setFields((prev) =>
            prev.map((f) => (f.id === fieldId ? { ...f, [prop]: value } : f))
        );
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            const positions: Record<string, any> = {};
            fields.forEach(f => {
                positions[f.id] = {
                    x: Math.round(f.x),
                    y: Math.round(f.y),
                    fontSize: f.fontSize,
                    color: f.color
                };
            });

            await updateBadgeTemplate(template.uuid, { field_positions: positions });
            onSave();
            toast.success("Badge design saved!");
            onClose();
        } catch (error: any) {
            toast.error("Failed to save design");
        } finally {
            setSaving(false);
        }
    };

    const selectedFieldData = fields.find((f) => f.id === selectedField);

    return (
        <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="max-w-6xl h-[90vh] flex flex-col p-0 gap-0">
                <DialogHeader className="px-6 py-4 border-b">
                    <DialogTitle className="flex items-center gap-2">
                        <Move className="h-5 w-5" />
                        Badge Designer
                    </DialogTitle>
                    <DialogDescription>
                        Drag fields to position them on your badge.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-1 overflow-hidden">
                    {/* Canvas Area */}
                    <div className="flex-1 bg-muted overflow-auto flex justify-center p-8 relative">
                        <div
                            ref={containerRef}
                            className="relative shadow-lg select-none bg-white"
                            style={{
                                width: template.width_px * scale,
                                height: template.height_px * scale,
                            }}
                            onMouseMove={handleMouseMove}
                            onMouseUp={handleMouseUp}
                            onMouseLeave={handleMouseUp}
                        >
                            {template.start_image ? (
                                <img
                                    src={template.start_image}
                                    alt="Badge Template"
                                    className="w-full h-full object-contain pointer-events-none"
                                />
                            ) : (
                                <div className="flex items-center justify-center h-full w-full text-gray-400 bg-card border-2 border-dashed">
                                    No Image Uploaded
                                </div>
                            )}

                            {/* Overlays */}
                            {fields.map((field) => (
                                <div
                                    key={field.id}
                                    className={`absolute px-2 py-1 rounded cursor-move whitespace-nowrap z-50 ${selectedField === field.id
                                            ? "ring-2 ring-blue-500 bg-blue-100/90 text-blue-800"
                                            : "bg-yellow-100/50 hover:bg-yellow-200/90 text-yellow-900"
                                        }`}
                                    style={{
                                        left: field.x * scale,
                                        top: field.y * scale,
                                        fontSize: (field.fontSize * scale) + 'px',
                                        color: field.color,
                                        lineHeight: 1,
                                        fontFamily: "sans-serif",
                                    }}
                                    onMouseDown={(e) => handleMouseDown(field.id, e)}
                                >
                                    {field.label}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Sidebar */}
                    <div className="w-80 border-l bg-gray-50 p-4 space-y-6 overflow-y-auto">
                        <div className="space-y-4">
                            <h3 className="font-semibold text-foreground border-b pb-2">Zoom</h3>
                            <div className="flex items-center gap-2">
                                <Button variant="outline" size="icon" onClick={() => setScale(s => Math.max(0.2, s - 0.1))}>
                                    <ZoomOut className="h-4 w-4" />
                                </Button>
                                <span className="text-sm w-16 text-center">{Math.round(scale * 100)}%</span>
                                <Button variant="outline" size="icon" onClick={() => setScale(s => Math.min(2.0, s + 0.1))}>
                                    <ZoomIn className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>

                        <div className="space-y-4">
                            <h3 className="font-semibold text-foreground border-b pb-2">Selected Field</h3>
                            {selectedFieldData ? (
                                <div className="space-y-4">
                                    <div className="text-sm font-medium text-blue-600 bg-blue-50 p-2 rounded">
                                        {selectedFieldData.label}
                                    </div>

                                    <div className="grid grid-cols-2 gap-3 pb-2">
                                        <div className="space-y-1">
                                            <Label className="text-xs">X (px)</Label>
                                            <Input
                                                type="number"
                                                value={Math.round(selectedFieldData.x)}
                                                onChange={(e) => updateFieldProperty(selectedFieldData.id, "x", parseInt(e.target.value) || 0)}
                                                className="h-8"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-xs">Y (px)</Label>
                                            <Input
                                                type="number"
                                                value={Math.round(selectedFieldData.y)}
                                                onChange={(e) => updateFieldProperty(selectedFieldData.id, "y", parseInt(e.target.value) || 0)}
                                                className="h-8"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <Label className="text-xs">Font Size (px)</Label>
                                        <Input
                                            type="number"
                                            value={selectedFieldData.fontSize}
                                            onChange={(e) => updateFieldProperty(selectedFieldData.id, "fontSize", parseInt(e.target.value) || 12)}
                                            className="h-8"
                                        />
                                    </div>

                                    <div className="space-y-1">
                                        <Label className="text-xs">Color</Label>
                                        <div className="flex gap-2">
                                            <Input
                                                type="color"
                                                value={selectedFieldData.color}
                                                onChange={(e) => updateFieldProperty(selectedFieldData.id, "color", e.target.value)}
                                                className="h-8 w-12 p-1"
                                            />
                                            <Input
                                                value={selectedFieldData.color}
                                                onChange={(e) => updateFieldProperty(selectedFieldData.id, "color", e.target.value)}
                                                className="h-8 flex-1"
                                            />
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground italic py-4">
                                    Select a field to edit properties
                                </p>
                            )}
                        </div>
                    </div>
                </div>

                <DialogFooter className="px-6 py-4 border-t bg-gray-50">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={saving}>
                        {saving ? "Saving..." : "Save Design"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
