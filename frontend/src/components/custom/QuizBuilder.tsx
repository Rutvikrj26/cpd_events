import React, { useState } from 'react';
import { Plus, Trash2, Check, X, GripVertical } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';

export interface QuizQuestion {
    id: string;
    text: string;
    type: 'single' | 'multiple';
    options: { id: string; text: string; isCorrect: boolean }[];
    points: number;
}

export interface QuizData {
    questions: QuizQuestion[];
    passing_score: number;
}

interface QuizBuilderProps {
    initialData?: QuizData;
    onChange: (data: QuizData) => void;
}

export function QuizBuilder({ initialData, onChange }: QuizBuilderProps) {
    const [questions, setQuestions] = useState<QuizQuestion[]>(initialData?.questions || []);
    const [passingScore, setPassingScore] = useState(initialData?.passing_score || 70);

    const updateParent = (newQuestions: QuizQuestion[], newPassingScore: number) => {
        onChange({
            questions: newQuestions,
            passing_score: newPassingScore
        });
    };

    const addQuestion = () => {
        const newQuestion: QuizQuestion = {
            id: crypto.randomUUID(),
            text: '',
            type: 'single',
            options: [
                { id: crypto.randomUUID(), text: '', isCorrect: false },
                { id: crypto.randomUUID(), text: '', isCorrect: false }
            ],
            points: 10
        };
        const updated = [...questions, newQuestion];
        setQuestions(updated);
        updateParent(updated, passingScore);
    };

    const updateQuestion = (id: string, updates: Partial<QuizQuestion>) => {
        const updated = questions.map(q => q.id === id ? { ...q, ...updates } : q);
        setQuestions(updated);
        updateParent(updated, passingScore);
    };

    const removeQuestion = (id: string) => {
        const updated = questions.filter(q => q.id !== id);
        setQuestions(updated);
        updateParent(updated, passingScore);
    };

    const addOption = (questionId: string) => {
        const updated = questions.map(q => {
            if (q.id !== questionId) return q;
            return {
                ...q,
                options: [...q.options, { id: crypto.randomUUID(), text: '', isCorrect: false }]
            };
        });
        setQuestions(updated);
        updateParent(updated, passingScore);
    };

    const updateOption = (questionId: string, optionId: string, updates: Partial<{ text: string; isCorrect: boolean }>) => {
        const updated = questions.map(q => {
            if (q.id !== questionId) return q;

            // For single choice, if setting correct, uncheck others
            let newOptions = q.options.map(opt => {
                if (opt.id === optionId) {
                    return { ...opt, ...updates };
                }
                if (q.type === 'single' && updates.isCorrect) {
                    return { ...opt, isCorrect: false };
                }
                return opt;
            });

            return { ...q, options: newOptions };
        });
        setQuestions(updated);
        updateParent(updated, passingScore);
    };

    const removeOption = (questionId: string, optionId: string) => {
        const updated = questions.map(q => {
            if (q.id !== questionId) return q;
            return { ...q, options: q.options.filter(opt => opt.id !== optionId) };
        });
        setQuestions(updated);
        updateParent(updated, passingScore);
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center gap-4 p-4 border rounded-lg bg-gray-50">
                <div className="flex-1">
                    <Label htmlFor="passing-score">Passing Score (%)</Label>
                    <div className="flex items-center gap-2 mt-1">
                        <Input
                            id="passing-score"
                            type="number"
                            min="0"
                            max="100"
                            value={passingScore}
                            onChange={(e) => {
                                const val = parseInt(e.target.value) || 0;
                                setPassingScore(val);
                                updateParent(questions, val);
                            }}
                            className="w-24"
                        />
                        <span className="text-sm text-muted-foreground">Required to pass this quiz</span>
                    </div>
                </div>
                <div className="text-right text-sm text-muted-foreground">
                    Total Questions: {questions.length} | Max Points: {questions.reduce((sum, q) => sum + (q.points || 0), 0)}
                </div>
            </div>

            <div className="space-y-4">
                {questions.map((question, index) => (
                    <Card key={question.id} className="group relative">
                        <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <Button variant="ghost" size="icon" className="text-red-500 hover:text-red-600 hover:bg-red-50" onClick={() => removeQuestion(question.id)}>
                                <Trash2 className="h-4 w-4" />
                            </Button>
                        </div>
                        <CardHeader className="pb-2">
                            <div className="flex items-center gap-2">
                                <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-semibold">Q{index + 1}</span>
                                <Select
                                    value={question.type}
                                    onValueChange={(val: 'single' | 'multiple') => updateQuestion(question.id, { type: val })}
                                >
                                    <SelectTrigger className="w-[180px] h-8 text-xs">
                                        <SelectValue placeholder="Question Type" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="single">Single Choice</SelectItem>
                                        <SelectItem value="multiple">Multiple Choice</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div>
                                <Textarea
                                    placeholder="Enter your question text here..."
                                    value={question.text}
                                    onChange={(e) => updateQuestion(question.id, { text: e.target.value })}
                                    className="resize-none"
                                />
                            </div>

                            <div className="space-y-2">
                                <Label className="text-xs text-muted-foreground">Options</Label>
                                {question.options.map((option) => (
                                    <div key={option.id} className="flex items-center gap-2">
                                        <div className="pt-1">
                                            {question.type === 'single' ? (
                                                <div
                                                    className={`h-4 w-4 rounded-full border flex items-center justify-center cursor-pointer ${option.isCorrect ? 'border-green-500 bg-green-50' : 'border-gray-300'}`}
                                                    onClick={() => updateOption(question.id, option.id, { isCorrect: true })}
                                                >
                                                    {option.isCorrect && <div className="h-2 w-2 rounded-full bg-green-500" />}
                                                </div>
                                            ) : (
                                                <Checkbox
                                                    checked={option.isCorrect}
                                                    onCheckedChange={(checked) => updateOption(question.id, option.id, { isCorrect: checked as boolean })}
                                                />
                                            )}
                                        </div>
                                        <Input
                                            value={option.text}
                                            onChange={(e) => updateOption(question.id, option.id, { text: e.target.value })}
                                            placeholder={`Option text`}
                                            className={`flex-1 ${option.isCorrect ? 'border-green-200 bg-green-50/20' : ''}`}
                                        />
                                        <Button variant="ghost" size="icon" className="h-8 w-8 text-gray-400 hover:text-red-500" onClick={() => removeOption(question.id, option.id)}>
                                            <X className="h-3 w-3" />
                                        </Button>
                                    </div>
                                ))}
                                <Button variant="ghost" size="sm" className="h-7 text-xs text-blue-500 hover:text-blue-700 p-0 hover:bg-transparent" onClick={() => addOption(question.id)}>
                                    <Plus className="h-3 w-3 mr-1" /> Add Option
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                ))}
            </div>

            <Button onClick={addQuestion} className="w-full" variant="outline" size="lg">
                <Plus className="mr-2 h-4 w-4" /> Add Question
            </Button>
        </div>
    );
}
