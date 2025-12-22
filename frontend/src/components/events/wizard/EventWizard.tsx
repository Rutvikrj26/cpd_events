import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { Button } from '@/components/ui/button';
import { EventWizardProvider, useEventWizard, WizardStep } from './EventWizardContext';
import { StepBasicInfo } from './steps/StepBasicInfo';
import { StepSchedule } from './steps/StepSchedule';
import { StepDetails } from './steps/StepDetails';
import { StepSettings } from './steps/StepSettings';
import { StepReview } from './steps/StepReview';
import {
    createEvent,
    updateEvent,
    uploadEventImage,
    deleteEventImage,
    createEventSession,
    updateEventSession,
    getEventSessions,
    deleteEventSession
} from '@/api/events';
import { EventCreateRequest } from '@/api/events/types';
import { toast } from 'sonner';

// The inner content that consumes the context
const WizardContent = () => {
    const { currentStep, nextStep, prevStep, formData, isStepValid, isEditMode } = useEventWizard();
    const navigate = useNavigate();
    const [isSubmitting, setIsSubmitting] = React.useState(false);

    const steps = [
        { id: WizardStep.BasicInfo, label: 'Basic Info' },
        { id: WizardStep.Schedule, label: 'Schedule' },
        { id: WizardStep.Details, label: 'Details' },
        { id: WizardStep.Settings, label: 'Settings' },
        { id: WizardStep.Review, label: 'Review' },
    ];

    const handleFinish = async () => {
        setIsSubmitting(true);
        try {
            // Extract frontend-only fields from form data
            const { _imageFile, _sessions, _isImageRemoved, ...eventData } = formData;

            let savedEvent;
            if (isEditMode && formData.uuid) {
                // For update, we use the UUID and Partial data
                savedEvent = await updateEvent(formData.uuid, eventData);
                toast.success('Event updated successfully!');
            } else {
                // For create, we assert that the form data is complete enough (validated by steps)
                savedEvent = await createEvent(eventData as EventCreateRequest);
                toast.success('Event created successfully!');
            }

            // Robustly get UUID - fallback to formData.uuid for updates if response is partial
            const targetUuid = savedEvent?.uuid || (isEditMode ? formData.uuid : undefined);

            // Upload image if a file was selected
            if (_imageFile && targetUuid) {
                try {
                    await uploadEventImage(targetUuid, _imageFile);
                    toast.success('Image uploaded successfully!');
                } catch (imgError) {
                    console.error('Image upload failed:', imgError);
                    toast.warning('Event saved but image upload failed. You can try again later.');
                }
            } else if (_isImageRemoved && targetUuid) {
                // If explicit removal was requested and no new file replaced it
                try {
                    await deleteEventImage(targetUuid);
                    toast.info('Cover image removed.');
                } catch (delError) {
                    console.error('Image deletion failed:', delError);
                }
            }

            // Save sessions if multi-session is enabled
            if (formData.is_multi_session && _sessions && _sessions.length > 0 && targetUuid) {
                try {
                    // If editing, we need to handle existing sessions
                    if (isEditMode) {
                        const existingSessions = await getEventSessions(targetUuid);
                        const existingUuids = new Set(existingSessions.map(s => s.uuid));
                        const newSessionUuids = new Set(_sessions.filter(s => s.uuid).map(s => s.uuid));

                        // Delete sessions that were removed
                        for (const existing of existingSessions) {
                            if (!newSessionUuids.has(existing.uuid)) {
                                await deleteEventSession(targetUuid, existing.uuid!);
                            }
                        }

                        // Create or update sessions
                        for (const session of _sessions) {
                            if (session.uuid && existingUuids.has(session.uuid)) {
                                await updateEventSession(targetUuid, session.uuid, session);
                            } else {
                                await createEventSession(targetUuid, session);
                            }
                        }
                    } else {
                        // Create all sessions for new event
                        for (const session of _sessions) {
                            await createEventSession(targetUuid, session);
                        }
                    }
                    toast.success(`${_sessions.length} session(s) saved!`);
                } catch (sessionError) {
                    console.error('Session save failed:', sessionError);
                    toast.warning('Event saved but some sessions could not be saved.');
                }
            }

            navigate('/events');
        } catch (error) {
            console.error(error);
            toast.error(isEditMode ? 'Failed to update event. Please try again.' : 'Failed to create event. Please try again.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="max-w-4xl mx-auto py-8 px-4">
            {/* Stepper Header */}
            <div className="mb-8">
                <nav aria-label="Progress">
                    <ol role="list" className="space-y-4 md:flex md:space-x-8 md:space-y-0">
                        {steps.map((step) => {
                            const isComplete = currentStep > step.id;
                            const isCurrent = currentStep === step.id;

                            return (
                                <li key={step.id} className="md:flex-1">
                                    <div
                                        className={cn(
                                            "group flex flex-col border-l-4 py-2 pl-4 transition-colors md:border-l-0 md:border-t-4 md:pb-0 md:pl-0 md:pt-4",
                                            isComplete ? "border-primary hover:border-primary/80" :
                                                isCurrent ? "border-primary" : "border-muted"
                                        )}
                                    >
                                        <span className={cn(
                                            "text-xs font-semibold uppercase tracking-wide",
                                            isComplete || isCurrent ? "text-primary" : "text-muted-foreground"
                                        )}>
                                            Step {step.id + 1}
                                        </span>
                                        <span className="text-sm font-medium">{step.label}</span>
                                    </div>
                                </li>
                            );
                        })}
                    </ol>
                </nav>
            </div>

            {/* Step Content */}
            <div className="bg-card rounded-xl border border-border shadow-sm min-h-[400px] flex flex-col">
                <div className="p-6 md:p-8 flex-1">
                    {currentStep === WizardStep.BasicInfo && <StepBasicInfo />}
                    {currentStep === WizardStep.Schedule && <StepSchedule />}
                    {currentStep === WizardStep.Details && <StepDetails />}
                    {currentStep === WizardStep.Settings && <StepSettings />}
                    {currentStep === WizardStep.Review && <StepReview />}
                </div>

                {/* Footer Controls */}
                <div className="bg-muted/30 p-4 rounded-b-xl border-t border-border flex justify-between items-center">
                    <Button
                        variant="ghost"
                        onClick={currentStep === 0 ? () => navigate('/events') : prevStep}
                    >
                        {currentStep === 0 ? 'Cancel' : 'Back'}
                    </Button>

                    <div className="flex gap-3">
                        {/* Optional Draft Save could go here */}

                        {currentStep === WizardStep.Review ? (
                            <Button onClick={handleFinish} disabled={isSubmitting} className="min-w-[120px]">
                                {isSubmitting ? (isEditMode ? 'Updating...' : 'Creating...') : (isEditMode ? 'Update Event' : 'Create Event')}
                            </Button>
                        ) : (
                            <Button
                                onClick={nextStep}
                                disabled={!isStepValid(currentStep)}
                                className="min-w-[100px]"
                            >
                                Next <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

interface EventWizardProps {
    initialData?: any;
    isEditMode?: boolean;
}

export const EventWizard = ({ initialData, isEditMode }: EventWizardProps) => {
    return (
        <EventWizardProvider initialData={initialData} isEditMode={isEditMode}>
            <WizardContent />
        </EventWizardProvider>
    );
};
