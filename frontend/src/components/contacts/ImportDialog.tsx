import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, Upload, FileText, AlertCircle, CheckCircle } from 'lucide-react';
import { toast } from 'sonner';
import { bulkImportContacts, BulkImportParams } from '@/api/contacts';

interface ImportDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    onSuccess?: () => void;
}

interface ParsedContact {
    email: string;
    full_name: string;
    professional_title?: string;
    organization_name?: string;
    phone?: string;
    notes?: string;
}

export function ImportDialog({
    open,
    onOpenChange,
    onSuccess
}: ImportDialogProps) {
    const [loading, setLoading] = useState(false);
    const [file, setFile] = useState<File | null>(null);
    const [parsedContacts, setParsedContacts] = useState<ParsedContact[]>([]);
    const [parseError, setParseError] = useState<string | null>(null);

    const resetState = () => {
        setFile(null);
        setParsedContacts([]);
        setParseError(null);
    };

    React.useEffect(() => {
        if (open) {
            resetState();
        }
    }, [open]);

    const parseCSV = (text: string): ParsedContact[] => {
        const lines = text.trim().split('\n');
        if (lines.length < 2) {
            throw new Error('CSV must have at least a header row and one data row');
        }

        // Parse header
        const header = lines[0].split(',').map(h => h.trim().toLowerCase().replace(/['"]/g, ''));

        // Find column indices
        const emailIdx = header.findIndex(h => h.includes('email'));
        const nameIdx = header.findIndex(h => h.includes('name') && !h.includes('organization'));
        const titleIdx = header.findIndex(h => h.includes('title') || h.includes('professional'));
        const orgIdx = header.findIndex(h => h.includes('organization') || h.includes('company'));
        const phoneIdx = header.findIndex(h => h.includes('phone'));
        const notesIdx = header.findIndex(h => h.includes('notes'));

        if (emailIdx === -1) {
            throw new Error('CSV must have an "email" column');
        }

        const contacts: ParsedContact[] = [];
        for (let i = 1; i < lines.length; i++) {
            const values = lines[i].split(',').map(v => v.trim().replace(/^["']|["']$/g, ''));
            const email = values[emailIdx]?.trim();

            if (!email) continue; // Skip empty rows

            contacts.push({
                email,
                full_name: nameIdx >= 0 ? values[nameIdx] || email : email,
                professional_title: titleIdx >= 0 ? values[titleIdx] : undefined,
                organization_name: orgIdx >= 0 ? values[orgIdx] : undefined,
                phone: phoneIdx >= 0 ? values[phoneIdx] : undefined,
                notes: notesIdx >= 0 ? values[notesIdx] : undefined,
            });
        }

        return contacts;
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const selectedFile = e.target.files?.[0];
        if (!selectedFile) return;

        setFile(selectedFile);
        setParseError(null);
        setParsedContacts([]);

        try {
            const text = await selectedFile.text();
            const contacts = parseCSV(text);
            setParsedContacts(contacts);
        } catch (error) {
            setParseError(error instanceof Error ? error.message : 'Failed to parse CSV');
        }
    };

    const handleImport = async () => {
        if (parsedContacts.length === 0) return;

        setLoading(true);
        try {
            const data: BulkImportParams = { contacts: parsedContacts };
            const result = await bulkImportContacts(data);

            toast.success(`Imported ${result.created} contacts`, {
                description: result.skipped > 0 ? `${result.skipped} duplicates skipped` : undefined
            });

            onSuccess?.();
            onOpenChange(false);
        } catch (error) {
            console.error('Failed to import contacts:', error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="max-w-md">
                <DialogHeader>
                    <DialogTitle>Import Contacts</DialogTitle>
                    <DialogDescription>
                        Upload a CSV file with contacts. Required column: email. Optional: name, title, organization, phone, notes.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    {/* File upload */}
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

                    {/* Parse result */}
                    {parseError && (
                        <div className="flex items-start gap-2 p-3 bg-destructive/10 text-destructive rounded-lg text-sm">
                            <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                            <span>{parseError}</span>
                        </div>
                    )}

                    {parsedContacts.length > 0 && (
                        <div className="flex items-start gap-2 p-3 bg-primary/10 text-primary rounded-lg text-sm">
                            <CheckCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                            <span>Found {parsedContacts.length} contacts ready to import</span>
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
                        Cancel
                    </Button>
                    <Button
                        onClick={handleImport}
                        disabled={loading || parsedContacts.length === 0}
                    >
                        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Import {parsedContacts.length > 0 && `(${parsedContacts.length})`}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
