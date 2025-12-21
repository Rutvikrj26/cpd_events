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

export const StepBasicInfo = () => {
    const { formData, updateFormData } = useEventWizard();

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-right-4 duration-300">
            <div className="space-y-2">
                <h2 className="text-xl font-semibold text-slate-900">Basic Information</h2>
                <p className="text-sm text-slate-500">Let's start with the core details of your event.</p>
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

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <Label>Event Type</Label>
                        <Select
                            value={formData.event_type}
                            onValueChange={(value) => updateFormData({ event_type: value })}
                        >
                            <SelectTrigger>
                                <SelectValue placeholder="Select type" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="webinar">Webinar</SelectItem>
                                <SelectItem value="workshop">Workshop</SelectItem>
                                <SelectItem value="conference">Conference</SelectItem>
                                <SelectItem value="training">Training Session</SelectItem>
                                <SelectItem value="networking">Networking Event</SelectItem>
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
