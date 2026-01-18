import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
    CheckCircle,
    Circle,
    User,
    Video,
    Calendar,
    CreditCard,
    BookOpen,
    ChevronRight,
    X,
    Sparkles
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';
import { useAuth } from '@/contexts/AuthContext';
import { getZoomStatus } from '@/api/integrations';
import { getEvents } from '@/api/events';
import { getSubscription } from '@/api/billing';
import { getOwnedCourses } from '@/api/courses';
import { getRoleFlags } from '@/lib/role-utils';

interface ChecklistItem {
    id: string;
    title: string;
    description: string;
    icon: React.ElementType;
    completed: boolean;
    href?: string;
    action?: string;
}

interface OnboardingChecklistProps {
    onDismiss?: () => void;
    variant?: 'card' | 'sidebar';
}

const STORAGE_KEY = 'onboarding_checklist_dismissed';

const getInitialDismissed = () => {
    if (typeof window === 'undefined') return false;
    return localStorage.getItem(STORAGE_KEY) === 'true';
};

export function OnboardingChecklist({ onDismiss, variant = 'card' }: OnboardingChecklistProps) {
    const { user } = useAuth();
    const [items, setItems] = useState<ChecklistItem[]>([]);
    const [loading, setLoading] = useState(() => !getInitialDismissed());
    const [dismissed, setDismissed] = useState(getInitialDismissed);

    useEffect(() => {
        if (dismissed) return;

        async function checkProgress() {
            if (!user) {
                setLoading(false);
                return;
            }

            const checklistItems: ChecklistItem[] = [];
            const subscription = await getSubscription().catch(() => null);
            const { isOrganizer, isCourseManager } = getRoleFlags(user, subscription);

            if (!isOrganizer && !isCourseManager) {
                setLoading(false);
                return;
            }

            // 1. Complete Profile
            const hasProfile = isOrganizer
                ? !!(user?.full_name && user?.organization_name)
                : !!user?.full_name;
            checklistItems.push({
                id: 'profile',
                title: 'Complete your profile',
                description: isOrganizer
                    ? 'Add your organization name and details'
                    : 'Add your personal details and preferences',
                icon: User,
                completed: hasProfile,
                href: '/settings',
                action: 'Complete Profile'
            });

            // 2. Connect Zoom (organizer or course manager)
            if (isOrganizer || isCourseManager) {
                try {
                    const zoomStatus = await getZoomStatus();
                    checklistItems.push({
                        id: 'zoom',
                        title: 'Connect Zoom account',
                        description: 'Enable automatic meeting creation',
                        icon: Video,
                        completed: zoomStatus.is_connected,
                        href: '/organizer/zoom',
                        action: 'Connect Zoom'
                    });
                } catch {
                    checklistItems.push({
                        id: 'zoom',
                        title: 'Connect Zoom account',
                        description: 'Enable automatic meeting creation',
                        icon: Video,
                        completed: false,
                        href: '/organizer/zoom',
                        action: 'Connect Zoom'
                    });
                }
            }

            // 3. Create First Event
            if (isOrganizer) {
                try {
                    const events = await getEvents();
                    checklistItems.push({
                        id: 'event',
                        title: 'Create your first event',
                        description: 'Set up a webinar, workshop, or training',
                        icon: Calendar,
                        completed: events.results.length > 0,
                        href: '/events/create',
                        action: 'Create Event'
                    });
                } catch {
                    checklistItems.push({
                        id: 'event',
                        title: 'Create your first event',
                        description: 'Set up a webinar, workshop, or training',
                        icon: Calendar,
                        completed: false,
                        href: '/events/create',
                        action: 'Create Event'
                    });
                }
            }

            // 4. Create First Course
            if (isCourseManager) {
                try {
                    const courses = await getOwnedCourses();
                    checklistItems.push({
                        id: 'course',
                        title: 'Create your first course',
                        description: 'Build a self-paced learning experience',
                        icon: BookOpen,
                        completed: courses.length > 0,
                        href: '/courses/manage/new',
                        action: 'Create Course'
                    });
                } catch {
                    checklistItems.push({
                        id: 'course',
                        title: 'Create your first course',
                        description: 'Build a self-paced learning experience',
                        icon: BookOpen,
                        completed: false,
                        href: '/courses/manage/new',
                        action: 'Create Course'
                    });
                }
            }

            // 5. Set up Billing
            try {
                const hasBilling = subscription?.status === 'active' ||
                    subscription?.status === 'trialing';
                checklistItems.push({
                    id: 'billing',
                    title: 'Set up billing',
                    description: 'Add a payment method for when your trial ends',
                    icon: CreditCard,
                    completed: hasBilling,
                    href: '/billing',
                    action: 'Set Up Billing'
                });
            } catch {
                checklistItems.push({
                    id: 'billing',
                    title: 'Set up billing',
                    description: 'Add a payment method for when your trial ends',
                    icon: CreditCard,
                    completed: false,
                    href: '/billing',
                    action: 'Set Up Billing'
                });
            }

            setItems(checklistItems);
            setLoading(false);
        }

        checkProgress();
    }, [user, dismissed]);

    const handleDismiss = () => {
        localStorage.setItem(STORAGE_KEY, 'true');
        setDismissed(true);
        onDismiss?.();
    };

    // Don't show for non-creators
    if (items.length === 0) {
        return null;
    }

    // Don't show if dismissed or loading
    if (dismissed || loading) {
        return null;
    }

    const completedCount = items.filter(i => i.completed).length;
    const totalCount = items.length;
    const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
    const allComplete = completedCount === totalCount;

    // Don't show if all items are complete
    if (allComplete) {
        return null;
    }

    if (variant === 'sidebar') {
        return (
            <div className="p-4 bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg border border-primary/20">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                        <Sparkles className="h-4 w-4 text-primary" />
                        <span className="text-sm font-medium">Getting Started</span>
                    </div>
                    <button
                        onClick={handleDismiss}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-4 w-4" />
                    </button>
                </div>
                <Progress value={progress} className="h-1.5 mb-3" />
                <p className="text-xs text-muted-foreground mb-3">
                    {completedCount} of {totalCount} complete
                </p>
                <div className="space-y-2">
                    {items.filter(i => !i.completed).slice(0, 2).map((item) => (
                        <Link
                            key={item.id}
                            to={item.href || '#'}
                            className="flex items-center gap-2 text-xs text-primary hover:underline"
                        >
                            <Circle className="h-3 w-3" />
                            {item.title}
                        </Link>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <Card className="border-primary/20 bg-gradient-to-br from-primary/5 to-transparent">
            <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-primary/10">
                            <Sparkles className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                            <CardTitle className="text-lg">Complete Your Setup</CardTitle>
                            <p className="text-sm text-muted-foreground">
                                {completedCount} of {totalCount} tasks complete
                            </p>
                        </div>
                    </div>
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleDismiss}
                        className="h-8 w-8"
                    >
                        <X className="h-4 w-4" />
                    </Button>
                </div>
                <Progress value={progress} className="h-2 mt-3" />
            </CardHeader>
            <CardContent className="pt-0">
                <div className="space-y-2">
                    {items.map((item) => {
                        const Icon = item.icon;
                        return (
                            <Link
                                key={item.id}
                                to={item.href || '#'}
                                className={cn(
                                    "flex items-center gap-3 p-3 rounded-lg transition-colors",
                                    item.completed
                                        ? "bg-muted/30"
                                        : "bg-card hover:bg-muted/50 border border-border"
                                )}
                            >
                                <div className={cn(
                                    "p-2 rounded-full",
                                    item.completed
                                        ? "bg-green-100 dark:bg-green-900/30"
                                        : "bg-muted"
                                )}>
                                    {item.completed ? (
                                        <CheckCircle className="h-4 w-4 text-green-600" />
                                    ) : (
                                        <Icon className="h-4 w-4 text-muted-foreground" />
                                    )}
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className={cn(
                                        "text-sm font-medium",
                                        item.completed && "text-muted-foreground line-through"
                                    )}>
                                        {item.title}
                                    </p>
                                    <p className="text-xs text-muted-foreground truncate">
                                        {item.description}
                                    </p>
                                </div>
                                {!item.completed && (
                                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />
                                )}
                            </Link>
                        );
                    })}
                </div>
            </CardContent>
        </Card>
    );
}
