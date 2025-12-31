import React, { useState, useRef } from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { LocationAutocomplete } from '@/components/ui/LocationAutocomplete';
import { MapPin, Upload, Image as ImageIcon, X } from 'lucide-react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';

export const StepDetails = () => {
    const { formData, updateFormData } = useEventWizard();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isImageRemoved, setIsImageRemoved] = useState(false);

    // Check if event has online or in-person component
    const hasOnlineComponent = formData.format === 'online' || formData.format === 'hybrid';
    const hasInPersonComponent = formData.format === 'in-person' || formData.format === 'hybrid';

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            // Validate file type
            const validTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
            if (!validTypes.includes(file.type)) {
                alert('Please select a valid image file (JPEG, PNG, GIF, or WebP)');
                return;
            }

            // Validate file size (5MB max)
            if (file.size > 5 * 1024 * 1024) {
                alert('File too large. Maximum size is 5MB.');
                return;
            }

            setSelectedFile(file);
            setIsImageRemoved(false);

            // Create preview URL
            const url = URL.createObjectURL(file);
            setPreviewUrl(url);

            // Store file reference in form data (will be uploaded on submit)
            // Also reset removal flag since we are adding a new file
            updateFormData({ _imageFile: file, _isImageRemoved: false });
        }
    };

    const clearImage = () => {
        setSelectedFile(null);
        setPreviewUrl(null);
        setIsImageRemoved(true);
        // Set removal flag so Wizard knows to delete on server
        updateFormData({ _imageFile: undefined, _isImageRemoved: true });
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    // Determine the preview source: 
    // 1. Local preview (newly selected)
    // 2. Existing featured_image_url (unless explicitly removed)
    const preview = previewUrl || (!isImageRemoved ? formData.featured_image_url : null) || null;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Event Details</h2>
                <p className="text-sm text-muted-foreground">Provide a comprehensive description for your attendees.</p>
            </div>

            <div className="space-y-2">
                <Label>Description</Label>
                <ReactQuill
                    theme="snow"
                    placeholder="What will attendees learn? Who are the speakers?"
                    value={formData.description || ''}
                    onChange={(value) => updateFormData({ description: value })}
                    className="mb-4"
                />
            </div>

            {/* Location Section - Only shown for in-person/hybrid events */}
            {hasInPersonComponent && (
                <div className="space-y-2 p-4 bg-amber-50/50 rounded-lg border border-amber-100">
                    <Label className="flex items-center gap-2">
                        <MapPin className="h-4 w-4 text-amber-600" />
                        Venue / Location
                    </Label>
                    <LocationAutocomplete
                        value={formData.location || ''}
                        onChange={(value) => updateFormData({ location: value })}
                        placeholder="Search for a venue or enter address..."
                    />
                    <p className="text-xs text-muted-foreground">
                        This address will be shared with registered attendees.
                    </p>
                </div>
            )}



            {/* Cover Image Section */}
            <div className="space-y-3">
                <Label className="flex items-center gap-2">
                    <ImageIcon className="h-4 w-4" />
                    Cover Image
                </Label>

                <div className="space-y-3">
                    <input
                        ref={fileInputRef}
                        type="file"
                        accept="image/jpeg,image/png,image/gif,image/webp"
                        onChange={handleFileSelect}
                        onClick={(e) => { (e.target as HTMLInputElement).value = ''; }}
                        className="hidden"
                    />

                    {!selectedFile && !preview ? (
                        <div
                            onClick={() => fileInputRef.current?.click()}
                            className="border-2 border-dashed border-border rounded-lg p-8 text-center bg-muted/30 hover:bg-muted/50 transition-colors cursor-pointer"
                        >
                            <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
                            <p className="text-sm text-muted-foreground">Click to upload or drag and drop</p>
                            <p className="text-xs text-muted-foreground mt-1">JPEG, PNG, GIF, WebP • Max 5MB</p>
                        </div>
                    ) : (
                        <div className="relative mt-3 aspect-video max-w-sm overflow-hidden rounded-lg border border-border bg-muted">
                            <img
                                src={preview!}
                                alt="Event cover preview"
                                className="h-full w-full object-cover"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).style.display = 'none';
                                }}
                            />
                            <div className="absolute top-2 right-2 flex gap-2">
                                <Button
                                    type="button"
                                    variant="default"
                                    size="sm"
                                    onClick={() => fileInputRef.current?.click()}
                                >
                                    Change
                                </Button>
                                <Button
                                    type="button"
                                    variant="destructive"
                                    size="sm"
                                    onClick={clearImage}
                                >
                                    <X className="h-4 w-4" />
                                </Button>
                            </div>
                        </div>
                    )}
                    {selectedFile && (
                        <p className="text-xs text-green-600 mt-1 flex items-center gap-1">
                            <ImageIcon className="h-3 w-3" />
                            Selected: {selectedFile.name}
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};
