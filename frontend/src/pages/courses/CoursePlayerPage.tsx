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
import { updateContentProgress, submitQuiz, getQuizAttempts } from '@/api/learning';
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
    ChevronDown,
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
    const [assignmentFile, setAssignmentFile] = useState<File | null>(null);
    const [uploadProgress, setUploadProgress] = useState(0);
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
        if (completed) return <CheckCircle2 className="h-4 w-4 text-success" />;

        switch (type) {
            case 'video': return <Video className="h-4 w-4 text-info" />;
            case 'text': return <FileText className="h-4 w-4 text-warning" />;
            case 'document': return <File className="h-4 w-4 text-primary" />;
            case 'lesson': return <FileText className="h-4 w-4 text-success" />;
            case 'external': return <ExternalLink className="h-4 w-4 text-info" />;
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
                return <Badge className="bg-info">Submitted</Badge>;
            case 'in_review':
                return <Badge className="bg-warning">In Review</Badge>;
            case 'needs_revision':
                return <Badge variant="destructive">Needs Revision</Badge>;
            case 'graded':
                return <Badge className="bg-success">Graded</Badge>;
            case 'approved':
                return <Badge className="bg-success">Approved</Badge>;
            case 'draft':
                return <Badge variant="secondary">Draft</Badge>;
            default:
                return <Badge variant="outline">Not Submitted</Badge>;
        }
    };

    const buildSubmissionPayload = (assignment: Assignment): FormData | { content?: Record<string, any>; file_url?: string } => {
        const submissionType = assignment.submission_type || 'text';
        const hasFile = assignmentFile !== null;

        // If there's a file, use FormData
        if (hasFile || submissionType === 'file') {
            const formData = new FormData();
            formData.append('assignment', assignment.uuid);
            
            if (assignmentFile) {
                formData.append('submission_file', assignmentFile);
            }
            
            if (submissionType === 'text' || submissionType === 'mixed') {
                if (assignmentDraft.text) {
                    formData.append('content', JSON.stringify({ text: assignmentDraft.text }));
                }
            }
            
            if (submissionType === 'url' || submissionType === 'mixed') {
                if (assignmentDraft.url) {
                    const content = JSON.parse(formData.get('content') as string || '{}');
                    content.url = assignmentDraft.url;
                    formData.set('content', JSON.stringify(content));
                }
            }
            
            // Keep file_url for backwards compatibility
            if (assignmentDraft.file_url) {
                formData.append('file_url', assignmentDraft.file_url);
            }
            
            return formData;
        }

        // Otherwise use JSON payload (no file)
        const content: Record<string, any> = {};

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
                                                    <CheckCircle2 className="h-4 w-4 text-success shrink-0" />
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
                                                        <ClipboardCheck className="h-4 w-4 text-warning" />
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
                                        file={assignmentFile}
                                        onDraftChange={setAssignmentDraft}
                                        onFileChange={setAssignmentFile}
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
    const { toast } = useToast();
    const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
    const [result, setResult] = useState<{ score: number; passed: boolean; attempt_number: number } | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [startTime] = useState(Date.now());
    const [attemptHistory, setAttemptHistory] = useState<any>(null);
    const [showHistory, setShowHistory] = useState(false);

    const quizData = content.content_data || {};
    const questions = quizData.questions || [];
    const passingScore = quizData.passing_score ?? 70;
    const maxAttempts = quizData.max_attempts ?? 3;

    useEffect(() => {
        loadAttemptHistory();
    }, [content.uuid]);

    const loadAttemptHistory = async () => {
        try {
            const history = await getQuizAttempts(content.uuid);
            setAttemptHistory(history);
            
            // If there's a passed attempt, set result from the last attempt
            if (history.attempts.length > 0) {
                const lastAttempt = history.attempts[0];
                if (lastAttempt.passed) {
                    setResult({
                        score: lastAttempt.score,
                        passed: lastAttempt.passed,
                        attempt_number: lastAttempt.attempt_number,
                    });
                }
            }
        } catch (error) {
            console.error('Failed to load quiz attempt history:', error);
        }
    };

    const handleSingleSelect = (questionId: string, optionId: string) => {
        setAnswers(prev => ({ ...prev, [questionId]: optionId }));
    };

    const handleMultipleSelect = (questionId: string, optionId: string) => {
        setAnswers(prev => {
            const existing = Array.isArray(prev[questionId]) ? prev[questionId] as string[] : [];
            if (existing.includes(optionId)) {
                return { ...prev, [questionId]: existing.filter(id => id !== optionId) };
            }
            return { ...prev, [questionId]: [...existing, optionId] };
        });
    };

    const handleSubmit = async () => {
        // Validate all questions are answered
        const unansweredQuestions = questions.filter((q: any) => !answers[q.id] || 
            (Array.isArray(answers[q.id]) && (answers[q.id] as string[]).length === 0)
        );
        
        if (unansweredQuestions.length > 0) {
            toast({
                title: 'Incomplete Quiz',
                description: `Please answer all questions before submitting. ${unansweredQuestions.length} question(s) remaining.`,
                variant: 'destructive',
            });
            return;
        }

        setIsSubmitting(true);

        try {
            // Calculate time spent in seconds
            const timeSpentSeconds = Math.floor((Date.now() - startTime) / 1000);

            // Submit quiz to backend API
            const result = await submitQuiz({
                content_uuid: content.uuid,
                submitted_answers: answers,
                time_spent_seconds: timeSpentSeconds,
            });

            setResult({
                score: result.score,
                passed: result.passed,
                attempt_number: result.attempt_number,
            });

            toast({
                title: result.passed ? 'Quiz Passed!' : 'Quiz Failed',
                description: result.passed 
                    ? `Congratulations! You scored ${result.score}% and passed the quiz.`
                    : `You scored ${result.score}%. You need ${passingScore}% to pass. ${maxAttempts - result.attempt_number} attempt(s) remaining.`,
                variant: result.passed ? 'default' : 'destructive',
            });

            // If passed, mark as complete and trigger onComplete
            if (result.passed) {
                await onComplete();
            }

            // Reload attempt history
            await loadAttemptHistory();
        } catch (error: any) {
            console.error('Quiz submission error:', error);
            toast({
                title: 'Submission Failed',
                description: error.response?.data?.error || 'Failed to submit quiz. Please try again.',
                variant: 'destructive',
            });
        } finally {
            setIsSubmitting(false);
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
                            {(question.options || []).map((option: any) => {
                                const isChecked = question.type === 'multiple'
                                    ? Array.isArray(answers[question.id]) && (answers[question.id] as string[]).includes(option.id)
                                    : answers[question.id] === option.id;
                                
                                return (
                                    <label key={option.id} className="flex items-center gap-2 text-sm cursor-pointer">
                                        <input
                                            type={question.type === 'multiple' ? 'checkbox' : 'radio'}
                                            name={question.id}
                                            checked={isChecked}
                                            onChange={() =>
                                                question.type === 'multiple'
                                                    ? handleMultipleSelect(question.id, option.id)
                                                    : handleSingleSelect(question.id, option.id)
                                            }
                                            disabled={isSubmitting || (result?.passed ?? false)}
                                        />
                                        <span>{option.text}</span>
                                    </label>
                                );
                            })}
                        </div>
                    </div>
                ))}

                <div className="flex items-center justify-between">
                    <Button 
                        onClick={handleSubmit} 
                        disabled={isSubmitting || (result?.passed ?? false)}
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : (
                            'Submit Quiz'
                        )}
                    </Button>
                    {result && (
                        <div className="flex items-center gap-2">
                            <Badge variant={result.passed ? 'default' : 'destructive'}>
                                {result.score}% {result.passed ? 'Passed' : 'Failed'}
                            </Badge>
                            <span className="text-sm text-muted-foreground">
                                Attempt {result.attempt_number}/{maxAttempts}
                            </span>
                        </div>
                    )}
                </div>

                {attemptHistory && attemptHistory.attempts.length > 0 && (
                    <div className="border-t pt-4">
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setShowHistory(!showHistory)}
                            className="w-full justify-between"
                        >
                            <span className="text-sm font-medium">
                                Attempt History ({attemptHistory.total_attempts})
                            </span>
                            <ChevronDown
                                className={`h-4 w-4 transition-transform ${showHistory ? 'rotate-180' : ''}`}
                            />
                        </Button>

                        {showHistory && (
                            <div className="mt-4 space-y-2">
                                {attemptHistory.attempts.map((attempt: any, index: number) => (
                                    <div
                                        key={attempt.uuid}
                                        className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                                    >
                                        <div className="flex items-center gap-3">
                                            <Badge variant={attempt.passed ? 'default' : 'secondary'}>
                                                #{attempt.attempt_number}
                                            </Badge>
                                            <div>
                                                <p className="text-sm font-medium">
                                                    {attempt.score}% {attempt.passed ? '✓ Passed' : '✗ Failed'}
                                                </p>
                                                <p className="text-xs text-muted-foreground">
                                                    {new Date(attempt.created_at).toLocaleDateString()} at{' '}
                                                    {new Date(attempt.created_at).toLocaleTimeString()}
                                                </p>
                                            </div>
                                        </div>
                                        <div className="text-right text-xs text-muted-foreground">
                                            {Math.floor(attempt.time_spent_seconds / 60)}m {attempt.time_spent_seconds % 60}s
                                        </div>
                                    </div>
                                ))}
                                {attemptHistory.remaining_attempts !== null && (
                                    <p className="text-xs text-muted-foreground text-center pt-2">
                                        {attemptHistory.remaining_attempts} attempt(s) remaining
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                )}
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
    file,
    onDraftChange,
    onFileChange,
    onSaveDraft,
    onSubmit,
}: {
    assignment: Assignment;
    submission?: AssignmentSubmission;
    badge: React.ReactNode;
    isSubmitting: boolean;
    draft: { text: string; url: string; file_url: string };
    file: File | null;
    onDraftChange: (draft: { text: string; url: string; file_url: string }) => void;
    onFileChange: (file: File | null) => void;
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
                    <Card className="border-warning bg-warning-subtle">
                        <CardContent className="pt-4 text-sm">
                            <p className="font-medium text-warning mb-1">Instructor Feedback</p>
                            <p className="text-warning">{submission.feedback}</p>
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
                        <p className="text-sm font-medium">Upload File</p>
                        <div className="space-y-2">
                            <input
                                type="file"
                                id="assignment-file-upload"
                                className="hidden"
                                disabled={!canEdit}
                                accept=".pdf,.doc,.docx,.txt,.zip,.jpg,.jpeg,.png,.gif"
                                onChange={(e) => {
                                    const selectedFile = e.target.files?.[0] || null;
                                    onFileChange(selectedFile);
                                }}
                            />
                            <label
                                htmlFor="assignment-file-upload"
                                className={`flex items-center justify-center gap-2 w-full border-2 border-dashed rounded-md p-4 cursor-pointer hover:bg-muted/50 transition ${
                                    !canEdit ? 'opacity-50 cursor-not-allowed' : ''
                                }`}
                            >
                                <File className="h-5 w-5 text-muted-foreground" />
                                <span className="text-sm text-muted-foreground">
                                    {file ? file.name : 'Click to select file or drag and drop'}
                                </span>
                            </label>
                            {file && (
                                <div className="flex items-center justify-between p-2 bg-muted rounded">
                                    <div className="flex items-center gap-2">
                                        <File className="h-4 w-4" />
                                        <div>
                                            <p className="text-sm font-medium">{file.name}</p>
                                            <p className="text-xs text-muted-foreground">
                                                {(file.size / 1024 / 1024).toFixed(2)} MB
                                            </p>
                                        </div>
                                    </div>
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => onFileChange(null)}
                                        disabled={!canEdit}
                                    >
                                        Remove
                                    </Button>
                                </div>
                            )}
                            <p className="text-xs text-muted-foreground">
                                Accepted: PDF, Word, Text, ZIP, Images. Max size: 50MB
                            </p>
                        </div>
                        
                        {/* Keep URL option for backwards compatibility */}
                        <div className="pt-2">
                            <p className="text-xs font-medium text-muted-foreground mb-1">Or paste a file URL (optional)</p>
                            <input
                                className="w-full border rounded-md p-2 text-sm"
                                placeholder="https://drive.google.com/..."
                                value={draft.file_url}
                                disabled={!canEdit}
                                onChange={(event) => onDraftChange({ ...draft, file_url: event.target.value })}
                            />
                        </div>
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
