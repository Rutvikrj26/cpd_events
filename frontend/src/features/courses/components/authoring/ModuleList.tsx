import React, { useState } from 'react';
import {
    GripVertical,
    Trash2,
    Edit2,
    FileText,
    ChevronRight,
    ChevronDown,
    HelpCircle,
    ClipboardCheck,
    Plus,
} from 'lucide-react';
import { Button } from '@/shared/ui/button';
import { Badge } from '@/shared/ui/badge';
import { Card, CardContent } from '@/shared/ui/card';
import type { Assignment, CourseModule } from '@/api/courses/types';

interface ModuleListCallbacks {
    onDeleteModule: (moduleUuid: string) => void;
    onAddContent: (moduleUuid: string) => void;
    onEditContent: (moduleUuid: string, content: any) => void;
    onPreviewContent: (content: any) => void;
    onDeleteContent: (contentUuid: string) => void;
    onAddAssignment: (moduleUuid: string) => void;
    onEditAssignment: (moduleUuid: string, assignment: Assignment) => void;
    onDeleteAssignment: (moduleUuid: string, assignmentUuid: string) => void;
}

interface ModuleListProps extends ModuleListCallbacks {
    modules: CourseModule[];
}

interface ModuleItemProps extends ModuleListCallbacks {
    module: CourseModule;
}

function ModuleItem({
    module,
    onDeleteModule,
    onAddContent,
    onEditContent,
    onPreviewContent,
    onDeleteContent,
    onAddAssignment,
    onEditAssignment,
    onDeleteAssignment,
}: ModuleItemProps) {
    const [isExpanded, setIsExpanded] = useState(false);
    const contents: any[] = module.module?.contents || [];
    const assignments: Assignment[] = module.module?.assignments || [];

    return (
        <Card className="overflow-hidden">
            <div className="flex items-center p-4 bg-muted/30 border-b border-border">
                <Button
                    variant="ghost"
                    size="icon"
                    className="mr-2 cursor-grab text-muted-foreground hover:text-foreground"
                    title="Drag to reorder (visual only)"
                >
                    <GripVertical className="h-4 w-4" />
                </Button>
                <div className="flex-1">
                    <div className="flex items-center gap-2">
                        <h3 className="font-medium">{module.module?.title || 'Untitled Module'}</h3>
                        {module.is_required && (
                            <Badge variant="secondary" className="text-[10px] h-5">
                                Required
                            </Badge>
                        )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                        {contents.length} items • {module.module?.cpd_credits || 0} credits
                    </p>
                </div>
                <div className="flex items-center gap-1">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsExpanded((prev) => !prev)}
                    >
                        {isExpanded ? (
                            <ChevronDown className="h-4 w-4" />
                        ) : (
                            <ChevronRight className="h-4 w-4" />
                        )}
                    </Button>
                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8 text-muted-foreground hover:text-destructive"
                        onClick={(e) => {
                            e.stopPropagation();
                            onDeleteModule(module.uuid);
                        }}
                    >
                        <Trash2 className="h-4 w-4" />
                    </Button>
                </div>
            </div>

            {isExpanded && (
                <CardContent className="p-0 bg-card">
                    <div className="divide-y divide-border">
                        {/* Contents */}
                        {contents.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground italic">
                                No content in this module yet.
                                <div className="mt-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-xs"
                                        onClick={() => onAddContent(module.module.uuid)}
                                    >
                                        <Plus className="mr-1 h-3 w-3" /> Add Content
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            contents.map((content: any) => (
                                <div
                                    key={content.uuid}
                                    className="flex items-center p-3 pl-12 hover:bg-muted/30 group cursor-pointer"
                                    onClick={() => onPreviewContent(content)}
                                >
                                    <div className="mr-3 text-muted-foreground">
                                        {content.content_type === 'quiz' ? (
                                            <HelpCircle className="h-4 w-4 text-primary" />
                                        ) : (
                                            <FileText className="h-4 w-4" />
                                        )}
                                    </div>
                                    <span className="text-sm flex-1">
                                        {content.title}{' '}
                                        <span className="text-xs text-muted-foreground ml-2">
                                            ({content.content_type})
                                        </span>
                                    </span>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                        <Button
                                            variant="ghost"
                                            size="sm"
                                            className="h-6 px-2 text-xs"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onPreviewContent(content);
                                            }}
                                        >
                                            Preview
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onEditContent(module.module.uuid, content);
                                            }}
                                        >
                                            <Edit2 className="h-3 w-3" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                onDeleteContent(content.uuid);
                                            }}
                                        >
                                            <Trash2 className="h-3 w-3" />
                                        </Button>
                                    </div>
                                </div>
                            ))
                        )}
                        <div className="p-2 pl-12 bg-muted/20">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-muted-foreground hover:text-primary"
                                onClick={() => onAddContent(module.module.uuid)}
                            >
                                <Plus className="mr-1 h-3 w-3" /> Add Content
                            </Button>
                        </div>

                        {/* Assignments */}
                        <div className="border-t border-border" />
                        {assignments.length === 0 ? (
                            <div className="p-8 text-center text-sm text-muted-foreground italic">
                                No assignments in this module yet.
                                <div className="mt-2">
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        className="h-7 text-xs"
                                        onClick={() => onAddAssignment(module.module.uuid)}
                                    >
                                        <Plus className="mr-1 h-3 w-3" /> Add Assignment
                                    </Button>
                                </div>
                            </div>
                        ) : (
                            assignments.map((assignment) => (
                                <div
                                    key={assignment.uuid}
                                    className="flex items-center p-3 pl-12 hover:bg-muted/30 group"
                                >
                                    <div className="mr-3 text-muted-foreground">
                                        <ClipboardCheck className="h-4 w-4 text-warning" />
                                    </div>
                                    <span className="text-sm flex-1">
                                        {assignment.title}
                                        <span className="text-xs text-muted-foreground ml-2">
                                            ({assignment.submission_type || 'text'})
                                        </span>
                                    </span>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6"
                                            onClick={() =>
                                                onEditAssignment(module.module.uuid, assignment)
                                            }
                                        >
                                            <Edit2 className="h-3 w-3" />
                                        </Button>
                                        <Button
                                            variant="ghost"
                                            size="icon"
                                            className="h-6 w-6 text-muted-foreground hover:text-destructive"
                                            onClick={() =>
                                                onDeleteAssignment(
                                                    module.module.uuid,
                                                    assignment.uuid,
                                                )
                                            }
                                        >
                                            <Trash2 className="h-3 w-3" />
                                        </Button>
                                    </div>
                                </div>
                            ))
                        )}
                        <div className="p-2 pl-12 bg-muted/20">
                            <Button
                                variant="ghost"
                                size="sm"
                                className="h-7 text-xs text-muted-foreground hover:text-primary"
                                onClick={() => onAddAssignment(module.module.uuid)}
                            >
                                <Plus className="mr-1 h-3 w-3" /> Add Assignment
                            </Button>
                        </div>
                    </div>
                </CardContent>
            )}
        </Card>
    );
}

export function ModuleList({ modules, ...callbacks }: ModuleListProps) {
    return (
        <div className="space-y-4">
            {modules.map((courseModule) => (
                <ModuleItem key={courseModule.uuid} module={courseModule} {...callbacks} />
            ))}
        </div>
    );
}
