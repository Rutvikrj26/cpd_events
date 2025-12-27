import React from "react";
import { Link } from "react-router-dom";
import { Calendar, Clock, MapPin, Users, Video } from "lucide-react";
import { Card, CardContent, CardFooter, CardHeader } from "../ui/card";
import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { AspectRatio } from "../ui/aspect-ratio";
import { Event } from "@/lib/mock-data";
import { StatusBadge } from "./StatusBadge";

interface EventCardProps {
  event: Event;
  variant?: "default" | "compact" | "horizontal";
  showStatus?: boolean;
}

export function EventCard({ event, variant = "default", showStatus = false }: EventCardProps) {
  if (variant === "horizontal") {
    return (
      <Card className="flex flex-col sm:flex-row overflow-hidden hover:shadow-md transition-shadow duration-200">
        <div className="w-full sm:w-48 h-32 sm:h-auto relative">
          <img
            src={event.image}
            alt={event.title}
            className="absolute inset-0 h-full w-full object-cover"
          />
        </div>
        <div className="flex-1 flex flex-col justify-between p-4">
          <div className="space-y-2">
            <div className="flex items-start justify-between gap-2">
              <div className="space-y-1">
                <div className="flex items-center gap-2 text-xs text-primary font-medium">
                  {event.type} • {event.creditType} {event.credits} Credits
                </div>
                <h3 className="font-semibold text-lg text-foreground line-clamp-1">{event.title}</h3>
              </div>
              {showStatus && <StatusBadge status={event.status} />}
            </div>
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                <Calendar className="h-4 w-4" />
                <span>{new Date(event.startDate).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                <span>{event.startTime}</span>
              </div>
              <div className="flex items-center gap-1">
                <Users className="h-4 w-4" />
                <span>{event.organizer}</span>
              </div>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <div className="text-sm font-medium text-foreground">
              {event.price === "Free" ? "Free" : `$${event.price}`}
            </div>
            <Link to={`/events/${event.id}`}>
              <Button size="sm" variant="outline">View Details</Button>
            </Link>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <Card className="flex flex-col h-full overflow-hidden hover:shadow-md transition-shadow duration-200">
      <div className="relative">
        <AspectRatio ratio={16 / 9}>
          <img
            src={event.image}
            alt={event.title}
            className="h-full w-full object-cover"
          />
        </AspectRatio>
        <div className="absolute top-2 left-2 flex gap-2">
          <Badge className="bg-card/90 text-foreground hover:bg-card/90 font-medium shadow-sm backdrop-blur-sm border-0">
            {event.type}
          </Badge>
          {showStatus && <StatusBadge status={event.status} className="shadow-sm backdrop-blur-sm" />}
        </div>
        <div className="absolute top-2 right-2">
          <Badge className="bg-primary text-primary-foreground hover:bg-primary/90 font-medium shadow-sm border-0">
            {event.credits} {event.creditType}
          </Badge>
        </div>
      </div>

      <CardHeader className="p-4 pb-2 space-y-2">
        <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
          {new Date(event.startDate).toLocaleDateString(undefined, { month: 'short', day: 'numeric', weekday: 'short' })}
        </div>
        <h3 className="font-semibold text-lg text-foreground line-clamp-2 leading-tight min-h-[3rem]">
          {event.title}
        </h3>
      </CardHeader>

      <CardContent className="p-4 py-2 flex-1">
        <div className="space-y-2 text-sm text-muted-foreground">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 shrink-0" />
            <span className="truncate">{event.organizer}</span>
          </div>
          <div className="flex items-center gap-2">
            <Video className="h-4 w-4 shrink-0" />
            <span>Online Event</span>
          </div>
        </div>
      </CardContent>

      <CardFooter className="p-4 pt-2 flex items-center justify-between border-t border-gray-50 mt-auto">
        <span className="font-semibold text-foreground">
          {event.price === "Free" ? "Free" : `$${event.price}`}
        </span>
        <Link to={`/events/${event.id}`}>
          <Button size="sm" className="bg-gray-900 text-white hover:bg-gray-800">
            Details
          </Button>
        </Link>
      </CardFooter>
    </Card>
  );
}
