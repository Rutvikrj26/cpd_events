import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, BookOpen, SlidersHorizontal, Award, X, Clock, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Pagination } from "@/components/ui/pagination";
import { getPublicCourses, PublicCourseListParams, Course } from "@/api/courses";
import { PaginatedResponse } from "@/api/types";
import { useAuth } from "@/contexts/AuthContext";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

// Define filter options
type Filters = {
  freeOnly: boolean;
  paidOnly: boolean;
};

const initialFilters: Filters = {
  freeOnly: false,
  paidOnly: false,
};

export function CourseDiscoveryPage() {
  const [searchTerm, setSearchTerm] = useState("");
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("newest");
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [showMobileFilters, setShowMobileFilters] = useState(false);
  const { user, isAuthenticated } = useAuth();

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const fetchCourses = useCallback(async () => {
    setLoading(true);
    try {
      const params: PublicCourseListParams = {
        page,
        page_size: pageSize,
        search: searchTerm || undefined,
      };
      const response = await getPublicCourses(params);
      // Filter only published and public courses (client-side for now)
      const publicCourses = response.results.filter(
        course => course.status === 'published' && course.is_public
      );
      setCourses(publicCourses);
      setTotalPages(response.total_pages);
      setTotalCount(response.count);
    } catch (error) {
      console.error("Failed to load courses", error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchTerm]);

  useEffect(() => {
    fetchCourses();
  }, [fetchCourses]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [searchTerm, filters]);

  const resetFilters = () => {
    setFilters(initialFilters);
    setSearchTerm("");
    setPage(1);
  };

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (filters.freeOnly) count++;
    if (filters.paidOnly) count++;
    return count;
  }, [filters]);

  // Apply client-side filters (until backend supports all filters)
  const filteredCourses = useMemo(() => {
    let result = [...courses];

    // Price filters (client-side for now)
    if (filters.freeOnly && !filters.paidOnly) {
      result = result.filter(
        (course) => course.is_free || !course.price_cents || course.price_cents === 0
      );
    } else if (filters.paidOnly && !filters.freeOnly) {
      result = result.filter(
        (course) => !course.is_free && course.price_cents && course.price_cents > 0
      );
    }

    // Sorting
    result.sort((a, b) => {
      switch (sortBy) {
        case "newest":
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case "popular":
          return (b.enrollment_count || 0) - (a.enrollment_count || 0);
        case "price-low":
          return (a.price_cents || 0) - (b.price_cents || 0);
        case "price-high":
          return (b.price_cents || 0) - (a.price_cents || 0);
        default:
          return 0;
      }
    });

    return result;
  }, [courses, filters, sortBy]);

  // Determine smart CTA based on user state
  const getEmptyStateCTA = () => {
    if (!isAuthenticated) {
      return {
        text: "Create a Course",
        link: "/signup?role=course_manager&plan=lms",
        secondary: { text: "View Pricing", link: "/pricing" }
      };
    }
    
    // Check if user can create courses (from manifest/subscription)
    // For now, we'll check account_type
    const canCreateCourses = user?.account_type === 'course_manager' || user?.account_type === 'admin';
    
    if (canCreateCourses) {
      return {
        text: "Create a Course",
        link: "/courses/manage/new",
        secondary: { text: "Go to Dashboard", link: "/dashboard" }
      };
    }
    
    return {
      text: "Upgrade to Create Courses",
      link: "/billing",
      secondary: { text: "View Plans", link: "/pricing" }
    };
  };

  const emptyStateCTA = getEmptyStateCTA();

  // Filter sidebar content (reused for desktop and mobile)
  const FilterContent = () => (
    <div className="space-y-6">
      <div>
        <h4 className="text-sm font-medium mb-3">Price</h4>
        <div className="space-y-2">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="price-free"
              checked={filters.freeOnly}
              onCheckedChange={(checked) =>
                setFilters((prev) => ({ ...prev, freeOnly: !!checked }))
              }
            />
            <label htmlFor="price-free" className="text-sm text-muted-foreground font-medium cursor-pointer">
              Free Courses
            </label>
          </div>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="price-paid"
              checked={filters.paidOnly}
              onCheckedChange={(checked) =>
                setFilters((prev) => ({ ...prev, paidOnly: !!checked }))
              }
            />
            <label htmlFor="price-paid" className="text-sm text-muted-foreground font-medium cursor-pointer">
              Paid Courses
            </label>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col min-h-screen">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12">
        <PageHeader
          title="Browse Courses"
          description="Discover self-paced professional development courses."
          className="mb-8"
        />

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Filters Sidebar - Desktop */}
          <div className="hidden lg:block w-72 flex-shrink-0 space-y-8">
            <div className="bg-card border border-border/80 rounded-xl p-6 shadow-sm sticky top-24">
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-semibold text-foreground flex items-center">
                  <SlidersHorizontal className="mr-2 h-4 w-4" /> Filters
                  {activeFilterCount > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {activeFilterCount}
                    </Badge>
                  )}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                  onClick={resetFilters}
                  disabled={activeFilterCount === 0 && !searchTerm}
                >
                  Reset
                </Button>
              </div>
              <FilterContent />
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1 min-w-0">
            {/* Search and Sort Bar */}
            <div className="bg-card p-4 rounded-xl border border-border/80 shadow-sm mb-8 flex flex-col sm:flex-row gap-4 items-center justify-between sticky top-0 z-10 lg:static backdrop-blur-xl lg:backdrop-blur-none bg-card/80 lg:bg-card">
              <div className="relative w-full sm:max-w-md">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Search className="h-4 w-4 text-muted-foreground" />
                </div>
                <Input
                  placeholder="Search courses by title..."
                  className="pl-10 h-11 bg-muted/30 border-border shadow-none focus:bg-card transition-colors"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                    onClick={() => setSearchTerm("")}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                )}
              </div>

              <div className="flex w-full sm:w-auto items-center gap-2">
                {/* Mobile Filters Toggle */}
                <Button
                  variant="outline"
                  className="lg:hidden flex-1 sm:flex-none border-dashed"
                  onClick={() => setShowMobileFilters(!showMobileFilters)}
                >
                  <Filter className="h-4 w-4 mr-2" />
                  Filters
                  {activeFilterCount > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {activeFilterCount}
                    </Badge>
                  )}
                </Button>

                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className="w-full sm:w-[180px] h-11">
                    <SelectValue placeholder="Sort by" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="newest">Newest Listed</SelectItem>
                    <SelectItem value="popular">Most Popular</SelectItem>
                    <SelectItem value="price-low">Price: Low to High</SelectItem>
                    <SelectItem value="price-high">Price: High to Low</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Mobile Filters Panel */}
            {showMobileFilters && (
              <div className="lg:hidden bg-card border border-border/80 rounded-xl p-6 shadow-sm mb-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-foreground">Filters</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={resetFilters}
                    disabled={activeFilterCount === 0}
                  >
                    Reset
                  </Button>
                </div>
                <FilterContent />
              </div>
            )}

            {/* Active Filters Display */}
            {activeFilterCount > 0 && (
              <div className="flex flex-wrap gap-2 mb-6">
                {filters.freeOnly && (
                  <Badge variant="secondary" className="gap-1">
                    Free
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => setFilters((prev) => ({ ...prev, freeOnly: false }))}
                    />
                  </Badge>
                )}
                {filters.paidOnly && (
                  <Badge variant="secondary" className="gap-1">
                    Paid
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => setFilters((prev) => ({ ...prev, paidOnly: false }))}
                    />
                  </Badge>
                )}
              </div>
            )}

            {/* Results Grid */}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div key={i} className="h-96 rounded-xl bg-muted animate-pulse"></div>
                ))}
              </div>
            ) : filteredCourses.length > 0 ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  {filteredCourses.map((course) => (
                    <CourseCard key={course.uuid} course={course} />
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <Pagination
                    page={page}
                    totalPages={totalPages}
                    totalCount={totalCount}
                    pageSize={pageSize}
                    onPageChange={setPage}
                    className="mt-8"
                  />
                )}
              </>
            ) : (
              <div className="text-center py-24 bg-card rounded-xl border border-dashed border-border/80">
                <div className="mx-auto h-16 w-16 bg-muted/30 rounded-full flex items-center justify-center mb-4">
                  <BookOpen className="h-8 w-8 text-slate-300" />
                </div>
                <h3 className="mt-2 text-lg font-semibold text-foreground">No courses found</h3>
                <p className="mt-1 text-muted-foreground max-w-sm mx-auto mb-6">
                  {searchTerm || activeFilterCount > 0
                    ? "We couldn't find any courses matching your criteria."
                    : "Be the first to create a course on our platform!"}
                </p>
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <Link to={emptyStateCTA.link}>
                    <Button size="lg">
                      {emptyStateCTA.text}
                    </Button>
                  </Link>
                  {emptyStateCTA.secondary && (
                    <Link to={emptyStateCTA.secondary.link}>
                      <Button size="lg" variant="outline">
                        {emptyStateCTA.secondary.text}
                      </Button>
                    </Link>
                  )}
                </div>
                {(searchTerm || activeFilterCount > 0) && (
                  <div className="mt-6">
                    <Button variant="ghost" onClick={resetFilters}>
                      Clear Filters
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Course card component for API data
function CourseCard({ course }: { course: Course }) {
  return (
    <Link to={`/courses/${course.slug || course.uuid}`} className="group block h-full">
      <Card className="h-full overflow-hidden hover:shadow-lg transition-all duration-300 border-border/80 hover:border-primary/50 group-hover:-translate-y-1">
        <div className="relative aspect-video bg-gradient-to-br from-slate-100 to-slate-200 overflow-hidden">
          {course.featured_image_url ? (
            <img
              src={course.featured_image_url}
              alt={course.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-primary/10 to-primary/5">
              <BookOpen className="h-16 w-16 text-primary/30" />
            </div>
          )}

          <div className="absolute top-3 right-3">
            {course.is_free || !course.price_cents || course.price_cents === 0 ? (
              <Badge className="bg-success/90 text-white shadow-sm">Free</Badge>
            ) : (
              <Badge className="bg-white/90 text-foreground border shadow-sm">
                ${(course.price_cents / 100).toFixed(0)}
              </Badge>
            )}
          </div>
        </div>
        <CardContent className="p-5 flex flex-col h-[calc(100%-14rem)]">
          <h3 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors line-clamp-2 mb-2 leading-tight">
            {course.title}
          </h3>

          <p className="text-sm text-muted-foreground line-clamp-2 mb-4 flex-1">
            {course.short_description || course.description}
          </p>

          <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
            {course.estimated_hours && (
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{course.estimated_hours}h</span>
              </div>
            )}
            {course.cpd_credits && Number(course.cpd_credits) > 0 && (
              <div className="flex items-center gap-1">
                <Award className="h-3 w-3" />
                <span>{course.cpd_credits} CPD</span>
              </div>
            )}
            {course.enrollment_count > 0 && (
              <div className="flex items-center gap-1">
                <Users className="h-3 w-3" />
                <span>{course.enrollment_count}</span>
              </div>
            )}
          </div>

          {course.organization_name && (
            <div className="flex items-center gap-2 pt-3 border-t border-border/50">
              <Avatar className="h-6 w-6">
                {course.organization_logo_url ? (
                  <AvatarImage src={course.organization_logo_url} alt={course.organization_name} />
                ) : null}
                <AvatarFallback className="text-xs">
                  {course.organization_name[0]}
                </AvatarFallback>
              </Avatar>
              <span className="text-xs text-muted-foreground truncate">{course.organization_name}</span>
            </div>
          )}
        </CardContent>
      </Card>
    </Link>
  );
}
