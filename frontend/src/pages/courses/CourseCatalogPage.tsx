import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, BookOpen } from 'lucide-react';
import { Input } from '@/shared/ui/input';
import { Button } from '@/shared/ui/button';
import { Card } from '@/shared/ui/card';
import { Skeleton } from '@/shared/ui/skeleton';
import { Pagination } from '@/shared/ui/pagination';
import { EmptyState } from '@/shared/ui/empty-state';
import { useDebounce } from '@/shared/hooks';
import { CourseCard, usePublicCourses } from '@/features/courses';
import type { Course } from '@/api/courses/types';

const PAGE_SIZE = 12;

/**
 * CourseCatalogPage — thin shell. Data via React Query, UI via the
 * feature's CourseCard. Search input is debounced so typing doesn't
 * re-fetch on every keystroke.
 */
export const CourseCatalogPage: React.FC = () => {
    const navigate = useNavigate();
    const [searchQuery, setSearchQuery] = useState('');
    const [page, setPage] = useState(1);
    const debouncedSearch = useDebounce(searchQuery, 250);

    // Reset to page 1 whenever the search term changes.
    useEffect(() => {
        setPage(1);
    }, [debouncedSearch]);

    const { data, isLoading } = usePublicCourses({
        page,
        page_size: PAGE_SIZE,
        search: debouncedSearch || undefined,
    });

    const courses = (data?.results ?? []).filter(
        (c) => c.status === 'published' && c.is_public
    );
    const totalPages = data?.total_pages ?? 1;
    const totalCount = data?.count ?? 0;

    const handleViewCourse = (course: Course) => {
        navigate(`/courses/${course.slug || course.uuid}`);
    };

    if (isLoading && page === 1) {
        return (
            <div className="container mx-auto max-w-7xl px-4 py-section">
                <div className="mb-section text-center">
                    <Skeleton className="mx-auto mb-tight h-10 w-72" />
                    <Skeleton className="mx-auto h-5 w-96" />
                </div>
                <div className="grid grid-cols-1 gap-card md:grid-cols-2 xl:grid-cols-3">
                    {Array.from({ length: 6 }).map((_, i) => (
                        <Card key={i} elevation="rest">
                            <Skeleton className="aspect-video w-full" />
                            <div className="space-y-tight p-card">
                                <Skeleton className="h-6 w-3/4" />
                                <Skeleton className="h-4 w-full" />
                                <Skeleton className="h-4 w-1/2" />
                            </div>
                        </Card>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/20">
            <div className="container mx-auto max-w-7xl px-4 py-section">
                <header className="mb-section text-center">
                    <div className="mb-tight inline-flex items-center justify-center gap-3">
                        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                            <BookOpen
                                className="h-6 w-6 text-primary"
                                strokeWidth={1.75}
                                aria-hidden="true"
                            />
                        </div>
                        <h1 className="text-display-lg text-foreground">Course catalog</h1>
                    </div>
                    <p className="mx-auto max-w-2xl text-body-lg text-muted-foreground">
                        Discover self-paced, live, and hybrid professional development courses
                        from leading organizations.
                    </p>
                </header>

                <div className="mx-auto mb-section max-w-2xl">
                    <div className="relative">
                        <Search
                            className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted-foreground"
                            aria-hidden="true"
                        />
                        <Input
                            type="text"
                            placeholder="Search courses by title, description, or organization..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="h-14 pl-12 text-body-lg"
                            aria-label="Search courses"
                        />
                    </div>
                    <div className="mt-tight flex items-center gap-card text-body text-muted-foreground">
                        <span>
                            {totalCount} {totalCount === 1 ? 'course' : 'courses'} found
                        </span>
                        {searchQuery && (
                            <Button variant="ghost" size="sm" onClick={() => setSearchQuery('')}>
                                Clear search
                            </Button>
                        )}
                    </div>
                </div>

                {courses.length === 0 ? (
                    <EmptyState
                        tone="muted"
                        icon={BookOpen}
                        title="No courses found"
                        description={
                            searchQuery
                                ? 'Try a different search term, or clear the filter to browse everything.'
                                : 'Check back soon for new courses.'
                        }
                        action={
                            searchQuery ? (
                                <Button variant="outline" onClick={() => setSearchQuery('')}>
                                    Clear search
                                </Button>
                            ) : undefined
                        }
                    />
                ) : (
                    <>
                        <div className="grid grid-cols-1 gap-card md:grid-cols-2 xl:grid-cols-3">
                            {courses.map((course) => (
                                <CourseCard
                                    key={course.uuid}
                                    course={course}
                                    onView={handleViewCourse}
                                />
                            ))}
                        </div>

                        {totalPages > 1 && (
                            <Pagination
                                page={page}
                                totalPages={totalPages}
                                totalCount={totalCount}
                                pageSize={PAGE_SIZE}
                                onPageChange={setPage}
                                className="mt-block"
                            />
                        )}
                    </>
                )}
            </div>
        </div>
    );
};
