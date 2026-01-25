import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
    getCourse,
    getCourseBySlug,
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
import { Input } from '@/components/ui/input';
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
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
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
    Link as LinkIcon,
    ClipboardCheck,
    Info,
    BookOpen,
    Calendar,
    Clock,
    AlertCircle,
} from 'lucide-react';
import { NotebookRenderer } from '@/components/courses/NotebookRenderer';

interface ModuleContent {
    uuid: string;
    title: string;
    content_type: 'text' | 'video' | 'document' | 'quiz' | 'lesson' | 'external' | 'notebook';
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
    | { type: 'assignment'; item: Assignment; moduleUuid: string }
    | { type: 'session'; item: CourseSession; moduleUuid: null };

export function CoursePlayerPage() {
    const { courseUuid, courseSlug } = useParams<{ courseUuid?: string; courseSlug?: string }>();
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
            if (!courseUuid && !courseSlug) return;

            setIsEnrollmentBlocked(false);
            setCompletedContents(new Set());
            setSubmissions([]);
            setAnnouncements([]);
            try {
                let courseData: Course;
                let effectiveUuid = courseUuid;

                // Fetch course details by UUID or Slug
                if (courseUuid) {
                    courseData = await getCourse(courseUuid);
                } else if (courseSlug) {
                    const resolvedCourse = await getCourseBySlug(courseSlug);
                    if (!resolvedCourse) throw new Error('Course not found');
                    courseData = resolvedCourse;
                    effectiveUuid = resolvedCourse.uuid;
                } else {
                    return;
                }

                if (!effectiveUuid) throw new Error('Invalid course data');

                setCourse(courseData);

                // Fetch modules
                const modulesData = await getCourseModules(effectiveUuid);

                // Fetch contents for each module
                const modulesWithContents = await Promise.all(
                    modulesData.map(async (mod) => {
                        const moduleUuid = mod.module?.uuid || mod.uuid;
                        try {
                            const contents = await getModuleContents(effectiveUuid!, moduleUuid);
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
                    const courseAnnouncements = await getCourseAnnouncements(effectiveUuid);
                    setAnnouncements(courseAnnouncements);
                } catch (error) {
                    console.error('Failed to load announcements:', error);
                }

                // Load sessions for hybrid courses
                if (courseData.format === 'hybrid') {
                    try {
                        const courseSessions = await getCourseSessions(effectiveUuid);
                        setSessions(courseSessions.filter((s: CourseSession) => s.is_published));
                    } catch (error) {
                        console.error('Failed to load sessions:', error);
                    }
                }

                // Pull progress to restore completed items
                try {
                    const progress = await getCourseProgress(effectiveUuid);
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
    }, [courseUuid, courseSlug, toast]);

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

    const selectSession = (session: CourseSession) => {
        setCurrentItem({ type: 'session', item: session, moduleUuid: null });
        setCurrentModuleUuid(null);
    };

    // Mark content as complete
    const markComplete = async () => {
        if (!course || !currentItem || currentItem.type !== 'content' || isSubmitting) return;

        setIsSubmitting(true);
        try {
            await updateContentProgress(currentItem.item.uuid, { progress_percent: 100, completed: true });

            // Update local state immediately
            const newItemUuid = currentItem.item.uuid;
            setCompletedContents(prev => new Set([...prev, newItemUuid]));

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
        } finally {
            setIsSubmitting(false);
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
            case 'notebook': return <BookOpen className="h-4 w-4 text-purple-600" />;
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
    const activeSession = currentItem?.type === 'session' ? currentItem.item : null;
    const videoUrl = activeContent?.content_data?.video?.url || 
                     activeContent?.content_data?.video_url || 
                     activeContent?.content_data?.youtube_url || 
                     activeContent?.content_data?.url;

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
                        {/* Live Sessions Section - Only for hybrid courses */}
                        {course.format === 'hybrid' && sessions.length > 0 && (() => {
                            // Sort sessions: live first, then upcoming, then past
                            const now = new Date();
                            const sortedSessions = [...sessions].sort((a, b) => {
                                const startA = new Date(a.starts_at);
                                const startB = new Date(b.starts_at);
                                const endA = new Date(startA.getTime() + a.duration_minutes * 60000);
                                const endB = new Date(startB.getTime() + b.duration_minutes * 60000);
                                
                                const isLiveA = now >= startA && now <= endA;
                                const isLiveB = now >= startB && now <= endB;
                                const isPastA = now > endA;
                                const isPastB = now > endB;
                                
                                // Live first
                                if (isLiveA && !isLiveB) return -1;
                                if (!isLiveA && isLiveB) return 1;
                                
                                // Then upcoming (sort by start time)
                                if (!isPastA && !isPastB) return startA.getTime() - startB.getTime();
                                
                                // Then past (sort by most recent first)
                                if (isPastA && isPastB) return startB.getTime() - startA.getTime();
                                
                                // Upcoming before past
                                if (!isPastA && isPastB) return -1;
                                if (isPastA && !isPastB) return 1;
                                
                                return 0;
                            });

                            // Find index where past sessions start
                            const firstPastIndex = sortedSessions.findIndex(session => {
                                const start = new Date(session.starts_at);
                                const end = new Date(start.getTime() + session.duration_minutes * 60000);
                                return now > end;
                            });

                            return (
                                <div className="mb-4">
                                    <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                        Live Sessions
                                    </div>
                                    <div className="space-y-1">
                                        {sortedSessions.map((session, index) => {
                                            const isActive = currentItem?.type === 'session' && currentItem.item.uuid === session.uuid;
                                            const start = new Date(session.starts_at);
                                            const end = new Date(start.getTime() + session.duration_minutes * 60000);
                                            const isLive = now >= start && now <= end;
                                            const isPast = now > end;
                                            const showDivider = index === firstPastIndex && firstPastIndex > 0;

                                            return (
                                                <React.Fragment key={session.uuid}>
                                                    {showDivider && (
                                                        <div className="flex items-center gap-2 py-2 px-1">
                                                            <Separator className="flex-1" />
                                                            <span className="text-xs text-muted-foreground">Past</span>
                                                            <Separator className="flex-1" />
                                                        </div>
                                                    )}
                                                    <button
                                                        onClick={() => selectSession(session)}
                                                        className={`w-full flex items-center gap-2 p-3 rounded-lg text-left transition-colors ${
                                                            isActive
                                                                ? 'bg-primary/10 text-primary'
                                                                : isPast
                                                                ? 'hover:bg-muted/50 opacity-75'
                                                                : 'hover:bg-muted'
                                                        }`}
                                                    >
                                                        <Video className={`h-4 w-4 shrink-0 ${
                                                            isLive ? 'text-red-500' : isPast ? 'text-muted-foreground' : 'text-blue-500'
                                                        }`} />
                                                        <div className="flex-1 min-w-0">
                                                            <div className="font-medium text-sm truncate">{session.title}</div>
                                                            <div className="text-xs text-muted-foreground">
                                                                {start.toLocaleDateString(undefined, {
                                                                    month: 'short',
                                                                    day: 'numeric',
                                                                })}
                                                                {' • '}
                                                                {session.duration_minutes} min
                                                            </div>
                                                        </div>
                                                        {isLive && (
                                                            <span className="flex items-center gap-1 text-xs text-red-500 shrink-0">
                                                                <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
                                                                Live
                                                            </span>
                                                        )}
                                                    </button>
                                                </React.Fragment>
                                            );
                                        })}
                                    </div>
                                    <Separator className="my-4" />
                                </div>
                            );
                        })()}

                        {/* Course Modules */}
                        {modules.length > 0 && (
                            <div className="px-3 py-2 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                                Course Content
                            </div>
                        )}
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
                {activeContent || activeAssignment || activeSession ? (
                    <>
                        {/* Content Header */}
                        <div className="p-4 border-b flex items-center justify-between bg-background">
                            <div>
                                <h2 className="text-xl font-semibold">
                                    {activeContent ? activeContent.title : activeAssignment ? activeAssignment.title : activeSession?.title}
                                </h2>
                                <div className="flex items-center gap-2 mt-1">
                                    {activeContent && (
                                        <Badge variant="outline" className="capitalize">{activeContent.content_type}</Badge>
                                    )}
                                    {activeAssignment && (
                                        <Badge variant="outline" className="capitalize">Assignment</Badge>
                                    )}
                                    {activeSession && (
                                        <Badge variant="outline" className="capitalize">Live Session</Badge>
                                    )}
                                    {activeContent?.duration_minutes && (
                                        <span className="text-sm text-muted-foreground">{activeContent.duration_minutes} min</span>
                                    )}
                                    {activeSession?.duration_minutes && (
                                        <span className="text-sm text-muted-foreground">{activeSession.duration_minutes} min</span>
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
                                    <Button onClick={markComplete} disabled={isSubmitting}>
                                        {isSubmitting ? (
                                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        ) : (
                                            <CheckCircle2 className="mr-2 h-4 w-4" />
                                        )}
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
                                        {videoUrl ? (
                                            (videoUrl.includes('youtube') || videoUrl.includes('vimeo')) ? (
                                                <iframe
                                                    src={videoUrl.replace('watch?v=', 'embed/')}
                                                    className="w-full h-full"
                                                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                                    allowFullScreen
                                                />
                                            ) : (
                                                <video
                                                    src={videoUrl}
                                                    controls
                                                    className="w-full h-full"
                                                />
                                            )
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
                                            {(activeContent.content_data?.text?.body || activeContent.content_data?.text) ? (
                                                <div dangerouslySetInnerHTML={{ __html: activeContent.content_data?.text?.body || activeContent.content_data?.text }} />
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
                                            {activeContent.content_data?.video?.url && (
                                                <div className="aspect-video bg-black rounded-lg overflow-hidden">
                                                    {activeContent.content_data.video.url.includes('youtube') ? (
                                                        <iframe
                                                            src={activeContent.content_data.video.url.replace('watch?v=', 'embed/')}
                                                            className="w-full h-full"
                                                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                                            allowFullScreen
                                                        />
                                                    ) : (
                                                        <video
                                                            src={activeContent.content_data.video.url}
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

                                {activeContent && activeContent.content_type === 'notebook' && (
                                    <NotebookRenderer
                                        fileUrl={activeContent.file || ''}
                                        metadata={activeContent.content_data || {}}
                                    />
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

                                {activeSession && (
                                    <SessionViewer session={activeSession} />
                                )}
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="flex-1 overflow-y-auto p-6">
                        <div className="max-w-4xl mx-auto">
                            <div className="text-center py-12">
                                <Award className="h-16 w-16 mx-auto text-muted-foreground/50 mb-4" />
                                <h3 className="text-lg font-medium mb-2">Welcome to {course.title}</h3>
                                <p className="text-muted-foreground mb-6">
                                    {course.format === 'hybrid' 
                                        ? 'Select a live session or lesson from the sidebar to begin your learning journey.'
                                        : 'Select a lesson from the sidebar to begin.'}
                                </p>
                                
                                {course.format === 'hybrid' && (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8 text-left">
                                        <Card>
                                            <CardHeader>
                                                <CardTitle className="text-base flex items-center gap-2">
                                                    <Video className="h-5 w-5 text-blue-500" />
                                                    Live Sessions
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <p className="text-sm text-muted-foreground">
                                                    {sessions.length} interactive live session{sessions.length !== 1 ? 's' : ''} with real-time Q&A and collaboration.
                                                </p>
                                            </CardContent>
                                        </Card>
                                        <Card>
                                            <CardHeader>
                                                <CardTitle className="text-base flex items-center gap-2">
                                                    <BookOpen className="h-5 w-5 text-green-500" />
                                                    Self-Paced Content
                                                </CardTitle>
                                            </CardHeader>
                                            <CardContent>
                                                <p className="text-sm text-muted-foreground">
                                                    {totalContents} lesson{totalContents !== 1 ? 's' : ''} you can complete at your own pace, anytime.
                                                </p>
                                            </CardContent>
                                        </Card>
                                    </div>
                                )}
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
    const maxAttempts = quizData.max_attempts != null ? quizData.max_attempts : 3;

    // Check if quiz can be submitted
    const hasRemainingAttempts = attemptHistory?.remaining_attempts == null || attemptHistory.remaining_attempts > 0;
    const hasNotUsedAllAttempts = !result || result.passed || (maxAttempts != null && result.attempt_number < maxAttempts);
    const canSubmitQuiz = hasRemainingAttempts && hasNotUsedAllAttempts;

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
                                            className="h-4 w-4 border-input bg-background text-primary focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50"
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
                        disabled={isSubmitting || (result?.passed ?? false) || !canSubmitQuiz}
                    >
                        {isSubmitting ? (
                            <>
                                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                Submitting...
                            </>
                        ) : !canSubmitQuiz ? (
                            'No Attempts Remaining'
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

// Quill editor configuration for assignment rich text
const quillModules = {
    toolbar: [
        [{ 'header': [1, 2, 3, false] }],
        ['bold', 'italic', 'underline', 'strike', 'blockquote'],
        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
        ['link', 'clean']
    ],
};

const quillFormats = [
    'header',
    'bold', 'italic', 'underline', 'strike', 'blockquote',
    'list', 'bullet',
    'link'
];

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

                {submission?.score !== undefined && submission?.score !== null && (
                    <div className="flex items-center gap-2 text-sm">
                        <Badge variant="outline" className="text-base">
                            Score: {submission.score}
                        </Badge>
                        {submission.status && (
                            <Badge variant={
                                submission.status === 'graded' ? 'default' : 
                                submission.status === 'needs_revision' ? 'destructive' : 
                                'secondary'
                            }>
                                {submission.status === 'graded' ? 'Graded' : 
                                 submission.status === 'needs_revision' ? 'Needs Revision' : 
                                 submission.status === 'submitted' ? 'Submitted' : 'Draft'}
                            </Badge>
                        )}
                    </div>
                )}

                {submission?.feedback && submission.feedback.trim() && (
                    <Card className="border-info bg-info-subtle">
                        <CardContent className="pt-4 text-sm">
                            <p className="font-medium text-info mb-2">Instructor Feedback</p>
                            <div className="text-foreground whitespace-pre-wrap">{submission.feedback}</div>
                        </CardContent>
                    </Card>
                )}

                {(assignment.submission_type === 'text' || assignment.submission_type === 'mixed' || !assignment.submission_type) && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">Response</p>
                        <ReactQuill
                            theme="snow"
                            value={draft.text}
                            onChange={(value) => onDraftChange({ ...draft, text: value })}
                            modules={quillModules}
                            formats={quillFormats}
                            readOnly={!canEdit}
                            className="bg-background"
                        />
                    </div>
                )}

                {(assignment.submission_type === 'url' || assignment.submission_type === 'mixed') && (
                    <div className="space-y-2">
                        <p className="text-sm font-medium">Reference URL</p>
                        <div className="relative">
                            <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                type="url"
                                placeholder="https://example.com"
                                className="pl-9"
                                value={draft.url}
                                disabled={!canEdit}
                                onChange={(event) => onDraftChange({ ...draft, url: event.target.value })}
                            />
                        </div>
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
                            <Input
                                type="url"
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

const SessionViewer = ({ session }: { session: CourseSession }) => {
    const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString(undefined, {
            weekday: 'long',
            month: 'long',
            day: 'numeric',
            year: 'numeric',
        });
    };

    const formatTime = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleTimeString(undefined, {
            hour: '2-digit',
            minute: '2-digit',
            timeZoneName: 'short',
        });
    };

    const getSessionStatus = () => {
        const now = new Date();
        const start = new Date(session.starts_at);
        const end = session.ends_at 
            ? new Date(session.ends_at) 
            : new Date(start.getTime() + (session.duration_minutes || 60) * 60000);

        if (now < start) {
            const diffMs = start.getTime() - now.getTime();
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            const diffDays = Math.floor(diffHours / 24);

            if (diffDays > 0) {
                return { status: 'upcoming', label: `Starts in ${diffDays} day${diffDays > 1 ? 's' : ''}`, color: 'blue' };
            } else if (diffHours > 0) {
                return { status: 'upcoming', label: `Starts in ${diffHours} hour${diffHours > 1 ? 's' : ''}`, color: 'blue' };
            } else {
                const diffMins = Math.floor(diffMs / (1000 * 60));
                return { status: 'upcoming', label: `Starting in ${diffMins} minute${diffMins > 1 ? 's' : ''}`, color: 'orange' };
            }
        } else if (now >= start && now <= end) {
            return { status: 'live', label: 'Live Now', color: 'red' };
        } else {
            return { status: 'past', label: 'Session Ended', color: 'gray' };
        }
    };

    const { status, label, color } = getSessionStatus();
    const canJoin = (status === 'live' || status === 'upcoming') && session.zoom_join_url;

    return (
        <Card>
            <CardHeader>
                <div className="flex items-start justify-between">
                    <div className="space-y-1">
                        <CardTitle className="text-2xl">{session.title}</CardTitle>
                        <div className="flex items-center gap-2">
                            <Badge 
                                variant={status === 'live' ? 'default' : 'outline'}
                                className={
                                    status === 'live' 
                                        ? 'bg-red-500 text-white animate-pulse' 
                                        : status === 'upcoming'
                                        ? 'text-blue-600 border-blue-300'
                                        : 'text-muted-foreground'
                                }
                            >
                                {status === 'live' && <span className="mr-1">●</span>}
                                {label}
                            </Badge>
                            {session.is_mandatory && (
                                <Badge variant="outline" className="text-orange-600 border-orange-300">
                                    Required
                                </Badge>
                            )}
                        </div>
                    </div>
                    {canJoin && (
                        <Button 
                            size="lg"
                            variant={status === 'live' ? 'default' : 'outline'}
                            asChild
                        >
                            <a
                                href={session.zoom_join_url}
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <ExternalLink className="mr-2 h-5 w-5" />
                                {status === 'live' ? 'Join Now' : 'Join Session'}
                            </a>
                        </Button>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-6">
                {session.description && (
                    <div>
                        <h3 className="font-medium mb-2">About This Session</h3>
                        <p className="text-muted-foreground whitespace-pre-wrap">{session.description}</p>
                    </div>
                )}

                <Separator />

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="space-y-3">
                        <div className="flex items-start gap-3">
                            <Calendar className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="text-sm font-medium">Date</p>
                                <p className="text-sm text-muted-foreground">{formatDate(session.starts_at)}</p>
                            </div>
                        </div>
                        <div className="flex items-start gap-3">
                            <Clock className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="text-sm font-medium">Time</p>
                                <p className="text-sm text-muted-foreground">
                                    {formatTime(session.starts_at)}
                                </p>
                            </div>
                        </div>
                    </div>

                    <div className="space-y-3">
                        <div className="flex items-start gap-3">
                            <Video className="h-5 w-5 text-muted-foreground mt-0.5" />
                            <div>
                                <p className="text-sm font-medium">Duration</p>
                                <p className="text-sm text-muted-foreground">{session.duration_minutes} minutes</p>
                            </div>
                        </div>
                        {session.cpd_credits && Number(session.cpd_credits) > 0 && (
                            <div className="flex items-start gap-3">
                                <CheckCircle2 className="h-5 w-5 text-muted-foreground mt-0.5" />
                                <div>
                                    <p className="text-sm font-medium">CPD Credits</p>
                                    <p className="text-sm text-muted-foreground">{session.cpd_credits} credits</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {session.minimum_attendance_percent > 0 && (
                    <>
                        <Separator />
                        <div className="flex items-start gap-3 p-4 bg-muted/50 rounded-lg">
                            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
                            <div>
                                <p className="text-sm font-medium">Attendance Requirement</p>
                                <p className="text-sm text-muted-foreground">
                                    You must attend at least {session.minimum_attendance_percent}% of this session to receive credit.
                                </p>
                            </div>
                        </div>
                    </>
                )}

                {session.zoom_error && (
                    <>
                        <Separator />
                        <div className="flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-lg">
                            <AlertCircle className="h-5 w-5 text-red-600 mt-0.5" />
                            <div>
                                <p className="text-sm font-medium text-red-900">Zoom Meeting Error</p>
                                <p className="text-sm text-red-700">{session.zoom_error}</p>
                            </div>
                        </div>
                    </>
                )}

                {status === 'past' && !session.zoom_error && (
                    <div className="text-center py-8 text-muted-foreground">
                        <p>This session has ended. Check back later for recordings or materials.</p>
                    </div>
                )}
            </CardContent>
        </Card>
    );
};

export default CoursePlayerPage;
