import React, { useEffect, useMemo, useRef } from 'react';
import ReactQuill, { Quill } from 'react-quill-new';
import 'react-quill-new/dist/quill.snow.css';
import 'quill-mention/autoregister';
import { searchCourseMembers } from '@/api/courses';

interface RichTextEditorProps {
    value: string;
    onChange: (html: string) => void;
    placeholder?: string;
    courseUuid: string;
    minHeight?: number;
    disabled?: boolean;
}

const TOOLBAR = [
    ['bold', 'italic', 'underline', 'strike'],
    [{ list: 'ordered' }, { list: 'bullet' }],
    ['blockquote', 'code-block', 'link'],
    ['clean'],
];

export function RichTextEditor({
    value,
    onChange,
    placeholder,
    courseUuid,
    minHeight = 120,
    disabled = false,
}: RichTextEditorProps) {
    const quillRef = useRef<ReactQuill>(null);
    const courseUuidRef = useRef(courseUuid);

    useEffect(() => {
        courseUuidRef.current = courseUuid;
    }, [courseUuid]);

    const modules = useMemo(
        () => ({
            toolbar: TOOLBAR,
            mention: {
                allowedChars: /^[A-Za-z0-9\s.@-]*$/,
                mentionDenotationChars: ['@'],
                dataAttributes: ['user-uuid', 'user-email'],
                source: async (searchTerm: string, renderList: (items: any[]) => void) => {
                    try {
                        const members = await searchCourseMembers(courseUuidRef.current, searchTerm);
                        const items = members.map((m) => ({
                            id: m.uuid,
                            value: m.full_name || m.email,
                            'user-uuid': m.uuid,
                            'user-email': m.email,
                        }));
                        renderList(items);
                    } catch {
                        renderList([]);
                    }
                },
                renderItem: (item: any) => {
                    const el = document.createElement('div');
                    el.textContent = item.value;
                    return el;
                },
                onSelect: (item: any, insertItem: (it: any) => void) => {
                    insertItem(item);
                },
            },
        }),
        []
    );

    return (
        <div
            className="rounded-md border bg-background discussion-rich-editor"
            style={{ minHeight }}
        >
            <ReactQuill
                ref={quillRef}
                value={value}
                onChange={onChange}
                placeholder={placeholder}
                modules={modules}
                theme="snow"
                readOnly={disabled}
            />
        </div>
    );
}

// Export raw Quill class so tests or advanced callers can register custom modules.
export { Quill };
