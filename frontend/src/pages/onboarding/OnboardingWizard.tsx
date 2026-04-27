import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Rocket,
    User,
    Calendar,
    BookOpen,
    ArrowRight,
    ArrowLeft,
    Check,
    Loader2,
    Building2,
} from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Input } from '@/shared/ui/input';
import { Label } from '@/shared/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/shared/ui/card';
import { Progress } from '@/shared/ui/progress';
import { useAuth } from '@/features/auth';
import { updateProfile, completeOnboarding } from '@/api/accounts';
import { toast } from 'sonner';

interface OnboardingWizardProps {
    onComplete?: () => void;
}

export function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
    const navigate = useNavigate();
    const { user, refreshManifest, refreshUser } = useAuth();
    const [searchParams, setSearchParams] = useSearchParams();
    const [currentStep, setCurrentStep] = useState(() => {
        const stepParam = searchParams.get('step');
        return stepParam ? parseInt(stepParam, 10) : 0;
    });
    const [isLoading, setIsLoading] = useState(false);

    const [profileData, setProfileData] = useState({
        organization_name: user?.organization_name || '',
        full_name: user?.full_name || '',
    });

    const isLearner = user?.primary_role === 'learner';
    const isLmsOnly = user?.primary_role === 'instructor';

    const steps = isLearner
        ? [
            { id: 'welcome', title: 'Welcome', icon: Rocket },
            { id: 'complete', title: 'Get Started', icon: Calendar },
        ]
        : [
            { id: 'welcome', title: 'Welcome', icon: Rocket },
            { id: 'profile', title: 'Your Profile', icon: User },
            { id: 'complete', title: 'Get Started', icon: isLmsOnly ? BookOpen : Calendar },
        ];

    const progress = ((currentStep + 1) / steps.length) * 100;
    const stepId = steps[currentStep]?.id;

    const nextStep = () => {
        if (currentStep < steps.length - 1) {
            setCurrentStep(prev => prev + 1);
        }
    };

    const prevStep = () => {
        if (currentStep > 0) {
            setCurrentStep(prev => prev - 1);
        }
    };

    const handleProfileSubmit = async () => {
        setIsLoading(true);
        try {
            await updateProfile({
                organization_name: profileData.organization_name,
                full_name: profileData.full_name,
            });
            toast.success("Profile updated!");
            nextStep();
        } catch (error) {
            toast.error("Failed to update profile");
        } finally {
            setIsLoading(false);
        }
    };

    const handleComplete = async () => {
        try {
            // Mark onboarding as complete on the backend
            await completeOnboarding();
            // Refresh user state and manifest to reflect the change
            await Promise.all([refreshUser(), refreshManifest()]);
            toast.success("You're all set! Welcome aboard.");

            if (onComplete) {
                onComplete();
            } else {
                navigate('/dashboard');
            }
        } catch (error) {
            // If API fails, still navigate to dashboard
            console.error('Failed to complete onboarding:', error);
            navigate('/dashboard');
        }
    };

    // Sync currentStep with URL
    React.useEffect(() => {
        setSearchParams({ step: currentStep.toString() }, { replace: true });
    }, [currentStep, setSearchParams]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-background to-muted/30 flex items-center justify-center p-4">
            <div className="w-full max-w-2xl">
                {/* Progress Header */}
                <div className="mb-8">
                    <div className="flex items-center justify-between mb-4">
                        {steps.map((step, index) => {
                            const Icon = step.icon;
                            const isComplete = index < currentStep;
                            const isCurrent = index === currentStep;

                            return (
                                <div
                                    key={step.id}
                                    className={`flex items-center gap-2 ${isCurrent ? 'text-primary' : isComplete ? 'text-success' : 'text-muted-foreground'
                                        }`}
                                >
                                    <div className={`
                                        w-10 h-10 rounded-full flex items-center justify-center
                                        ${isCurrent ? 'bg-primary text-primary-foreground' :
                                            isComplete ? 'bg-success text-success-foreground' :
                                                'bg-muted'}
                                    `}>
                                        {isComplete ? <Check className="h-5 w-5" /> : <Icon className="h-5 w-5" />}
                                    </div>
                                    <span className="hidden sm:block text-sm font-medium">{step.title}</span>
                                </div>
                            );
                        })}
                    </div>
                    <Progress value={progress} className="h-2" />
                </div>

                {/* Step Content */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={currentStep}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        transition={{ duration: 0.3 }}
                    >
                        <Card className="border-2">
                            {/* Step 0: Welcome */}
                            {stepId === 'welcome' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-primary/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mb-4">
                                            <Rocket className="h-10 w-10 text-primary" />
                                        </div>
                                        <CardTitle className="text-2xl">Welcome to Accredit! 🎉</CardTitle>
                                        <CardDescription className="text-base">
                                            {isLearner
                                                ? "You're all set to discover professional development opportunities"
                                                : isLmsOnly
                                                    ? "Let's get you set up to launch impactful courses"
                                                    : "Let's get you set up to create amazing CPD events"}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-6 text-center">
                                        {isLearner ? (
                                            <>
                                                <div className="grid grid-cols-3 gap-4 text-center">
                                                    <div className="p-4 bg-card border border-border rounded-lg">
                                                        <div className="h-8 w-8 mx-auto rounded-lg bg-primary/15 flex items-center justify-center mb-2">
                                                            <Calendar className="h-4 w-4 text-primary" />
                                                        </div>
                                                        <div className="text-sm font-medium text-foreground">Browse Events</div>
                                                        <div className="text-xs text-muted-foreground">Find CPD opportunities</div>
                                                    </div>
                                                    <div className="p-4 bg-card border border-border rounded-lg">
                                                        <div className="h-8 w-8 mx-auto rounded-lg bg-accent/15 flex items-center justify-center mb-2">
                                                            <BookOpen className="h-4 w-4 text-accent" />
                                                        </div>
                                                        <div className="text-sm font-medium text-foreground">Take Courses</div>
                                                        <div className="text-xs text-muted-foreground">Learn at your pace</div>
                                                    </div>
                                                    <div className="p-4 bg-card border border-border rounded-lg">
                                                        <div className="h-8 w-8 mx-auto rounded-lg bg-success/15 flex items-center justify-center mb-2">
                                                            <Check className="h-4 w-4 text-success" />
                                                        </div>
                                                        <div className="text-sm font-medium text-foreground">Earn Certificates</div>
                                                        <div className="text-xs text-muted-foreground">Track your CPD</div>
                                                    </div>
                                                </div>
                                            </>
                                        ) : (
                                            <div className="grid grid-cols-2 gap-4 text-center">
                                                <div className="p-4 bg-muted/30 rounded-lg">
                                                    <div className="text-2xl font-bold text-primary">
                                                        {isLmsOnly ? 'Courses' : 'Events'}
                                                    </div>
                                                    <div className="text-sm text-muted-foreground">
                                                        {isLmsOnly ? 'Launch self-paced learning' : 'Run live sessions'}
                                                    </div>
                                                </div>
                                                <div className="p-4 bg-muted/30 rounded-lg">
                                                    <div className="text-2xl font-bold text-primary">Certificates</div>
                                                    <div className="text-sm text-muted-foreground">Track CPD & completions</div>
                                                </div>
                                            </div>
                                        )}

                                        <Button size="lg" onClick={nextStep} className="w-full">
                                            {isLearner ? "Let's Go!" : "Let's Get Started"}
                                            <ArrowRight className="ml-2 h-4 w-4" />
                                        </Button>
                                    </CardContent>
                                </>
                            )}

                            {/* Step 1: Profile */}
                            {stepId === 'profile' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-primary/10 rounded-full p-4 w-16 h-16 flex items-center justify-center mb-2">
                                            <Building2 className="h-8 w-8 text-primary" />
                                        </div>
                                        <CardTitle>Set Up Your Profile</CardTitle>
                                        <CardDescription>
                                            {isLmsOnly
                                                ? 'This info will appear on your courses and certificates'
                                                : 'This info will appear on your events and certificates'}
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="space-y-2">
                                            <Label htmlFor="full_name">Your Name</Label>
                                            <Input
                                                id="full_name"
                                                value={profileData.full_name}
                                                onChange={e => setProfileData(prev => ({ ...prev, full_name: e.target.value }))}
                                                placeholder="Dr. Jane Smith"
                                            />
                                        </div>

                                        <div className="space-y-2">
                                            <Label htmlFor="organization_name">
                                                {isLmsOnly ? 'Organization / Brand (Optional)' : 'Organization / Company Name'}
                                            </Label>
                                            <Input
                                                id="organization_name"
                                                value={profileData.organization_name}
                                                onChange={e => setProfileData(prev => ({ ...prev, organization_name: e.target.value }))}
                                                placeholder="Healthcare Training Institute"
                                            />
                                            <p className="text-xs text-muted-foreground">
                                                {isLmsOnly ? 'Shown on course certificates and landing pages' : 'This will be shown as the event organizer'}
                                            </p>
                                        </div>

                                        <div className="flex gap-3 pt-4">
                                            <Button variant="outline" onClick={prevStep}>
                                                <ArrowLeft className="mr-2 h-4 w-4" />
                                                Back
                                            </Button>
                                            <Button
                                                className="flex-1"
                                                onClick={handleProfileSubmit}
                                                disabled={isLoading || !profileData.full_name || (!isLmsOnly && !profileData.organization_name)}
                                            >
                                                {isLoading ? (
                                                    <Loader2 className="h-4 w-4 animate-spin" />
                                                ) : (
                                                    <>
                                                        Continue
                                                        <ArrowRight className="ml-2 h-4 w-4" />
                                                    </>
                                                )}
                                            </Button>
                                        </div>
                                    </CardContent>
                                </>
                            )}

                            {/* Step: Complete */}
                            {stepId === 'complete' && (
                                <>
                                    <CardHeader className="text-center pb-2">
                                        <div className="mx-auto bg-success/10 rounded-full p-4 w-20 h-20 flex items-center justify-center mb-4">
                                            <Check className="h-10 w-10 text-success" />
                                        </div>
                                        <CardTitle className="text-2xl">You're All Set! 🎉</CardTitle>
                                        <CardDescription className="text-base">
                                            Your account is ready. What would you like to do first?
                                        </CardDescription>
                                    </CardHeader>
                                    <CardContent className="space-y-4">
                                        <div className="grid gap-3">
                                            {isLearner ? (
                                                <>
                                                    <Button
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={() => {
                                                            handleComplete();
                                                            navigate('/events');
                                                        }}
                                                    >
                                                        <Calendar className="mr-3 h-5 w-5" />
                                                        <div className="text-left">
                                                            <div className="font-medium">Browse Events</div>
                                                            <div className="text-xs opacity-80">Find CPD opportunities</div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>

                                                    <Button
                                                        variant="outline"
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={() => {
                                                            handleComplete();
                                                            navigate('/courses');
                                                        }}
                                                    >
                                                        <BookOpen className="mr-3 h-5 w-5 text-muted-foreground" />
                                                        <div className="text-left">
                                                            <div className="font-medium">Explore Courses</div>
                                                            <div className="text-xs text-muted-foreground">Learn at your own pace</div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>
                                                </>
                                            ) : (
                                                <>
                                                    <Button
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={() => {
                                                            handleComplete();
                                                            navigate(isLmsOnly ? '/courses/manage/new' : '/events/create');
                                                        }}
                                                    >
                                                        {isLmsOnly ? (
                                                            <BookOpen className="mr-3 h-5 w-5" />
                                                        ) : (
                                                            <Calendar className="mr-3 h-5 w-5" />
                                                        )}
                                                        <div className="text-left">
                                                            <div className="font-medium">
                                                                {isLmsOnly ? 'Create Your First Course' : 'Create Your First Event'}
                                                            </div>
                                                            <div className="text-xs opacity-80">
                                                                {isLmsOnly ? 'Launch your first learning experience' : 'Start engaging your audience'}
                                                            </div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>

                                                    <Button
                                                        variant="outline"
                                                        size="lg"
                                                        className="w-full h-auto py-4"
                                                        onClick={handleComplete}
                                                    >
                                                        <Rocket className="mr-3 h-5 w-5 text-muted-foreground" />
                                                        <div className="text-left">
                                                            <div className="font-medium">Explore Dashboard</div>
                                                            <div className="text-xs text-muted-foreground">Get familiar with the platform</div>
                                                        </div>
                                                        <ArrowRight className="ml-auto h-5 w-5" />
                                                    </Button>
                                                </>
                                            )}
                                        </div>
                                    </CardContent>
                                </>
                            )}
                        </Card>
                    </motion.div>
                </AnimatePresence>
            </div>


        </div>
    );
}
