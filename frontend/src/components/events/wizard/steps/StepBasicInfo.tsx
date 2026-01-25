import React from 'react';
import { useEventWizard } from '../EventWizardContext';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import { Building2, User } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export const StepBasicInfo = () => {
    const { formData, updateFormData, isEditMode } = useEventWizard();
    // Organization context removed - organization features disabled
    const organizations: any[] = [];
    const currentOrg = null;

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-foreground">Basic Information</h2>
                <p className="text-sm text-muted-foreground">Let's start with the core details of your event.</p>
            </div>

            <div className="grid gap-6">
                <div className="space-y-2">
                    <Label htmlFor="title">Event Title</Label>
                    <Input
                        id="title"
                        placeholder="e.g. Annual Leadership Summit 2024"
                        value={formData.title || ''}
                        onChange={(e) => updateFormData({ title: e.target.value })}
                        className="text-lg py-6"
                    />
                </div>

                {/* Organization Selector */}
                {organizations.length > 0 && (
                    <div className="space-y-2">
                        <Label>Create Event For</Label>
                        <Select
                            value={formData.organization || ''}
                            onValueChange={(value) => updateFormData({ organization: value || undefined })}
                        >
                            <SelectTrigger className="h-11">
                                <SelectValue placeholder="Personal Account">
                                    {formData.organization ? (
                                        <div className="flex items-center gap-2">
                                            <Building2 className="h-4 w-4 text-primary" />
                                            <span>
                                                {organizations.find(org => org.uuid === formData.organization)?.name || 'Organization'}
                                            </span>
                                            <Badge variant="secondary" className="ml-auto text-xs">
                                                Organization
                                            </Badge>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-2">
                                            <User className="h-4 w-4 text-muted-foreground" />
                                            <span>Personal Account</span>
                                        </div>
                                    )}
                                </SelectValue>
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="">
                                    <div className="flex items-center gap-2">
                                        <User className="h-4 w-4" />
                                        <span>Personal Account</span>
                                    </div>
                                </SelectItem>
                                {organizations.map((org) => (
                                    <SelectItem key={org.uuid} value={org.uuid}>
                                        <div className="flex items-center gap-2">
                                            <Building2 className="h-4 w-4" />
                                            <span>{org.name}</span>
                                            {org.user_role && (
                                                <Badge variant="outline" className="ml-auto text-xs capitalize">
                                                    {org.user_role}
                                                </Badge>
                                            )}
                                        </div>
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        {formData.organization && (
                            <p className="text-xs text-muted-foreground flex items-center gap-1">
                                <Building2 className="h-3 w-3" />
                                Creating as {organizations.find(org => org.uuid === formData.organization)?.name}
                            </p>
                        )}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <Label>Event Type</Label>
                        <Select
                            value={formData.event_type}
                            onValueChange={(value) => updateFormData({ event_type: value as any })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="webinar">Webinar</SelectItem>
                                <SelectItem value="workshop">Workshop</SelectItem>
                                <SelectItem value="training">Training Session</SelectItem>
                                <SelectItem value="lecture">Lecture</SelectItem>
                                <SelectItem value="other">Other</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>

                    <div className="space-y-2">
                        <Label>Format</Label>
                        <Select
                            value={formData.format}
                            onValueChange={(value: any) => updateFormData({ format: value })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select format" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="online">Online</SelectItem>
                                <SelectItem value="in-person">In Person</SelectItem>
                                <SelectItem value="hybrid">Hybrid</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </div>
            </div>
        </div>
    );
};
