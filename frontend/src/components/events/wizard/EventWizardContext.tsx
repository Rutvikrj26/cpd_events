import React, { createContext, useContext, useState, ReactNode } from 'react';
import { EventCreateRequest } from '@/api/events/types';

export enum WizardStep {
    BasicInfo = 0,
    Schedule = 1,
    Details = 2,
    Settings = 3,
    Review = 4
}

interface EventWizardState {
    currentStep: WizardStep;
    formData: Partial<EventCreateRequest>;
    // Helper to store raw input values if needed before processing
    raw?: any;
}

interface EventWizardContextType extends EventWizardState {
    setStep: (step: WizardStep) => void;
    nextStep: () => void;
    prevStep: () => void;
    updateFormData: (data: Partial<EventCreateRequest>) => void;
    isStepValid: (step: WizardStep) => boolean;
    isEditMode: boolean;
}

const EventWizardContext = createContext<EventWizardContextType | undefined>(undefined);

export const useEventWizard = () => {
    const context = useContext(EventWizardContext);
    if (!context) {
        throw new Error('useEventWizard must be used within an EventWizardProvider');
    }
    return context;
};

// Initial default state
const initialFormData: Partial<EventCreateRequest> = {
    title: '',
    event_type: 'webinar',
    format: 'online',
    description: '',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
    registration_enabled: true,
    cpd_enabled: true,
    cpd_credit_value: 1,
    is_public: true,
    minimum_attendance_minutes: 0,
    minimum_attendance_percent: 0,
    certificates_enabled: false,
    auto_issue_certificates: false,
    certificate_template: null,
    badges_enabled: false,
    auto_issue_badges: false,
    badge_template: null,

    // Payment Settings
    price: 0,
    currency: 'USD',
    is_free: true,
    zoom_settings: {},

    // Multi-session support
    is_multi_session: false,
    _sessions: [],
};

interface EventWizardProviderProps {
    children: ReactNode;
    initialData?: Partial<EventCreateRequest>;
    isEditMode?: boolean;
}

export const EventWizardProvider = ({ children, initialData, isEditMode }: EventWizardProviderProps) => {
    const [currentStep, setCurrentStep] = useState<WizardStep>(WizardStep.BasicInfo);
    const [formData, setFormData] = useState<Partial<EventCreateRequest>>(() => ({
        ...initialFormData,
        ...initialData,
    }));

    const updateFormData = (data: Partial<EventCreateRequest>) => {
        setFormData(prev => ({ ...prev, ...data }));
    };

    const nextStep = () => {
        setCurrentStep(prev => Math.min(prev + 1, WizardStep.Review));
    };

    const prevStep = () => {
        setCurrentStep(prev => Math.max(prev - 1, WizardStep.BasicInfo));
    };

    // Basic validation logic per step (can be expanded)
    const isStepValid = (step: WizardStep): boolean => {
        switch (step) {
            case WizardStep.BasicInfo:
                return !!formData.title && !!formData.event_type && !!formData.format;
            case WizardStep.Schedule:
                // Check if starts_at and duration are present
                // Note: starts_at might be partial if typing, so we check carefully
                return !!formData.starts_at && (formData.duration_minutes || 0) >= 15;
            case WizardStep.Details:
                return !!formData.description;
            case WizardStep.Settings:
                if (formData.certificates_enabled && !formData.certificate_template) {
                    return false;
                }
                return true;
            default:
                return true;
        }
    };

    return (
        <EventWizardContext.Provider value={{
            currentStep,
            formData,
            setStep: setCurrentStep,
            nextStep,
            prevStep,
            updateFormData,
            isStepValid,
            isEditMode: isEditMode || false
        }}>
            {children}
        </EventWizardContext.Provider>
    );
};
