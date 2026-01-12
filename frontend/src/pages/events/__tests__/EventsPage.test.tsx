import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { EventsPage } from "../EventsPage";

// Mock AuthContext
const mockUser = {
    uuid: "test-uuid",
    account_type: "organizer",
    display_name: "Test User",
};

vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({
        user: mockUser,
    }),
}));

// Mock events API
vi.mock("@/api/events", () => ({
    getEvents: vi.fn().mockResolvedValue([]),
    getPublicEvents: vi.fn().mockResolvedValue([]),
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
            expect(screen.getByText("My Events")).toBeInTheDocument();
        });
        expect(screen.getByText(/manage your cpd events/i)).toBeInTheDocument();
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
