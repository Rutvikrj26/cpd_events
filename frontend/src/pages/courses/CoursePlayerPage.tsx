import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
    getCourse,
    getCourseProgress,
    getMySubmissions,
    createSubmission,
    updateSubmission,
    submitSubmission,
    getCourseAnnouncements,
    getCourseSessions,
} from '@/api/courses';
import { getCourseModules, getModuleContents } from '@/api/courses/modules';
import { updateContentProgress } from '@/api/learning';
import { Course, CourseModule, Assignment, AssignmentSubmission, CourseAnnouncement, CourseSession } from '@/api/courses/types';
import { SessionsPanel } from '@/components/courses/SessionsPanel';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/components/ui/use-toast';
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from '@/components/ui/dialog';
import {
    ArrowLeft,
    CheckCircle2,
    Circle,
    PlayCircle,
    FileText,
    Video,
    File,
    Loader2,
    ChevronRight,
    Award,
    ExternalLink,
    ClipboardCheck,
    Info
} from 'lucide-react';

interface ModuleContent {
    uuid: string;
    title: string;
    content_type: 'text' | 'video' | 'document' | 'quiz' | 'lesson' | 'external';
    content_data?: any;
    file?: string;
    duration_minutes?: number;
    is_required: boolean;
    order: number;
}

interface ContentWithProgress extends ModuleContent {
    completed?: boolean;
}

interface ModuleWithContents extends CourseModule {
    contents?: ContentWithProgress[];
    expanded?: boolean;
}

type CourseItem =
    | { type: 'content'; item: ContentWithProgress; moduleUuid: string }
    | { type: 'assignment'; item: Assignment; moduleUuid: string };

export function CoursePlayerPage() {
    const { courseUuid } = useParams<{ courseUuid: string }>();
    const navigate = useNavigate();
    const { toast } = useToast();

    const [course, setCourse] = useState<Course | null>(null);
    const [modules, setModules] = useState<ModuleWithContents[]>([]);
    const [currentItem, setCurrentItem] = useState<CourseItem | null>(null);
    const [currentModuleUuid, setCurrentModuleUuid] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [contentLoading, setContentLoading] = useState(false);
    const [completedContents, setCompletedContents] = useState<Set<string>>(new Set());
    const [isEnrollmentBlocked, setIsEnrollmentBlocked] = useState(false);
    const [submissions, setSubmissions] = useState<AssignmentSubmission[]>([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [assignmentDraft, setAssignmentDraft] = useState({
        text: '',
        url: '',
        file_url: '',
    });
    const [announcements, setAnnouncements] = useState<CourseAnnouncement[]>([]);
    const [showAnnouncements, setShowAnnouncements] = useState(false);
    const [sessions, setSessions] = useState<CourseSession[]>([]);

    // Fetch course and modules on mount
    useEffect(() => {
        const fetchCourseData = async () => {
            if (!courseUuid) return;

            setIsEnrollmentBlocked(false);
            setCompletedContents(new Set());
            setSubmissions([]);
            setAnnouncements([]);
            try {
                // Fetch course details
                const courseData = await getCourse(courseUuid);
                setCourse(courseData);

                // Fetch modules
                const modulesData = await getCourseModules(courseUuid);

                // Fetch contents for each module
                const modulesWithContents = await Promise.all(
                    modulesData.map(async (mod) => {
                        const moduleUuid = mod.module?.uuid || mod.uuid;
                        try {
                            const contents = await getModuleContents(courseUuid, moduleUuid);
                            return {
                                ...mod,
                                contents: contents.sort((a: any, b: any) => a.order - b.order),
                                expanded: false
                            };
                        } catch {
                            return { ...mod, contents: [], expanded: false };
                        }
                    })
                );

                const sortedModules = modulesWithContents.sort((a, b) => a.order - b.order);
                setModules(sortedModules);

                let didSelectContent = false;

                // Load announcements (staff see all, learners see published)
                try {
                    const courseAnnouncements = await getCourseAnnouncements(courseUuid);
                    setAnnouncements(courseAnnouncements);
                } catch (error) {
                    console.error('Failed to load announcements:', error);
                }

                // Load sessions for hybrid courses
                if (courseData.format === 'hybrid') {
                    try {
                        const courseSessions = await getCourseSessions(courseUuid);
                        setSessions(courseSessions.filter((s: CourseSession) => s.is_published));
                    } catch (error) {
                        console.error('Failed to load sessions:', error);
                    }
                }

                // Pull progress to restore completed items
                try {
                    const progress = await getCourseProgress(courseUuid);
                    const completed = new Set<string>();
                    progress.modules.forEach(module => {
                        module.content_progress.forEach(progressItem => {
                            if (progressItem.status === 'completed' || progressItem.progress_percent === 100) {
                                completed.add(progressItem.content);
                            }
                        });
                    });
                    setCompletedContents(completed);

                    // Auto-select first incomplete content
                    const firstIncomplete = sortedModules
                        .flatMap((mod) => {
                            const moduleUuid = mod.module?.uuid || mod.uuid;
                            return (mod.contents || []).map(content => ({ content, moduleUuid }));
                        })
                        .find(({ content }) => !completed.has(content.uuid));

                    if (firstIncomplete) {
                        setCurrentItem({ type: 'content', item: firstIncomplete.content, moduleUuid: firstIncomplete.moduleUuid });
                        setCurrentModuleUuid(firstIncomplete.moduleUuid);
                        didSelectContent = true;
                        setModules(prev => prev.map((m) => ({
                            ...m,
                            expanded: (m.module?.uuid || m.uuid) === firstIncomplete.moduleUuid
                        })));
                    }
                } catch (error: any) {
                    // Progress may be unavailable for staff previews; ignore.
                }

                // Fallback: Auto-select first content
                if (!didSelectContent) {
                    const firstModule = sortedModules.find(m => m.contents && m.contents.length > 0);
                    if (firstModule && firstModule.contents?.[0]) {
                        setCurrentItem({ type: 'content', item: firstModule.contents[0], moduleUuid: firstModule.module?.uuid || firstModule.uuid });
                        setCurrentModuleUuid(firstModule.module?.uuid || firstModule.uuid);
                        setModules(prev => prev.map((m, i) => i === 0 ? { ...m, expanded: true } : m));
                    }
                }

                // Load submissions for assignments in this course
                try {
                    const assignmentIds = sortedModules.flatMap((mod) => mod.module?.assignments || []).map((assignment) => assignment.uuid);
                    if (assignmentIds.length > 0) {
                        const allSubmissions = await getMySubmissions();
                        const courseSubmissions = allSubmissions.filter((submission) => assignmentIds.includes(submission.assignment));
                        setSubmissions(courseSubmissions);
                    }
                } catch (error) {
                    console.error('Failed to load submissions:', error);
                }

            } catch (error) {
                console.error('Failed to load course:', error);
                const status = (error as any)?.response?.status;
                if (status === 403) {
                    setIsEnrollmentBlocked(true);
                } else {
                    toast({
                        variant: 'destructive',
                        title: 'Error',
                        description: 'Failed to load course content.',
                    });
                }
            } finally {
                setLoading(false);
            }
        };

        fetchCourseData();
    }, [courseUuid, toast]);

    // Toggle module expansion
    const toggleModule = (moduleUuid: string) => {
        setModules(prev => prev.map(m => {
            const id = m.module?.uuid || m.uuid;
            return id === moduleUuid ? { ...m, expanded: !m.expanded } : m;
        }));
    };

    // Select content
    const selectContent = (content: ContentWithProgress, moduleUuid: string) => {
        setCurrentItem({ type: 'content', item: content, moduleUuid });
        setCurrentModuleUuid(moduleUuid);
    };

    const selectAssignment = (assignment: Assignment, moduleUuid: string) => {
        setCurrentItem({ type: 'assignment', item: assignment, moduleUuid });
        setCurrentModuleUuid(moduleUuid);
        const latest = getLatestSubmission(assignment.uuid);
        setAssignmentDraft({
            text: (latest?.content as any)?.text || '',
            url: (latest?.content as any)?.url || '',
            file_url: latest?.file_url || '',
        });
    };

    // Mark content as complete
    const markComplete = async () => {
        if (!courseUuid || !currentItem || currentItem.type !== 'content') return;

        try {
            await updateContentProgress(currentItem.item.uuid, { progress_percent: 100, completed: true });

            // Update local state
            setCompletedContents(prev => new Set([...prev, currentItem.item.uuid]));

            toast({
                title: 'Progress saved!',
                description: 'Content marked as complete.',
            });

            // Auto-advance to next content
            advanceToNext();
        } catch (error) {
            console.error('Failed to update progress:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: 'Failed to save progress.',
            });
        }
    };

    // Advance to next content
    const advanceToNext = () => {
        if (!currentItem || currentItem.type !== 'content' || !currentModuleUuid) return;

        // Find current module and content index
        const moduleIndex = modules.findIndex(m => (m.module?.uuid || m.uuid) === currentModuleUuid);
        const currentModule = modules[moduleIndex];
        const contentIndex = currentModule?.contents?.findIndex(c => c.uuid === currentItem.item.uuid) ?? -1;

        // Try next content in same module
        if (currentModule?.contents && contentIndex < currentModule.contents.length - 1) {
            setCurrentItem({ type: 'content', item: currentModule.contents[contentIndex + 1], moduleUuid: currentModuleUuid });
            return;
        }

        // Try first content of next module
        for (let i = moduleIndex + 1; i < modules.length; i++) {
            if (modules[i].contents && modules[i].contents!.length > 0) {
                setCurrentItem({ type: 'content', item: modules[i].contents![0], moduleUuid: modules[i].module?.uuid || modules[i].uuid });
                setCurrentModuleUuid(modules[i].module?.uuid || modules[i].uuid);
                setModules(prev => prev.map((m, idx) => ({ ...m, expanded: idx === i })));
                return;
            }
        }

        // Course complete!
        toast({
            title: '🎉 Congratulations!',
            description: 'You have completed all course content!',
        });
    };

    // Get content icon
    const getContentIcon = (type: string, completed: boolean) => {
        if (completed) return <CheckCircle2 className="h-4 w-4 text-green-500" />;

        switch (type) {
            case 'video': return <Video className="h-4 w-4 text-blue-500" />;
            case 'text': return <FileText className="h-4 w-4 text-orange-500" />;
            case 'document': return <File className="h-4 w-4 text-purple-500" />;
            case 'lesson': return <FileText className="h-4 w-4 text-emerald-500" />;
            case 'external': return <ExternalLink className="h-4 w-4 text-sky-500" />;
            default: return <Circle className="h-4 w-4 text-muted-foreground" />;
        }
    };

    // Calculate progress
    const totalContents = modules.reduce((sum, m) => sum + (m.contents?.length || 0), 0);
    const progressPercent = totalContents > 0 ? Math.round((completedContents.size / totalContents) * 100) : 0;

    const getLatestSubmission = (assignmentUuid: string) => {
        return submissions
            .filter(submission => submission.assignment === assignmentUuid)
            .sort((a, b) => (b.attempt_number || 0) - (a.attempt_number || 0))[0];
    };

    const upsertSubmission = (updated: AssignmentSubmission) => {
        setSubmissions((prev) => {
            const existingIndex = prev.findIndex(submission => submission.uuid === updated.uuid);
            if (existingIndex === -1) {
                return [updated, ...prev];
            }
            const next = [...prev];
            next[existingIndex] = updated;
            return next;
        });
    };

    const getSubmissionBadge = (status?: AssignmentSubmission['status']) => {
        switch (status) {
            case 'submitted':
                return <Badge className="bg-blue-500">Submitted</Badge>;
            case 'in_review':
                return <Badge className="bg-amber-500">In Review</Badge>;
            case 'needs_revision':
                return <Badge variant="destructive">Needs Revision</Badge>;
            case 'graded':
                return <Badge className="bg-green-500">Graded</Badge>;
            case 'approved':
                return <Badge className="bg-emerald-600">Approved</Badge>;
            case 'draft':
                return <Badge variant="secondary">Draft</Badge>;
            default:
                return <Badge variant="outline">Not Submitted</Badge>;
        }
    };

    const buildSubmissionPayload = (assignment: Assignment) => {
        const content: Record<string, any> = {};
        const submissionType = assignment.submission_type || 'text';

        if (submissionType === 'text' || submissionType === 'mixed') {
            if (assignmentDraft.text) {
                content.text = assignmentDraft.text;
            }
        }

        if (submissionType === 'url' || submissionType === 'mixed') {
            if (assignmentDraft.url) {
                content.url = assignmentDraft.url;
            }
        }

        const payload: { content?: Record<string, any>; file_url?: string } = {};
        if (Object.keys(content).length > 0) {
            payload.content = content;
        }
        if (assignmentDraft.file_url) {
            payload.file_url = assignmentDraft.file_url;
        }
        return payload;
    };

    const handleSaveDraft = async (assignment: Assignment) => {
        try {
            setIsSubmitting(true);
            const latest = getLatestSubmission(assignment.uuid);
            const payload = buildSubmissionPayload(assignment);
            if (latest && latest.status === 'draft') {
                const updated = await updateSubmission(latest.uuid, payload);
                upsertSubmission(updated);
            } else {
                const created = await createSubmission(assignment.uuid, payload);
                upsertSubmission(created);
            }
            toast({ title: 'Draft saved', description: 'Your progress has been saved.' });
        } catch (error) {
            console.error('Failed to save draft:', error);
            toast({
                variant: 'destructive',
                title: 'Error',
                description: 'Failed to save draft.',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleSubmitAssignment = async (assignment: Assignment) => {
        try {
            setIsSubmitting(true);
            const latest = getLatestSubmission(assignment.uuid);
            const payload = buildSubmissionPayload(assignment);

            if (latest && latest.status === 'draft') {
                const updated = await updateSubmission(latest.uuid, payload);
                const submitted = await submitSubmission(updated.uuid);
                upsertSubmission(submitted);
            } else {
                const created = await createSubmission(assignment.uuid, payload);
                const submitted = await submitSubmission(created.uuid);
                upsertSubmission(submitted);
            }

            toast({ title: 'Assignment submitted', description: 'Your submission has been sent for review.' });
        } catch (error: any) {
            console.error('Failed to submit assignment:', error);
            toast({
                variant: 'destructive',
                title: 'Submission failed',
                description: error?.response?.data?.error?.message || 'Could not submit assignment.',
            });
        } finally {
            setIsSubmitting(false);
        }
    };

    const activeContent = currentItem?.type === 'content' ? currentItem.item : null;
    const activeAssignment = currentItem?.type === 'assignment' ? currentItem.item : null;
    const lessonVideoUrl = activeContent?.content_data?.video?.url || activeContent?.content_data?.video_url;

    if (loading) {
        return (
            <div className="flex h-[80vh] items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    if (!course) {
        return (
            <div className="flex h-[80vh] flex-col items-center justify-center gap-4">
                <p className="text-muted-foreground">Course not found</p>
                <Button onClick={() => navigate('/my-courses')}>Back to My Courses</Button>
            </div>
        );
    }

    if (isEnrollmentBlocked) {
        return (
            <div className="flex h-[80vh] flex-col items-center justify-center gap-4 text-center">
                <p className="text-muted-foreground">You are not enrolled in this course yet.</p>
                <div className="flex gap-2">
                    <Button onClick={() => navigate('/my-courses')}>Back to My Courses</Button>
                    {course.slug && (
                        <Button variant="outline" onClick={() => navigate(`/courses/${course.slug}`)}>
                            View Course Page
                        </Button>
                    )}
                </div>
            </div>
        );
    }

    return (
        <div className="flex h-[calc(100vh-4rem)] overflow-hidden">
            {/* Sidebar */}
            <div className="w-80 border-r bg-muted/30 flex flex-col">
                {/* Course Header */}
                <div className="p-4 border-b bg-background">
                    <Button variant="ghost" size="sm" className="mb-2 -ml-2" onClick={() => navigate('/my-courses')}>
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back to Courses
                    </Button>
                    <h1 className="font-semibold text-lg line-clamp-2">{course.title}</h1>
                    <div className="mt-3">
                        <div className="flex justify-between text-sm mb-1">
                            <span className="text-muted-foreground">Progress</span>
                            <span className="font-medium">{progressPercent}%</span>
                        </div>
                        <Progress value={progressPercent} className="h-2" />
                    </div>
                </div>

                {/* Module List */}
                <div className="flex-1 overflow-y-auto">
                    <div className="p-2">
                        {modules.map((mod, modIdx) => {
                            const moduleUuid = mod.module?.uuid || mod.uuid;
                            const moduleTitle = mod.module?.title || `Module ${modIdx + 1}`;
                            const moduleCompleted = mod.contents?.every(c => completedContents.has(c.uuid));

                            return (
                                <div key={moduleUuid} className="mb-2">
                                    <button
                                        onClick={() => toggleModule(moduleUuid)}
                                        className="w-full flex items-center gap-2 p-3 rounded-lg hover:bg-muted transition-colors text-left"
                                    >
                                        <ChevronRight className={`h-4 w-4 transition-transform ${mod.expanded ? 'rotate-90' : ''}`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                {moduleCompleted ? (
                                                    <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                                                ) : (
                                                    <span className="w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-medium shrink-0">
                                                        {modIdx + 1}
                                                    </span>
                                                )}
                                                <span className="font-medium truncate">{moduleTitle}</span>
                                            </div>
                                            <span className="text-xs text-muted-foreground">
                                                {mod.contents?.length || 0} items
                                            </span>
                                        </div>
                                    </button>

                                    {/* Content List */}
                                    {mod.expanded && mod.contents && (
                                        <div className="ml-4 pl-4 border-l">
                                            {mod.contents.map((content) => {
                                                const isActive = currentItem?.type === 'content' && currentItem.item.uuid === content.uuid;
                                                const isCompleted = completedContents.has(content.uuid);

                                                return (
                                                    <button
                                                        key={content.uuid}
                                                        onClick={() => selectContent(content, moduleUuid)}
                                                        className={`w-full flex items-center gap-2 p-2 rounded-md text-left text-sm transition-colors ${isActive
                                                            ? 'bg-primary/10 text-primary'
                                                            : 'hover:bg-muted'
                                                            }`}
                                                    >
                                                        {getContentIcon(content.content_type, isCompleted)}
                                                        <span className="truncate">{content.title}</span>
                                                    </button>
                                                );
                                            })}

                                            {(mod.module?.assignments || []).map((assignment) => {
                                                const isActive = currentItem?.type === 'assignment' && currentItem.item.uuid === assignment.uuid;
                                                const latestSubmission = getLatestSubmission(assignment.uuid);

                                                return (
                                                    <button
                                                        key={assignment.uuid}
                                                        onClick={() => selectAssignment(assignment, moduleUuid)}
                                                        className={`w-full flex items-center gap-2 p-2 rounded-md text-left text-sm transition-colors ${isActive
                                                            ? 'bg-primary/10 text-primary'
                                                            : 'hover:bg-muted'
                                                            }`}
                                                    >
                                                        <ClipboardCheck className="h-4 w-4 text-amber-500" />
                                                        <span className="truncate flex-1">{assignment.title}</span>
                                                        <span className="text-xs text-muted-foreground">
                                                            {latestSubmission?.status_display || latestSubmission?.status || 'Not started'}
                                                        </span>
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {activeContent || activeAssignment ? (
                    <>
                        {/* Content Header */}
                        <div className="p-4 border-b flex items-center justify-between bg-background">
                            <div>
                                <h2 className="text-xl font-semibold">
                                    {activeContent ? activeContent.title : activeAssignment?.title}
                                </h2>
                                <div className="flex items-center gap-2 mt-1">
                                    {activeContent && (
                                        <Badge variant="outline" className="capitalize">{activeContent.content_type}</Badge>
                                    )}
                                    {activeAssignment && (
                                        <Badge variant="outline" className="capitalize">Assignment</Badge>
                                    )}
                                    {activeContent?.duration_minutes && (
                                        <span className="text-sm text-muted-foreground">{activeContent.duration_minutes} min</span>
                                    )}
                                </div>
                            </div>
                            <div className="flex gap-2">
                                {announcements.length > 0 && (
                                    <Button variant="outline" onClick={() => setShowAnnouncements(true)}>
                                        <Info className="mr-2 h-4 w-4" />
                                        Announcements
                                    </Button>
                                )}
                                {activeContent && !completedContents.has(activeContent.uuid) && activeContent.content_type !== 'quiz' && (
                                    <Button onClick={markComplete}>
                                        <CheckCircle2 className="mr-2 h-4 w-4" />
                                        Mark Complete
                                    </Button>
                                )}
                                {activeContent && completedContents.has(activeContent.uuid) && (
                                    <Button variant="outline" onClick={advanceToNext}>
                                        Next
                                        <ChevronRight className="ml-2 h-4 w-4" />
                                    </Button>
                                )}
                            </div>
                        </div>

                        {/* Content Viewer */}
                        <div className="flex-1 overflow-y-auto p-6">
                            <div className="max-w-4xl mx-auto">
                                {activeContent && activeContent.content_type === 'video' && (
                                    <div className="aspect-video bg-black rounded-lg overflow-hidden">
                                        {activeContent.content_data?.video_url ? (
                                            <video
                                                src={activeContent.content_data.video_url}
                                                controls
                                                className="w-full h-full"
                                            />
                                        ) : activeContent.content_data?.youtube_url ? (
                                            <iframe
                                                src={activeContent.content_data.youtube_url.replace('watch?v=', 'embed/')}
                                                className="w-full h-full"
                                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                                allowFullScreen
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-white">
                                                <PlayCircle className="h-16 w-16 opacity-50" />
                                            </div>
                                        )}
                                    </div>
                                )}

                                {activeContent && activeContent.content_type === 'text' && (
                                    <Card>
                                        <CardContent className="pt-6 prose max-w-none">
                                            {activeContent.content_data?.text ? (
                                                <div dangerouslySetInnerHTML={{ __html: activeContent.content_data.text }} />
                                            ) : (
                                                <p className="text-muted-foreground">No content available.</p>
                                            )}
                                        </CardContent>
                                    </Card>
                                )}

                                {activeContent && activeContent.content_type === 'document' && (
                                    <Card>
                                        <CardContent className="pt-6">
                                            {activeContent.file ? (
                                                <div className="space-y-4">
                                                    <iframe
                                                        src={activeContent.file}
                                                        className="w-full h-[600px] border rounded"
                                                    />
                                                    <Button variant="outline" asChild>
                                                        <a href={activeContent.file} target="_blank" rel="noopener noreferrer">
                                                            <ExternalLink className="mr-2 h-4 w-4" />
                                                            Open in New Tab
                                                        </a>
                                                    </Button>
                                                </div>
                                            ) : (
                                                <p className="text-muted-foreground">No document available.</p>
                                            )}
                                        </CardContent>
                                    </Card>
                                )}

                                {activeContent && activeContent.content_type === 'lesson' && (
                                    <Card>
                                        <CardContent className="pt-6 space-y-6">
                                            {lessonVideoUrl && (
                                                <div className="aspect-video bg-black rounded-lg overflow-hidden">
                                                    {lessonVideoUrl.includes('youtube') ? (
                                                        <iframe
                                                            src={lessonVideoUrl.replace('watch?v=', 'embed/')}
                                                            className="w-full h-full"
                                                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                                            allowFullScreen
                                                        />
                                                    ) : (
                                                        <video
                                                            src={lessonVideoUrl}
                                                            controls
                                                            className="w-full h-full"
                                                        />
                                                    )}
                                                </div>
                                            )}
                                            {(activeContent.content_data?.text?.body || activeContent.content_data?.text) && (
                                                <div
                                                    className="prose max-w-none"
                                                    dangerouslySetInnerHTML={{ __html: activeContent.content_data?.text?.body || activeContent.content_data?.text }}
                                                />
                                            )}
                                            {activeContent.file && (
                                                <Button variant="outline" asChild>
                                                    <a href={activeContent.file} target="_blank" rel="noopener noreferrer">
                                                        <ExternalLink className="mr-2 h-4 w-4" />
                                                        Open attachment
                                                    </a>
                                                </Button>
                                            )}
                                        </CardContent>
                                    </Card>
                                )}

                                {activeContent && activeContent.content_type === 'external' && (
                                    <Card>
                                        <CardContent className="pt-6 space-y-2">
                                            <p className="text-muted-foreground">External resource</p>
                                            <Button variant="outline" asChild>
                                                <a href={activeContent.content_data?.url} target="_blank" rel="noopener noreferrer">
                                                    <ExternalLink className="mr-2 h-4 w-4" />
                                                    Open Link
                                                </a>
                                            </Button>
                                        </CardContent>
                                    </Card>
                                )}

                                {activeContent && activeContent.content_type === 'quiz' && (
                                    <QuizContent
                                        key={activeContent.uuid}
                                        content={activeContent}
                                        onComplete={async () => {
                                            await updateContentProgress(activeContent.uuid, { progress_percent: 100, completed: true });
                                            setCompletedContents(prev => new Set([...prev, activeContent.uuid]));
                                        }}
                                    />
                                )}

                                {activeAssignment && (
                                    <AssignmentContent
                                        assignment={activeAssignment}
                                        submission={getLatestSubmission(activeAssignment.uuid)}
                                        badge={getSubmissionBadge(getLatestSubmission(activeAssignment.uuid)?.status)}
                                        isSubmitting={isSubmitting}
                                        draft={assignmentDraft}
                                        onDraftChange={setAssignmentDraft}
                                        onSaveDraft={() => handleSaveDraft(activeAssignment)}
                                        onSubmit={() => handleSubmitAssignment(activeAssignment)}
                                    />
                                )}
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 overflow-y-auto p-6">
                        <div className="max-w-4xl mx-auto">
                            {/* Show sessions for hybrid courses */}
                            {course.format === 'hybrid' && sessions.length > 0 && (
                                <SessionsPanel sessions={sessions} courseTitle={course.title} />
                            )}

                            <div className="text-center py-12">
                                <Award className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
                                <h3 className="text-lg font-medium mb-2">
                                    {sessions.length > 0 ? 'Continue Learning' : 'No content selected'}
                                </h3>
                                <p className="text-muted-foreground">
                                    {sessions.length > 0
                                        ? 'Join a live session above or select a lesson from the sidebar.'
                                        : 'Select a lesson from the sidebar to begin.'}
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <Dialog open={showAnnouncements} onOpenChange={setShowAnnouncements}>
                <DialogContent className="max-w-2xl">
                    <DialogHeader>
                        <DialogTitle>Course Announcements</DialogTitle>
                    </DialogHeader>
                    <div className="space-y-4 max-h-[60vh] overflow-y-auto">
                        {announcements.length === 0 ? (
                            <p className="text-sm text-muted-foreground">No announcements yet.</p>
                        ) : (
                            announcements.map((announcement) => (
                                <Card key={announcement.uuid}>
                                    <CardHeader className="pb-2">
                                        <CardTitle className="text-base">{announcement.title}</CardTitle>
                                        <p className="text-xs text-muted-foreground">
                                            {new Date(announcement.created_at).toLocaleDateString()}
                                            {announcement.created_by_name ? ` • ${announcement.created_by_name}` : ''}
                                        </p>
                                    </CardHeader>
                                    <CardContent className="pt-0 text-sm text-muted-foreground whitespace-pre-wrap">
                                        {announcement.body}
                                    </CardContent>
                                </Card>
                            ))
                        )}
                    </div>
                </DialogContent>
            </Dialog>
        </div>
    );
}

const QuizContent = ({
    content,
    onComplete,
}: {
    content: ContentWithProgress;
    onComplete: () => Promise<void>;
}) => {
    const [answers, setAnswers] = useState<Record<string, string[]>>({});
    const [result, setResult] = useState<{ scorePercent: number; passed: boolean } | null>(null);

    const quizData = content.content_data || {};
    const questions = quizData.questions || [];
    const passingScore = quizData.passing_score ?? 70;

    const handleSingleSelect = (questionId: string, optionId: string) => {
        setAnswers(prev => ({ ...prev, [questionId]: [optionId] }));
    };

    const handleMultipleSelect = (questionId: string, optionId: string) => {
        setAnswers(prev => {
            const existing = prev[questionId] || [];
            if (existing.includes(optionId)) {
                return { ...prev, [questionId]: existing.filter(id => id !== optionId) };
            }
            return { ...prev, [questionId]: [...existing, optionId] };
        });
    };

    const handleSubmit = async () => {
        let totalPoints = 0;
        let earnedPoints = 0;

        questions.forEach((question: any) => {
            const correctOptions = (question.options || []).filter((opt: any) => opt.isCorrect).map((opt: any) => opt.id);
            const selected = answers[question.id] || [];
            totalPoints += question.points || 0;

            const isCorrect =
                correctOptions.length === selected.length &&
                correctOptions.every((id: string) => selected.includes(id));

            if (isCorrect) {
                earnedPoints += question.points || 0;
            }
        });

        const scorePercent = totalPoints > 0 ? Math.round((earnedPoints / totalPoints) * 100) : 0;
        const passed = scorePercent >= passingScore;

        setResult({ scorePercent, passed });
        if (passed) {
            await onComplete();
        }
    };

    return (
        <Card>
            <CardHeader>
                <CardTitle>Quiz</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
                {questions.length === 0 && (
                    <p className="text-muted-foreground">No quiz questions available.</p>
                )}
                {questions.map((question: any, index: number) => (
                    <div key={question.id} className="space-y-3">
                        <div className="flex items-center gap-2">
                            <Badge variant="outline">Q{index + 1}</Badge>
                            <p className="font-medium">{question.text}</p>
                        </div>
                        <div className="space-y-2">
                            {(question.options || []).map((option: any) => (
                                <label key={option.id} className="flex items-center gap-2 text-sm">
                                    <input
                                        type={question.type === 'multiple' ? 'checkbox' : 'radio'}
                                        name={question.id}
                                        checked={(answers[question.id] || []).includes(option.id)}
                                        onChange={() =>
                                            question.type === 'multiple'
                                                ? handleMultipleSelect(question.id, option.id)
                                                : handleSingleSelect(question.id, option.id)
                                        }
                                    />
                                    <span>{option.text}</span>
                                </label>
                            ))}
                        </div>
                    </div>
                ))}

                <div className="flex items-center justify-between">
                    <Button onClick={handleSubmit}>Submit Quiz</Button>
                    {result && (
                        <Badge className={result.passed ? 'bg-green-500' : 'bg-amber-500'}>
                            {result.scorePercent}% {result.passed ? 'Passed' : 'Try again'}
                        </Badge>
                    )}
                </div>
            </CardContent>
        </Card>
    );
};

const AssignmentContent = ({
    assignment,
    submission,
    badge,
    isSubmitting,
    draft,
    onDraftChange,
    onSaveDraft,
    onSubmit,
}: {
    assignment: Assignment;
    submission?: AssignmentSubmission;
    badge: React.ReactNode;
    isSubmitting: boolean;
    draft: { text: string; url: string; file_url: string };
    onDraftChange: (draft: { text: string; url: string; file_url: string }) => void;
    onSaveDraft: () => void;
    onSubmit: () => void;
}) => {
    const canEdit =
        !submission ||
        submission.status === 'draft' ||
        submission.status === 'needs_revision';

    return (
        <Card>
            <CardHeader>
                <div className="flex items-center justify-between">
                    <div>
                        <CardTitle>{assignment.title}</CardTitle>
                        <p className="text-sm text-muted-foreground">{assignment.submission_type_display}</p>
                    </div>
                    {badge}
                </div>
            </CardHeader>
            <CardContent className="space-y-4">
                {assignment.instructions && (
                    <div className="text-sm whitespace-pre-wrap">{assignment.instructions}</div>
                )}

                {submission?.feedback && (
                    <Card className="border-amber-200 bg-amber-50/50">
                        <CardContent className="pt-4 text-sm">
                            <p className="font-medium text-amber-700 mb-1">Instructor Feedback</p>
                            <p className="text-amber-700">{submission.feedback}</p>
                        </CardContent>
                    </Card>
                )}

                {submission?.score !== undefined && submission?.score !== null && (
                    <div className="text-sm text-muted-foreground">
                        Score: <span className="font-medium">{submission.score}</span>
                    </div>
                )}

                {(assignment.submission_type === 'text' || assignment.submission_type === 'mixed' || !assignment.submission_type) && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">Response</p>
                        <textarea
                            className="w-full min-h-[140px] border rounded-md p-3 text-sm"
                            value={draft.text}
                            disabled={!canEdit}
                            onChange={(event) => onDraftChange({ ...draft, text: event.target.value })}
                        />
                    </div>
                )}

                {(assignment.submission_type === 'url' || assignment.submission_type === 'mixed') && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">Reference URL</p>
                        <input
                            className="w-full border rounded-md p-2 text-sm"
                            value={draft.url}
                            disabled={!canEdit}
                            onChange={(event) => onDraftChange({ ...draft, url: event.target.value })}
                        />
                    </div>
                )}

                {(assignment.submission_type === 'file' || assignment.submission_type === 'mixed') && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">File URL</p>
                        <input
                            className="w-full border rounded-md p-2 text-sm"
                            value={draft.file_url}
                            disabled={!canEdit}
                            onChange={(event) => onDraftChange({ ...draft, file_url: event.target.value })}
                        />
                        <p className="text-xs text-muted-foreground">Paste a shareable file link.</p>
                    </div>
                )}

                <div className="flex gap-2">
                    <Button variant="outline" onClick={onSaveDraft} disabled={!canEdit || isSubmitting}>
                        Save Draft
                    </Button>
                    <Button onClick={onSubmit} disabled={!canEdit || isSubmitting}>
                        Submit Assignment
                    </Button>
                </div>
            </CardContent>
        </Card>
    );
};

export default CoursePlayerPage;
