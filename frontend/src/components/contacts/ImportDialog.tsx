import { useEffect, useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, Download, FileText, Loader2, Upload } from 'lucide-react';
import { toast } from 'sonner';
import {
    downloadContactsImportTemplate,
    importContactsCsv,
    ImportCsvResult,
} from '@/api/contacts';

interface ImportDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: () => void;
}

export function ImportDialog({ open, onOpenChange, onSuccess }: ImportDialogProps) {
    const [loading, setLoading] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [result, setResult] = useState<ImportCsvResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            setFile(null);
            setResult(null);
            setError(null);
        }
    }, [open]);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] ?? null;
        setFile(selected);
        setResult(null);
        setError(null);
    };

    const handleDownloadTemplate = async () => {
        try {
            await downloadContactsImportTemplate();
        } catch {
            toast.error('Failed to download template');
        }
    };

    const handleUpload = async () => {
        if (!file) return;
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const res = await importContactsCsv(file);
            setResult(res);
            if (res.created > 0) {
                toast.success(
                    `Imported ${res.created} contact${res.created === 1 ? '' : 's'}`,
                    {
                        description:
                            res.skipped > 0 ? `${res.skipped} duplicate(s) skipped` : undefined,
                    },
                );
            }
            if (res.errors.length === 0 && res.created > 0) {
                onSuccess?.();
                setTimeout(() => onOpenChange(false), 400);
            } else if (res.created > 0) {
                onSuccess?.();
            }
        } catch (err: any) {
            setError(
                err?.response?.data?.error?.message ??
                    err?.response?.data?.detail ??
                    err?.message ??
                    'Failed to import. Check the file format against the template.',
            );
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-lg">
                <DialogHeader>
                    <DialogTitle>Import Contacts</DialogTitle>
                    <DialogDescription>
                        Upload a CSV using the required columns: <code>email</code>,{' '}
                        <code>full_name</code>. Optional: professional_title, organization_name,
                        phone, notes. Download the template to see the expected format.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-2">
                    <div className="flex items-center justify-end">
                        <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={handleDownloadTemplate}
                        >
                            <Download className="h-4 w-4 mr-2" />
                            Download template
                        </Button>
                    </div>

                    <div className="border-2 border-dashed rounded-lg p-6 text-center hover:border-primary/50 transition-colors">
                        <input
                            type="file"
                            accept=".csv"
                            onChange={handleFileChange}
                            className="hidden"
                            id="csv-upload"
                            disabled={loading}
                        />
                        <label htmlFor="csv-upload" className="cursor-pointer">
                            {file ? (
                                <div className="flex items-center justify-center gap-2 text-sm">
                                    <FileText className="h-5 w-5 text-primary" />
                                    <span className="font-medium">{file.name}</span>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                                    <p className="text-sm text-muted-foreground">
                                        Click to select CSV file
                                    </p>
                                </div>
                            )}
                        </label>
                    </div>

                    {error && (
                        <div className="flex items-start gap-2 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
                            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                            <span>{error}</span>
                        </div>
                    )}

                    {result && (
                        <div className="space-y-2">
                            <div className="flex items-start gap-2 p-3 bg-primary/10 text-primary rounded-lg text-sm">
                                <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
                                <span>
                                    Imported {result.created} · skipped {result.skipped} ·
                                    errors {result.errors.length}
                                </span>
                            </div>
                            {result.errors.length > 0 && (
                                <div className="border rounded-lg max-h-48 overflow-auto text-xs">
                                    <table className="min-w-full">
                                        <thead className="bg-muted sticky top-0">
                                            <tr>
                                                <th className="text-left px-3 py-2">Row</th>
                                                <th className="text-left px-3 py-2">Email</th>
                                                <th className="text-left px-3 py-2">Error</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {result.errors.map((err, i) => (
                                                <tr key={i} className="border-t">
                                                    <td className="px-3 py-1.5 font-mono">
                                                        {err.row}
                                                    </td>
                                                    <td className="px-3 py-1.5">
                                                        {err.email || '—'}
                                                    </td>
                                                    <td className="px-3 py-1.5 text-destructive">
                                                        {err.error}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <DialogFooter>
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => onOpenChange(false)}
                        disabled={loading}
                    >
                        Close
                    </Button>
                    <Button onClick={handleUpload} disabled={loading || !file}>
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Upload & Import
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
