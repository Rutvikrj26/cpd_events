import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createEvent } from '@/api/events';
import { EventCreateRequest } from '@/api/events/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';

export const EventCreatePage = () => {
    const navigate = useNavigate();
    const { toast } = useToast();
    const [loading, setLoading] = useState(false);
    const [formData, setFormData] = useState<EventCreateRequest>({
        title: '',
        description: '',
        start_date: '',
        end_date: '',
        timezone: 'UTC',
        format: 'online', // Default
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        try {
            await createEvent(formData);
            toast({ title: 'Success', description: 'Event created successfully' });
            navigate('/events');
        } catch (error) {
            console.error(error);
            toast({ variant: 'destructive', title: 'Error', description: 'Failed to create event' });
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-2xl mx-auto py-8">
            <h1 className="text-2xl font-bold mb-6">Create New Event</h1>
            <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl border shadow-sm space-y-6">

                <div className="space-y-2">
                    <label className="text-sm font-medium">Event Title</label>
                    <Input
                        required
                        value={formData.title}
                        onChange={e => setFormData({ ...formData, title: e.target.value })}
                        placeholder="e.g. Annual CPD Conference 2024"
                    />
                </div>

                <div className="space-y-2">
                    <label className="text-sm font-medium">Description</label>
                    <textarea
                        className="w-full min-h-[100px] border rounded-md p-3 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
                        required
                        value={formData.description}
                        onChange={e => setFormData({ ...formData, description: e.target.value })}
                    />
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Start Date & Time</label>
                        <Input
                            type="datetime-local"
                            required
                            value={formData.start_date}
                            onChange={e => setFormData({ ...formData, start_date: e.target.value })}
                        />
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">End Date & Time</label>
                        <Input
                            type="datetime-local"
                            required
                            value={formData.end_date}
                            onChange={e => setFormData({ ...formData, end_date: e.target.value })}
                        />
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Format</label>
                        <select
                            className="w-full border rounded-md h-10 px-3 text-sm"
                            value={formData.format}
                            onChange={e => setFormData({ ...formData, format: e.target.value as any })}
                        >
                            <option value="online">Online</option>
                            <option value="in-person">In Person</option>
                            <option value="hybrid">Hybrid</option>
                        </select>
                    </div>
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Timezone</label>
                        <Input
                            value={formData.timezone}
                            onChange={e => setFormData({ ...formData, timezone: e.target.value })}
                        />
                    </div>
                </div>

                <div className="pt-4 flex justify-end gap-3">
                    <Button type="button" variant="ghost" onClick={() => navigate('/events')}>Cancel</Button>
                    <Button type="submit" disabled={loading}>
                        {loading ? 'Creating...' : 'Create Event'}
                    </Button>
                </div>

            </form>
        </div>
    );
};
