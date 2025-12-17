import { Plus, Calendar, Clock, MapPin, CheckCircle, Users, Award, PlayCircle, FileText, AlertCircle } from "lucide-react";

export interface Event {
  id: string;
  title: string;
  slug: string;
  description: string;
  organizer: string;
  startDate: string;
  endDate: string;
  startTime: string;
  duration: string;
  status: "draft" | "published" | "live" | "completed" | "cancelled";
  type: "Webinar" | "Workshop" | "Course" | "Conference";
  creditType: string;
  credits: number;
  price: number | "Free";
  image: string;
  attendees: number;
  capacity: number;
  isRegistered?: boolean;
}

export interface Certificate {
  id: string;
  eventId: string;
  eventTitle: string;
  organizer: string;
  issueDate: string;
  creditType: string;
  credits: number;
  status: "issued" | "revoked";
  previewUrl: string;
}

export const mockEvents: Event[] = [
  {
    id: "1",
    title: "Advanced Cardiology Symposium 2024",
    slug: "advanced-cardiology-2024",
    description: "A comprehensive update on the latest guidelines in heart failure management and interventional cardiology.",
    organizer: "Medical Education Institute",
    startDate: "2024-03-15",
    endDate: "2024-03-15",
    startTime: "09:00 AM",
    duration: "6 hours",
    status: "published",
    type: "Conference",
    creditType: "CME",
    credits: 6,
    price: 150,
    image: "https://images.unsplash.com/photo-1576091160399-112ba8d25d1d?auto=format&fit=crop&q=80&w=2070",
    attendees: 145,
    capacity: 200,
    isRegistered: false,
  },
  {
    id: "2",
    title: "Legal Ethics in the Digital Age",
    slug: "legal-ethics-digital",
    description: "Exploring the ethical implications of AI and digital communication in legal practice.",
    organizer: "State Bar Association",
    startDate: "2024-03-20",
    endDate: "2024-03-20",
    startTime: "01:00 PM",
    duration: "2 hours",
    status: "published",
    type: "Webinar",
    creditType: "CLE",
    credits: 2,
    price: 50,
    image: "https://images.unsplash.com/photo-1589829085413-56de8ae18c73?auto=format&fit=crop&q=80&w=2072",
    attendees: 89,
    capacity: 500,
    isRegistered: true,
  },
  {
    id: "3",
    title: "Modern Web Architecture Workshop",
    slug: "modern-web-arch",
    description: "Hands-on workshop building scalable frontend applications with React and Micro-frontends.",
    organizer: "TechFlow Academy",
    startDate: "2024-04-05",
    endDate: "2024-04-05",
    startTime: "10:00 AM",
    duration: "4 hours",
    status: "published",
    type: "Workshop",
    creditType: "Tech CPD",
    credits: 4,
    price: "Free",
    image: "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&q=80&w=2070",
    attendees: 45,
    capacity: 50,
    isRegistered: false,
  },
  {
    id: "4",
    title: "Pediatric Emergency Medicine Review",
    slug: "pediatric-emergency",
    description: "Review of common pediatric emergencies and critical care updates.",
    organizer: "General Hospital Education",
    startDate: "2024-02-28",
    endDate: "2024-02-28",
    startTime: "08:00 AM",
    duration: "8 hours",
    status: "completed",
    type: "Course",
    creditType: "CME",
    credits: 8,
    price: 200,
    image: "https://images.unsplash.com/photo-1516549655169-df83a0926e97?auto=format&fit=crop&q=80&w=2070",
    attendees: 120,
    capacity: 150,
    isRegistered: true,
  }
];

export const mockCertificates: Certificate[] = [
  {
    id: "cert-1",
    eventId: "4",
    eventTitle: "Pediatric Emergency Medicine Review",
    organizer: "General Hospital Education",
    issueDate: "2024-02-29",
    creditType: "CME",
    credits: 8,
    status: "issued",
    previewUrl: "#",
  },
  {
    id: "cert-2",
    eventId: "99",
    eventTitle: "Annual Compliance Training 2023",
    organizer: "Corp Learning",
    issueDate: "2023-12-15",
    creditType: "Compliance",
    credits: 1,
    status: "issued",
    previewUrl: "#",
  }
];

export const mockStats = {
  attendee: {
    totalCredits: 24,
    certificates: 12,
    upcomingEvents: 2,
    requiredCredits: 30,
  },
  organizer: {
    totalEvents: 15,
    activeEvents: 3,
    totalAttendees: 1250,
    certificatesIssued: 1100,
  }
};
