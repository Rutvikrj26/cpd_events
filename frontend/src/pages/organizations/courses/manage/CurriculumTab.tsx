import React from 'react';
import { CurriculumBuilder } from '@/features/courses';

interface CurriculumTabProps {
    courseUuid: string;
}

export function CurriculumTab({ courseUuid }: CurriculumTabProps) {
    return <CurriculumBuilder courseUuid={courseUuid} />;
}
