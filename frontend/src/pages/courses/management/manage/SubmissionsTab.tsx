import React, { useEffect, useMemo, useState } from "react";
import { format } from "date-fns";
import { ClipboardCheck, Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { AssignmentSubmissionStaff } from "@/api/courses/types";
import { getCourseSubmissions, gradeCourseSubmission } from "@/api/courses";

interface SubmissionsTabProps {
    courseUuid: string;
}

const STATUS_OPTIONS = ["all", "draft", "submitted", "in_review", "needs_revision", "graded", "approved"];

export function SubmissionsTab({ courseUuid }: SubmissionsTabProps) {
    const [submissions, setSubmissions] = useState<AssignmentSubmissionStaff[]>([]);
    const [loading, setLoading] = useState(true);
    const [searchTerm, setSearchTerm] = useState("");
    const [statusFilter, setStatusFilter] = useState("all");
    const [selectedSubmission, setSelectedSubmission] = useState<AssignmentSubmissionStaff | null>(null);
    const [scoreInput, setScoreInput] = useState("");
    const [feedbackInput, setFeedbackInput] = useState("");
    const [action, setAction] = useState<"grade" | "return" | "approve">("grade");
    const [saving, setSaving] = useState(false);

    useEffect(() => {
        const loadSubmissions = async () => {
            setLoading(true);
            try {
                const data = await getCourseSubmissions(courseUuid);
                setSubmissions(data);
            } catch (error) {
                console.error(error);
                toast.error("Failed to load submissions");
            } finally {
                setLoading(false);
            }
        };

        loadSubmissions();
    }, [courseUuid]);

    const filteredSubmissions = useMemo(() => {
        return submissions.filter((submission) => {
            const searchTarget = `${submission.assignment_title || ""} ${submission.user_name || ""} ${submission.user_email || ""}`.toLowerCase();
            const matchesSearch = searchTarget.includes(searchTerm.toLowerCase());
            const matchesStatus = statusFilter === "all" || submission.status === statusFilter;
            return matchesSearch && matchesStatus;
        });
    }, [submissions, searchTerm, statusFilter]);

    const getStatusBadge = (status: string, label?: string) => {
        const display = label || status.replace(/_/g, " ");
        switch (status) {
            case "submitted":
                return <Badge className="bg-blue-500 capitalize">{display}</Badge>;
            case "needs_revision":
                return <Badge className="bg-amber-500 capitalize">{display}</Badge>;
            case "graded":
            case "approved":
                return <Badge className="bg-green-500 capitalize">{display}</Badge>;
            default:
                return <Badge variant="secondary" className="capitalize">{display}</Badge>;
        }
    };

    const openReviewDialog = (submission: AssignmentSubmissionStaff) => {
        setSelectedSubmission(submission);
        setScoreInput(submission.score !== undefined && submission.score !== null ? String(submission.score) : "");
        setFeedbackInput(submission.feedback || "");
        setAction("grade");
    };

    const handleSaveReview = async () => {
        if (!selectedSubmission) return;
        const parsedScore = Number(scoreInput);
        if (Number.isNaN(parsedScore) || parsedScore < 0) {
            toast.error("Provide a valid score");
            return;
        }

        setSaving(true);
        try {
            const updated = await gradeCourseSubmission(courseUuid, selectedSubmission.uuid, {
                score: parsedScore,
                feedback: feedbackInput,
                action,
            });
            setSubmissions((prev) => prev.map((item) => (item.uuid === updated.uuid ? updated : item)));
            toast.success("Submission updated");
            setSelectedSubmission(updated);
        } catch (error) {
            console.error(error);
            toast.error("Failed to update submission");
        } finally {
            setSaving(false);
        }
    };

    const submissionContent = useMemo(() => {
        if (!selectedSubmission?.content) return {};
        if (typeof selectedSubmission.content === "string") {
            try {
                return JSON.parse(selectedSubmission.content);
            } catch (error) {
                return { text: selectedSubmission.content };
            }
        }
        return selectedSubmission.content;
    }, [selectedSubmission]);

    if (loading) {
        return (
            <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                    <h2 className="text-xl font-semibold">Submissions</h2>
                    <p className="text-sm text-muted-foreground">
                        Review learner assignments and provide feedback.
                    </p>
                </div>
            </div>

            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="relative w-full sm:max-w-sm">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                        placeholder="Search submissions..."
                        value={searchTerm}
                        onChange={(event) => setSearchTerm(event.target.value)}
                        className="pl-9"
                    />
                </div>
                <div className="w-full sm:w-56">
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                        <SelectTrigger>
                            <SelectValue placeholder="Filter by status" />
                        </SelectTrigger>
                        <SelectContent>
                            {STATUS_OPTIONS.map((status) => (
                                <SelectItem key={status} value={status} className="capitalize">
                                    {status.replace(/_/g, " ")}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                </div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold">{submissions.length}</p>
                        <p className="text-sm text-muted-foreground">Total</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-blue-500">
                            {submissions.filter((s) => s.status === "submitted" || s.status === "in_review").length}
                        </p>
                        <p className="text-sm text-muted-foreground">Awaiting Review</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-amber-500">
                            {submissions.filter((s) => s.status === "needs_revision").length}
                        </p>
                        <p className="text-sm text-muted-foreground">Needs Revision</p>
                    </CardContent>
                </Card>
                <Card>
                    <CardContent className="pt-4 text-center">
                        <p className="text-2xl font-bold text-green-600">
                            {submissions.filter((s) => s.status === "graded" || s.status === "approved").length}
                        </p>
                        <p className="text-sm text-muted-foreground">Graded</p>
                    </CardContent>
                </Card>
            </div>

            {filteredSubmissions.length === 0 ? (
                <Card>
                    <CardContent className="py-12 text-center">
                        <ClipboardCheck className="h-12 w-12 mx-auto text-muted-foreground/40 mb-4" />
                        <p className="text-muted-foreground">
                            {submissions.length === 0
                                ? "No submissions yet."
                                : "No submissions match your filters."}
                        </p>
                    </CardContent>
                </Card>
            ) : (
                <Card>
                    <CardHeader>
                        <CardTitle>Latest Submissions</CardTitle>
                        <CardDescription>{filteredSubmissions.length} submission(s)</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="divide-y">
                            {filteredSubmissions.map((submission) => (
                                <div key={submission.uuid} className="flex flex-col gap-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                                    <div>
                                        <p className="font-medium">{submission.assignment_title || "Assignment"}</p>
                                        <p className="text-sm text-muted-foreground">
                                            {submission.user_name || submission.user_email || "Learner"}
                                        </p>
                                        <p className="text-xs text-muted-foreground">
                                            {submission.submitted_at
                                                ? format(new Date(submission.submitted_at), "MMM d, yyyy")
                                                : "Not submitted"}
                                        </p>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-3">
                                        {getStatusBadge(submission.status, submission.status_display)}
                                        <div className="text-right">
                                            <p className="text-sm font-medium">
                                                {submission.score !== undefined && submission.score !== null ? submission.score : "N/A"}
                                            </p>
                                            <p className="text-xs text-muted-foreground">Score</p>
                                        </div>
                                        <Button variant="outline" size="sm" onClick={() => openReviewDialog(submission)}>
                                            Review
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            <Dialog open={!!selectedSubmission} onOpenChange={(open) => !open && setSelectedSubmission(null)}>
                <DialogContent className="max-w-3xl">
                    <DialogHeader>
                        <DialogTitle>Review Submission</DialogTitle>
                        <DialogDescription>
                            {selectedSubmission?.assignment_title || "Assignment"} - {selectedSubmission?.user_name || selectedSubmission?.user_email}
                        </DialogDescription>
                    </DialogHeader>
                    {selectedSubmission && (
                        <div className="space-y-4">
                            <Card>
                                <CardHeader className="pb-2">
                                    <CardTitle className="text-base">Submission Details</CardTitle>
                                    <CardDescription>
                                        {selectedSubmission.submitted_at
                                            ? format(new Date(selectedSubmission.submitted_at), "MMM d, yyyy - h:mm a")
                                            : "Not submitted yet"}
                                    </CardDescription>
                                </CardHeader>
                                <CardContent className="space-y-3 text-sm">
                                    {submissionContent?.text && (
                                        <div>
                                            <p className="font-medium mb-1">Response</p>
                                            <div 
                                                className="text-muted-foreground prose prose-sm dark:prose-invert max-w-none"
                                                dangerouslySetInnerHTML={{ __html: submissionContent.text }}
                                            />
                                        </div>
                                    )}
                                    {submissionContent?.url && (
                                        <div>
                                            <p className="font-medium mb-1">Reference URL</p>
                                            <a
                                                href={submissionContent.url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-primary underline"
                                            >
                                                {submissionContent.url}
                                            </a>
                                        </div>
                                    )}
                                    {selectedSubmission.file_url && (
                                        <div>
                                            <p className="font-medium mb-1">File</p>
                                            <a
                                                href={selectedSubmission.file_url}
                                                target="_blank"
                                                rel="noreferrer"
                                                className="text-primary underline"
                                            >
                                                {selectedSubmission.file_url}
                                            </a>
                                        </div>
                                    )}
                                </CardContent>
                            </Card>

                            <div className="grid gap-4 sm:grid-cols-2">
                                <div className="space-y-2">
                                    <Label htmlFor="score">Score</Label>
                                    <Input
                                        id="score"
                                        type="number"
                                        min="0"
                                        value={scoreInput}
                                        onChange={(event) => setScoreInput(event.target.value)}
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label htmlFor="action">Action</Label>
                                    <Select value={action} onValueChange={(value) => setAction(value as "grade" | "return" | "approve")}>
                                        <SelectTrigger id="action">
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="grade">Grade</SelectItem>
                                            <SelectItem value="return">Return for Revision</SelectItem>
                                            <SelectItem value="approve">Approve</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="feedback">Feedback</Label>
                                <Textarea
                                    id="feedback"
                                    value={feedbackInput}
                                    onChange={(event) => setFeedbackInput(event.target.value)}
                                    placeholder="Share feedback with the learner"
                                    className="min-h-[120px]"
                                />
                            </div>
                        </div>
                    )}
                    <DialogFooter>
                        <Button variant="outline" onClick={() => setSelectedSubmission(null)}>
                            Close
                        </Button>
                        <Button onClick={handleSaveReview} disabled={saving}>
                            {saving ? "Saving..." : "Save Review"}
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        </div>
    );
}

export default SubmissionsTab;
