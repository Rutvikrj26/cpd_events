import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/ui/card';
import { Badge } from '@/shared/ui/badge';
import { Button } from '@/shared/ui/button';
import { Checkbox } from '@/shared/ui/checkbox';
import { RadioGroup, RadioGroupItem } from '@/shared/ui/radio-group';
import type { ModuleContent } from './types';

/**
 * QuizTaker — renders a quiz, scores client-side against `passing_score`,
 * and reports `{answers, score}` to the parent on pass.
 *
 * Shape of `content.content_data`:
 *   { questions: Question[], passing_score: number }
 *
 * Each question:
 *   { id, text, type: 'single' | 'multiple', options, correct_answer, points }
 *
 * Backwards-compatible with two option shapes:
 *   - string[] (legacy) — index of correct treated as correct_answer
 *   - { id, text, isCorrect }[] (current)
 */

export interface QuizResult {
    answers: Record<string, string[]>;
    score: number;
}

interface SavedQuizState {
    quiz_answers?: Record<string, string[]>;
    score?: number;
    passed?: boolean;
}

interface QuizTakerProps {
    content: ModuleContent;
    onComplete: (result: QuizResult) => void | Promise<void>;
    /** Previously persisted state — typically `contentProgress.last_position`. */
    savedProgress?: SavedQuizState;
}

export function QuizTaker({ content, onComplete, savedProgress }: QuizTakerProps) {
    const alreadyPassed = savedProgress?.passed === true;

    const [answers, setAnswers] = useState<Record<string, string[]>>(
        alreadyPassed && savedProgress?.quiz_answers ? savedProgress.quiz_answers : {}
    );
    const [result, setResult] = useState<{ scorePercent: number; passed: boolean } | null>(
        alreadyPassed && savedProgress?.score != null
            ? { scorePercent: savedProgress.score, passed: true }
            : null
    );

    const quizData = content.content_data || {};
    const rawQuestions = quizData.questions || [];
    const passingScore = quizData.passing_score ?? 70;

    const questions = rawQuestions.map((q: any) => {
        const options = (q.options || []).map((opt: any, idx: number) => {
            if (typeof opt === 'string') {
                return {
                    id: String(idx),
                    text: opt,
                    isCorrect: q.correct_answer === idx,
                };
            }
            return {
                id: opt.id ?? String(idx),
                text: opt.text ?? opt,
                isCorrect: opt.isCorrect ?? false,
            };
        });
        return { ...q, id: String(q.id), options, points: q.points ?? 1 };
    });

    const handleSingleSelect = (questionId: string, optionId: string) => {
        setAnswers((prev) => ({ ...prev, [questionId]: [optionId] }));
    };

    const handleMultipleSelect = (questionId: string, optionId: string) => {
        setAnswers((prev) => {
            const existing = prev[questionId] || [];
            if (existing.includes(optionId)) {
                return {
                    ...prev,
                    [questionId]: existing.filter((id) => id !== optionId),
                };
            }
            return { ...prev, [questionId]: [...existing, optionId] };
        });
    };

    const handleSubmit = async () => {
        let totalPoints = 0;
        let earnedPoints = 0;

        questions.forEach((question: any) => {
            const correctOptions = question.options
                .filter((opt: any) => opt.isCorrect)
                .map((opt: any) => opt.id);
            const selected = answers[question.id] || [];
            totalPoints += question.points;

            const isCorrect =
                correctOptions.length === selected.length &&
                correctOptions.every((id: string) => selected.includes(id));

            if (isCorrect) {
                earnedPoints += question.points;
            }
        });

        const scorePercent =
            totalPoints > 0 ? Math.round((earnedPoints / totalPoints) * 100) : 0;
        const passed = scorePercent >= passingScore;

        setResult({ scorePercent, passed });
        if (passed) {
            await onComplete({ answers, score: scorePercent });
        }
    };

    const handleRetry = () => {
        setAnswers({});
        setResult(null);
    };

    return (
        <Card elevation="rest">
            <CardHeader>
                <div className="flex items-center justify-between">
                    <CardTitle>Quiz</CardTitle>
                    {alreadyPassed && savedProgress?.score != null && (
                        <Badge variant="success">Passed — {savedProgress.score}%</Badge>
                    )}
                </div>
            </CardHeader>
            <CardContent className="space-y-card">
                {questions.length === 0 && (
                    <p className="text-muted-foreground">No quiz questions available.</p>
                )}
                {questions.map((question: any, index: number) => (
                    <div key={question.id} className="space-y-tight">
                        <div className="flex items-center gap-2">
                            <Badge variant="outline">Q{index + 1}</Badge>
                            <p className="font-medium">{question.text}</p>
                        </div>
                        {question.type === 'multiple' ? (
                            <div className="space-y-2 pl-2">
                                {question.options.map((option: any) => (
                                    <label
                                        key={option.id}
                                        className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 text-body hover:bg-muted/50"
                                    >
                                        <Checkbox
                                            checked={(answers[question.id] || []).includes(option.id)}
                                            onCheckedChange={() =>
                                                handleMultipleSelect(question.id, option.id)
                                            }
                                        />
                                        <span>{option.text}</span>
                                    </label>
                                ))}
                            </div>
                        ) : (
                            <RadioGroup
                                value={(answers[question.id] || [])[0] ?? ''}
                                onValueChange={(value) =>
                                    handleSingleSelect(question.id, value)
                                }
                                className="pl-2"
                            >
                                {question.options.map((option: any) => (
                                    <label
                                        key={option.id}
                                        className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 text-body hover:bg-muted/50"
                                    >
                                        <RadioGroupItem value={option.id} />
                                        <span>{option.text}</span>
                                    </label>
                                ))}
                            </RadioGroup>
                        )}
                    </div>
                ))}

                <div className="flex items-center justify-between">
                    <Button onClick={handleSubmit} disabled={result?.passed}>
                        Submit quiz
                    </Button>
                    {result && (
                        <div className="flex items-center gap-2">
                            <Badge variant={result.passed ? 'success' : 'overdue'}>
                                {result.scorePercent}% {result.passed ? 'Passed' : 'Try again'}
                            </Badge>
                            {!result.passed && (
                                <Button variant="outline" size="sm" onClick={handleRetry}>
                                    Retry
                                </Button>
                            )}
                        </div>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}
