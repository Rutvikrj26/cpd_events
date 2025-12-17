import React from "react";
import { Search, Filter, Calendar as CalendarIcon, SlidersHorizontal } from "lucide-react";
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
import { EventCard } from "@/components/custom/EventCard";
import { PageHeader } from "@/components/custom/PageHeader";
import { mockEvents } from "@/lib/mock-data";

export function EventDiscovery() {
  const [searchTerm, setSearchTerm] = React.useState("");
  
  // Filter events based on search term
  const filteredEvents = mockEvents.filter(event => 
    event.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
    event.organizer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="bg-gray-50 min-h-screen py-12">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <PageHeader 
          title="Browse Events" 
          description="Discover professional development opportunities to advance your career."
        />

        <div className="flex flex-col lg:flex-row gap-8">
          {/* Filters Sidebar - Desktop */}
          <div className="hidden lg:block w-64 flex-shrink-0 space-y-8">
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-4">Event Type</h3>
              <div className="space-y-3">
                {["Webinar", "Workshop", "Course", "Conference"].map((type) => (
                  <div key={type} className="flex items-center space-x-2">
                    <Checkbox id={`type-${type}`} />
                    <label 
                      htmlFor={`type-${type}`}
                      className="text-sm text-gray-600 leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {type}
                    </label>
                  </div>
                ))}
              </div>
            </div>
            
            <Separator />

            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-4">Credit Type</h3>
              <div className="space-y-3">
                {["CME", "CLE", "CPE", "General"].map((type) => (
                  <div key={type} className="flex items-center space-x-2">
                    <Checkbox id={`credit-${type}`} />
                    <label 
                      htmlFor={`credit-${type}`}
                      className="text-sm text-gray-600 leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                    >
                      {type}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <Separator />
            
            <div>
              <h3 className="text-sm font-medium text-gray-900 mb-4">Price</h3>
              <div className="space-y-3">
                <div className="flex items-center space-x-2">
                  <Checkbox id="price-free" />
                  <label htmlFor="price-free" className="text-sm text-gray-600">Free</label>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox id="price-paid" />
                  <label htmlFor="price-paid" className="text-sm text-gray-600">Paid</label>
                </div>
              </div>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {/* Search and Sort Bar */}
            <div className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm mb-6 flex flex-col sm:flex-row gap-4 items-center justify-between">
               <div className="relative w-full sm:max-w-md">
                 <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                   <Search className="h-4 w-4 text-gray-400" />
                 </div>
                 <Input 
                   placeholder="Search events, topics, or organizers..." 
                   className="pl-10"
                   value={searchTerm}
                   onChange={(e) => setSearchTerm(e.target.value)}
                 />
               </div>
               
               <div className="flex w-full sm:w-auto items-center gap-2">
                  <Button variant="outline" className="lg:hidden flex-1 sm:flex-none">
                    <Filter className="h-4 w-4 mr-2" />
                    Filters
                  </Button>
                  
                  <Select defaultValue="upcoming">
                    <SelectTrigger className="w-full sm:w-[180px]">
                      <SelectValue placeholder="Sort by" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="upcoming">Date: Upcoming</SelectItem>
                      <SelectItem value="newest">Newest Listed</SelectItem>
                      <SelectItem value="price-low">Price: Low to High</SelectItem>
                    </SelectContent>
                  </Select>
               </div>
            </div>

            {/* Results Grid */}
            {filteredEvents.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                {filteredEvents.map(event => (
                  <EventCard key={event.id} event={event} />
                ))}
              </div>
            ) : (
              <div className="text-center py-20 bg-white rounded-lg border border-gray-200 border-dashed">
                <div className="mx-auto h-12 w-12 text-gray-400">
                  <CalendarIcon className="h-12 w-12" />
                </div>
                <h3 className="mt-2 text-sm font-semibold text-gray-900">No events found</h3>
                <p className="mt-1 text-sm text-gray-500">
                  We couldn't find any events matching your search terms.
                </p>
                <div className="mt-6">
                  <Button variant="outline" onClick={() => setSearchTerm("")}>
                    Clear filters
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
