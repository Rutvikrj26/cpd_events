import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { EventsPage } from "../EventsPage";

const mockUser = {
    uuid: "test-uuid",
    roles: ["organizer"],
    primary_role: "organizer",
    display_name: "Test User",
};

vi.mock("@/features/auth", () => ({
    useAuth: () => ({
        user: mockUser,
    }),
}));

// Mock events API. The page expects the paginated `{results: []}` shape;
// returning a bare array makes `data.results` undefined and the page
// crashes silently. Return the canonical shape.
vi.mock("@/api/events", () => ({
    getEvents: vi
        .fn()
        .mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
    getPublicEvents: vi
        .fn()
        .mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
    deleteEvent: vi.fn(),
}));

// Page also imports `duplicateEvent` from a separate module.
vi.mock("@/api/events/actions", () => ({
    duplicateEvent: vi.fn(),
}));

vi.mock("sonner", () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

const renderEventsPage = () => {
    return render(
        <BrowserRouter>
            <EventsPage />
        </BrowserRouter>
    );
};

describe("EventsPage", () => {
    it("renders page header for organizer", async () => {
        renderEventsPage();

        await waitFor(() => {
            expect(screen.getByText("Manage Events")).toBeInTheDocument();
        });
        expect(screen.getByText(/your cpd events/i)).toBeInTheDocument();
    });

    it("has Create Event button for organizer", async () => {
        renderEventsPage();

        await waitFor(() => {
            expect(screen.getByRole("link", { name: /create event/i })).toBeInTheDocument();
        });
    });

    it("shows empty state message when no events", async () => {
        renderEventsPage();

        await waitFor(() => {
            expect(screen.getByText(/no events found/i)).toBeInTheDocument();
        });
    });

    it("Create Event button links to create page", async () => {
        renderEventsPage();

        await waitFor(() => {
            const createButton = screen.getByRole("link", { name: /create event/i });
            expect(createButton).toHaveAttribute("href", "/events/create");
        });
    });

    it("shows loading state initially", async () => {
        renderEventsPage();
        expect(screen.getByText("Loading events...")).toBeInTheDocument();
        await screen.findByText(/no events found/i);
    });
});
