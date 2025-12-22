import React, { useState, useRef, useEffect } from "react";
import { Move, MousePointer, Download, RefreshCw, ZoomIn, ZoomOut } from "lucide-react";
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
import { generateTemplatePreview, saveFieldPositions, FieldPositions, FieldPosition } from "@/api/certificates";
import { toast } from "sonner";
import { Document, Page, pdfjs } from 'react-pdf';

// Initialize PDF worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface DraggableField {
    id: string;
    label: string;
    x: number;
    y: number;
    fontSize: number;
}

interface FieldPositionEditorProps {
    open: boolean;
    onClose: () => void;
    templateUuid: string;
    templateFileUrl: string | null;
    initialPositions: FieldPositions;
    onSave: (positions: FieldPositions) => void;
}

const DEFAULT_FIELDS: DraggableField[] = [
    // These IDs must match keys from backend's Certificate.build_certificate_data()
    { id: "attendee_name", label: "Attendee Name", x: 100, y: 100, fontSize: 24 },
    { id: "event_title", label: "Event Title", x: 100, y: 150, fontSize: 20 },
    { id: "event_date", label: "Event Date", x: 100, y: 200, fontSize: 16 },
    { id: "cpd_credits", label: "CPD Credits", x: 100, y: 250, fontSize: 16 },
    { id: "organizer_name", label: "Organizer", x: 100, y: 300, fontSize: 14 },
    { id: "issued_date", label: "Issue Date", x: 100, y: 350, fontSize: 12 },
];

export function FieldPositionEditor({
    open,
    onClose,
    templateUuid,
    templateFileUrl,
    initialPositions,
    onSave,
}: FieldPositionEditorProps) {
    const wrapperRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [fields, setFields] = useState<DraggableField[]>([]);
    const [selectedField, setSelectedField] = useState<string | null>(null);
    const [dragging, setDragging] = useState<string | null>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    // PDF State
    const [numPages, setNumPages] = useState<number>(0);
    const [pageNumber, setPageNumber] = useState(1);
    const [pdfDimensions, setPdfDimensions] = useState<{ width: number; height: number } | null>(null);
    const [scale, setScale] = useState(1);

    // Initialize fields from initialPositions
    // Note: initialPositions are stored in PDF Coordinates (points)
    // We need to wait until we know the scale to convert them to Screen Coordinates (pixels)
    useEffect(() => {
        if (!pdfDimensions || !scale) return;

        const initFields = DEFAULT_FIELDS.map((field) => {
            const saved = initialPositions?.[field.id] || field; // Use field defaults if not saved
            return {
                ...field,
                // Convert PDF Point -> Screen Pixel
                x: saved.x * scale,
                y: saved.y * scale,
                fontSize: saved.fontSize,
            };
        });
        // Only set fields if we haven't initialized or if scale changed significantly (drag compensation handled elsewhere)
        // Actually, on scale change we must re-calculate field positions
        setFields(initFields);
    }, [initialPositions, pdfDimensions, scale, open]);

    function onDocumentLoadSuccess({ numPages }: { numPages: number }) {
        setNumPages(numPages);
    }

    function onPageLoadSuccess(page: any) {
        const { width, height, originalWidth, originalHeight } = page;
        // Check if dimensions changed to avoid unnecessary re-renders/loops
        if (pdfDimensions?.width === originalWidth && pdfDimensions?.height === originalHeight) {
            return;
        }

        // originalWidth/Height are in points (72 DPI) usually
        setPdfDimensions({ width: originalWidth, height: originalHeight });

        // Calculate scale to fit wrapper ONCE when dimensions are first loaded
        // We use wrapperRef which is stable, not containerRef which changes size
        if (wrapperRef.current) {
            const wrapperW = wrapperRef.current.clientWidth - 64; // -64 for padding (p-8 = 32px * 2)
            const newScale = Math.min(1.0, Math.max(0.2, wrapperW / originalWidth));
            setScale(newScale);
        }
    }

    const handleMouseDown = (fieldId: string, e: React.MouseEvent) => {
        e.stopPropagation(); // Stop propagation to prevent drag issues
        e.preventDefault();
        setDragging(fieldId);
        setSelectedField(fieldId);
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!dragging || !containerRef.current) return;

        const rect = containerRef.current.getBoundingClientRect();
        // Calculate position relative to container, ensuring it stays within bounds
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Constraint within container
        const constrainedX = Math.max(0, Math.min(x, rect.width - 50));
        const constrainedY = Math.max(0, Math.min(y, rect.height - 20));

        setFields((prev) =>
            prev.map((f) =>
                f.id === dragging
                    ? { ...f, x: constrainedX, y: constrainedY }
                    : f
            )
        );
    };

    const handleMouseUp = () => {
        setDragging(null);
    };

    const updateFieldProperty = (fieldId: string, prop: keyof DraggableField, value: number) => {
        setFields((prev) =>
            prev.map((f) => (f.id === fieldId ? { ...f, [prop]: value } : f))
        );
    };

    const getFieldPositions = (): FieldPositions => {
        const positions: FieldPositions = {};
        fields.forEach((f) => {
            // Convert Screen Pixel -> PDF Point
            // x_pdf = x_screen / scale
            positions[f.id] = {
                x: f.x / scale,
                y: f.y / scale,
                fontSize: f.fontSize
            };
        });
        return positions;
    };

    const handleGeneratePreview = async () => {
        setLoading(true);
        try {
            const result = await generateTemplatePreview(templateUuid, getFieldPositions());
            setPreviewUrl(result.preview_url);
            toast.success("Preview generated!");
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to generate preview");
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        try {
            await saveFieldPositions(templateUuid, getFieldPositions());
            onSave(getFieldPositions());
            toast.success("Field positions saved!");
            onClose();
        } catch (error: any) {
            toast.error(error?.response?.data?.detail || "Failed to save positions");
        } finally {
            setSaving(false);
        }
    };

    const selectedFieldData = fields.find((f) => f.id === selectedField);

    // Fix for local media URLs
    const pdfUrl = templateFileUrl?.startsWith('/media/')
        ? `http://localhost:8000${templateFileUrl}`
        : templateFileUrl;

    return (
        <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
            <DialogContent className="max-w-6xl h-[90vh] flex flex-col p-0 gap-0">
                <DialogHeader className="px-6 py-4 border-b">
                    <DialogTitle className="flex items-center gap-2">
                        <Move className="h-5 w-5" />
                        Position Certificate Fields
                    </DialogTitle>
                    <DialogDescription>
                        Drag fields to position them. The view is scaled, but positions are saved accurately for PDF generation.
                    </DialogDescription>
                </DialogHeader>

                <div className="flex flex-1 overflow-hidden">
                    {/* PDF Preview Area */}
                    <div ref={wrapperRef} className="flex-1 bg-muted overflow-auto flex justify-center p-8 relative">
                        <div
                            ref={containerRef}
                            className="relative shadow-lg select-none"
                            style={{
                                width: pdfDimensions ? pdfDimensions.width * scale : '100%',
                                height: pdfDimensions ? pdfDimensions.height * scale : 'auto'
                            }}
                            onMouseMove={handleMouseMove}
                            onMouseUp={handleMouseUp}
                            onMouseLeave={handleMouseUp}
                        >
                            {pdfUrl ? (
                                <Document
                                    file={pdfUrl}
                                    onLoadSuccess={onDocumentLoadSuccess}
                                    loading={
                                        <div className="flex items-center justify-center h-96 w-full">
                                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                                        </div>
                                    }
                                    error={
                                        <div className="flex items-center justify-center h-96 w-full text-red-500">
                                            Failed to load PDF. Please check if the file is valid.
                                        </div>
                                    }
                                >
                                    <Page
                                        pageNumber={pageNumber}
                                        scale={scale}
                                        onLoadSuccess={onPageLoadSuccess}
                                        renderTextLayer={false}
                                        renderAnnotationLayer={false}
                                    />
                                </Document>
                            ) : (
                                <div className="flex items-center justify-center h-96 w-full text-gray-400 bg-card border-2 border-dashed">
                                    No PDF uploaded
                                </div>
                            )}

                            {/* Overlays */}
                            {fields.map((field) => (
                                <div
                                    key={field.id}
                                    className={`absolute px-2 py-1 rounded cursor-move select-none whitespace-nowrap z-50 ${selectedField === field.id
                                        ? "ring-2 ring-blue-500 bg-blue-100/90 text-blue-800"
                                        : "bg-yellow-100/80 hover:bg-yellow-200/90 text-yellow-900"
                                        } ${dragging === field.id ? "opacity-75 shadow-xl scale-105" : "shadow-sm"}`}
                                    style={{
                                        left: field.x,
                                        top: field.y,
                                        fontSize: Math.max(10, field.fontSize * scale), // Scale font size for visual preview
                                        fontFamily: "Helvetica, sans-serif",
                                        transform: 'translate(-50%, -50%)' // Center anchor
                                    }}
                                    onMouseDown={(e) => handleMouseDown(field.id, e)}
                                >
                                    {field.label}
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Properties Sidebar */}
                    <div className="w-80 border-l bg-gray-50 p-4 space-y-6 overflow-y-auto">
                        <div className="space-y-4">
                            <h3 className="font-semibold text-foreground border-b pb-2">Zoom & Layout</h3>
                            <div className="flex items-center gap-2">
                                <Button variant="outline" size="icon" onClick={() => setScale(s => Math.max(0.2, s - 0.1))}>
                                    <ZoomOut className="h-4 w-4" />
                                </Button>
                                <span className="text-sm w-16 text-center">{Math.round(scale * 100)}%</span>
                                <Button variant="outline" size="icon" onClick={() => setScale(s => Math.min(2.0, s + 0.1))}>
                                    <ZoomIn className="h-4 w-4" />
                                </Button>
                            </div>
                            {pdfDimensions && (
                                <p className="text-xs text-muted-foreground">
                                    Original Size: {Math.round(pdfDimensions.width)} x {Math.round(pdfDimensions.height)} pt
                                </p>
                            )}
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
                                            <Label className="text-xs">X (pt)</Label>
                                            <Input
                                                type="number"
                                                value={Math.round(selectedFieldData.x / scale)}
                                                onChange={(e) => updateFieldProperty(selectedFieldData.id, "x", (parseInt(e.target.value) || 0) * scale)}
                                                className="h-8"
                                            />
                                        </div>
                                        <div className="space-y-1">
                                            <Label className="text-xs">Y (pt)</Label>
                                            <Input
                                                type="number"
                                                value={Math.round(selectedFieldData.y / scale)}
                                                onChange={(e) => updateFieldProperty(selectedFieldData.id, "y", (parseInt(e.target.value) || 0) * scale)}
                                                className="h-8"
                                            />
                                        </div>
                                    </div>

                                    <div className="space-y-1">
                                        <Label className="text-xs">Font Size (pt)</Label>
                                        <Input
                                            type="number"
                                            value={selectedFieldData.fontSize}
                                            onChange={(e) => updateFieldProperty(selectedFieldData.id, "fontSize", parseInt(e.target.value) || 12)}
                                            className="h-8"
                                        />
                                    </div>
                                </div>
                            ) : (
                                <p className="text-sm text-muted-foreground italic py-4">
                                    Select a field on the certificate to edit its properties
                                </p>
                            )}
                        </div>

                        <div className="flex-1"></div>

                        <div className="space-y-3 pt-4 border-t">
                            <Button
                                variant="outline"
                                className="w-full"
                                onClick={handleGeneratePreview}
                                disabled={loading || !templateFileUrl}
                            >
                                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                                Generate Preview
                            </Button>

                            {previewUrl && (
                                <a href={previewUrl.startsWith('/media/') ? `http://localhost:8000${previewUrl}` : previewUrl} target="_blank" rel="noopener noreferrer" className="block">
                                    <Button variant="outline" className="w-full text-blue-600 border-blue-200 hover:bg-blue-50">
                                        <Download className="mr-2 h-4 w-4" />
                                        Download Preview
                                    </Button>
                                </a>
                            )}
                        </div>
                    </div>
                </div>

                <DialogFooter className="px-6 py-4 border-t bg-gray-50">
                    <Button variant="outline" onClick={onClose}>
                        Cancel
                    </Button>
                    <Button onClick={handleSave} disabled={saving}>
                        {saving ? "Saving..." : "Save Positions"}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
