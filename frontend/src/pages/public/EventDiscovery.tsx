import React, { useEffect, useState, useMemo, useCallback } from "react";
import { Link } from "react-router-dom";
import { Search, Filter, Calendar as CalendarIcon, SlidersHorizontal, Award, X } from "lucide-react";
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
import { getPublicEvents, PublicEventListParams } from "@/api/events";
import { Event } from "@/api/events/types";
import { PaginatedResponse } from "@/api/types";

// Define filter options
const EVENT_TYPES = ["Webinar", "Workshop", "Course", "Conference"];
const FORMATS = ["online", "in-person", "hybrid"] as const;
const FORMAT_LABELS: Record<string, string> = {
  online: "Online",
  "in-person": "In-Person",
  hybrid: "Hybrid",
};

type Filters = {
  eventTypes: string[];
  formats: string[];
  freeOnly: boolean;
  paidOnly: boolean;
};

const initialFilters: Filters = {
  eventTypes: [],
  formats: [],
  freeOnly: false,
  paidOnly: false,
};

export function EventDiscovery() {
  const [searchTerm, setSearchTerm] = useState("");
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState("upcoming");
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [showMobileFilters, setShowMobileFilters] = useState(false);

  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(12);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    try {
      const params: PublicEventListParams = {
        page,
        page_size: pageSize,
        search: searchTerm || undefined,
      };
      const response = await getPublicEvents(params);
      setEvents(response.results);
      setTotalPages(response.total_pages);
      setTotalCount(response.count);
    } catch (error) {
      console.error("Failed to load events", error);
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, searchTerm]);

  useEffect(() => {
    fetchEvents();
  }, [fetchEvents]);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [searchTerm, filters]);

  const toggleEventType = (type: string) => {
    setFilters((prev) => ({
      ...prev,
      eventTypes: prev.eventTypes.includes(type)
        ? prev.eventTypes.filter((t) => t !== type)
        : [...prev.eventTypes, type],
    }));
  };

  const toggleFormat = (format: string) => {
    setFilters((prev) => ({
      ...prev,
      formats: prev.formats.includes(format)
        ? prev.formats.filter((f) => f !== format)
        : [...prev.formats, format],
    }));
  };

  const resetFilters = () => {
    setFilters(initialFilters);
    setSearchTerm("");
    setPage(1);
  };

  const activeFilterCount = useMemo(() => {
    let count = 0;
    count += filters.eventTypes.length;
    count += filters.formats.length;
    if (filters.freeOnly) count++;
    if (filters.paidOnly) count++;
    return count;
  }, [filters]);

  // Apply client-side filters (until backend supports all filters)
  const filteredEvents = useMemo(() => {
    let result = [...events];

    // Event type filter (client-side for now)
    if (filters.eventTypes.length > 0) {
      result = result.filter((event) =>
        filters.eventTypes.some(
          (type) => event.event_type?.toLowerCase() === type.toLowerCase()
        )
      );
    }

    // Format filter (client-side for now)
    if (filters.formats.length > 0) {
      result = result.filter((event) =>
        filters.formats.includes(event.format)
      );
    }

    // Price filters (client-side for now)
    if (filters.freeOnly && !filters.paidOnly) {
      result = result.filter(
        (event) => !event.price || Number(event.price) === 0
      );
    } else if (filters.paidOnly && !filters.freeOnly) {
      result = result.filter(
        (event) => event.price && Number(event.price) > 0
      );
    }

    // Sorting
    result.sort((a, b) => {
      switch (sortBy) {
        case "upcoming":
          return new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime();
        case "newest":
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case "popular":
          return (b.attendee_count || 0) - (a.attendee_count || 0);
        default:
          return 0;
      }
    });

    return result;
  }, [events, filters, sortBy]);

  // Filter sidebar content (reused for desktop and mobile)
  const FilterContent = () => (
    <div className="space-y-6">
      <div>
        <h4 className="text-sm font-medium mb-3">Event Type</h4>
        <div className="space-y-2">
          {EVENT_TYPES.map((type) => (
            <div key={type} className="flex items-center space-x-2">
              <Checkbox
                id={`type-${type}`}
                checked={filters.eventTypes.includes(type)}
                onCheckedChange={() => toggleEventType(type)}
              />
              <label
                htmlFor={`type-${type}`}
                className="text-sm text-muted-foreground leading-none cursor-pointer font-medium"
              >
                {type}
              </label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="text-sm font-medium mb-3">Format</h4>
        <div className="space-y-2">
          {FORMATS.map((format) => (
            <div key={format} className="flex items-center space-x-2">
              <Checkbox
                id={`format-${format}`}
                checked={filters.formats.includes(format)}
                onCheckedChange={() => toggleFormat(format)}
              />
              <label
                htmlFor={`format-${format}`}
                className="text-sm text-muted-foreground leading-none cursor-pointer font-medium"
              >
                {FORMAT_LABELS[format]}
              </label>
            </div>
          ))}
        </div>
      </div>

      <Separator />

      <div>
        <h4 className="text-sm font-medium mb-3">Registration Fee</h4>
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
              Free
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
              Paid
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
          title="Browse Events"
          description="Discover professional development opportunities to advance your career."
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
                  placeholder="Search events, topics, or organizers..."
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
                    <SelectItem value="upcoming">Upcoming</SelectItem>
                    <SelectItem value="newest">Newest Listed</SelectItem>
                    <SelectItem value="popular">Most Popular</SelectItem>
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
                {filters.eventTypes.map((type) => (
                  <Badge key={type} variant="secondary" className="gap-1">
                    {type}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => toggleEventType(type)}
                    />
                  </Badge>
                ))}
                {filters.formats.map((format) => (
                  <Badge key={format} variant="secondary" className="gap-1">
                    {FORMAT_LABELS[format]}
                    <X
                      className="h-3 w-3 cursor-pointer"
                      onClick={() => toggleFormat(format)}
                    />
                  </Badge>
                ))}
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
                  <div key={i} className="h-80 rounded-xl bg-muted animate-pulse"></div>
                ))}
              </div>
            ) : filteredEvents.length > 0 ? (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  {filteredEvents.map((event) => (
                    <EventCard key={event.uuid} event={event} />
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
                  <CalendarIcon className="h-8 w-8 text-slate-300" />
                </div>
                <h3 className="mt-2 text-lg font-semibold text-foreground">No events found</h3>
                <p className="mt-1 text-muted-foreground max-w-sm mx-auto">
                  {searchTerm || activeFilterCount > 0
                    ? "We couldn't find any events matching your criteria."
                    : "There are no public events available at the moment."}
                </p>
                {(searchTerm || activeFilterCount > 0) && (
                  <div className="mt-6">
                    <Button variant="outline" onClick={resetFilters}>
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

// Event card component for API data
function EventCard({ event }: { event: Event }) {
  return (
    <Link to={`/events/${event.slug || event.uuid}`} className="group block h-full">
      <Card className="h-full overflow-hidden hover:shadow-lg transition-all duration-300 border-border/80 hover:border-primary/50 group-hover:-translate-y-1">
        <div className="h-44 bg-gradient-to-br from-slate-100 to-slate-200 relative flex items-center justify-center overflow-hidden">
          {/* Placeholder Image Logic */}
          <div className="absolute inset-0 bg-blue-600/5 group-hover:bg-blue-600/10 transition-colors"></div>
          <CalendarIcon className="h-10 w-10 text-slate-300 group-hover:scale-110 transition-transform duration-500" />

          <div className="absolute top-3 right-3">
            <Badge
              variant={event.format === "online" ? "secondary" : "default"}
              className="uppercase text-[10px] tracking-wider font-bold shadow-sm backdrop-blur-md bg-card/90 text-foreground border-0"
            >
              {event.format === "in-person" ? "In-Person" : event.format}
            </Badge>
          </div>
          {event.status === "live" && (
            <div className="absolute top-3 left-3">
              <Badge variant="destructive" className="animate-pulse shadow-sm">
                LIVE NOW
              </Badge>
            </div>
          )}
        </div>
        <CardContent className="p-5 flex flex-col h-[calc(100%-11rem)]">
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-3 font-medium uppercase tracking-wider">
            <span className="text-primary font-bold">
              {new Date(event.starts_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
            </span>
            <span>•</span>
            <span>{event.event_type}</span>
          </div>

          <h3 className="font-bold text-lg text-foreground group-hover:text-primary transition-colors line-clamp-2 mb-2 leading-tight">
            {event.title}
          </h3>

          <p className="text-sm text-muted-foreground line-clamp-2 mb-4 flex-1">
            {event.short_description || event.description}
          </p>

          <div className="flex items-center justify-between pt-4 border-t border-border/50 mt-auto">
            {event.cpd_credits && Number(event.cpd_credits) > 0 ? (
              <div className="flex items-center text-xs font-medium text-amber-600 bg-amber-50 px-2 py-1 rounded-md">
                <Award className="h-3 w-3 mr-1" />
                <span>{event.cpd_credits} Credits</span>
              </div>
            ) : (
              <div className="text-xs text-muted-foreground">No Credits</div>
            )}

            {event.registration_enabled ? (
              <span className="text-xs font-semibold text-blue-600 group-hover:underline">View Details</span>
            ) : (
              <span className="text-xs font-medium text-slate-400">Closed</span>
            )}
          </div>

          {event.organization_info ? (
            <div className="mt-3 text-xs text-muted-foreground">
              Hosted by <span className="font-medium text-foreground">{event.organization_info.name}</span>
            </div>
          ) : event.organizer_name ? (
            <div className="mt-3 text-xs text-muted-foreground">
              Hosted by <span className="font-medium text-foreground">{event.organizer_name}</span>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </Link>
  );
}
