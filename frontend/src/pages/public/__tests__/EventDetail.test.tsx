import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { EventDetail } from "../EventDetail";

// Mock the API calls. The page also imports `getPublicEvents` (related
// events sidebar), and `getMyRegistrations` is paginated — a bare array
// crashes `.results.find`.
vi.mock("@/api/events", () => ({
    getPublicEvent: vi.fn().mockRejectedValue(new Error("Not found")),
    getPublicEvents: vi
        .fn()
        .mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

vi.mock("@/api/registrations", () => ({
    getMyRegistrations: vi
        .fn()
        .mockResolvedValue({ results: [], count: 0, next: null, previous: null }),
}));

vi.mock("@/features/auth", () => ({
    useAuth: () => ({
        isAuthenticated: false,
        user: null,
    }),
}));

vi.mock("sonner", () => ({
    toast: { success: vi.fn(), error: vi.fn() },
}));

const renderEventDetail = (id = "test-event-id") => {
    return render(
        // The page is mounted at `/events/:id/details`. The previous
        // pattern was `/events/:id` (no trailing segment), so the route
        // never matched and the page never rendered — body was empty.
        <MemoryRouter initialEntries={[`/events/${id}/details`]}>
            <Routes>
                <Route path="/events/:id/details" element={<EventDetail />} />
            </Routes>
        </MemoryRouter>
    );
};

describe("EventDetail", () => {
    let consoleError: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
        consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    });

    afterEach(() => {
        consoleError.mockRestore();
    });

    it("shows loading state initially", async () => {
        renderEventDetail();
        expect(document.querySelector(".animate-spin")).toBeInTheDocument();
        await screen.findByText("Event Not Found");
    });

    it("shows error state when event not found", async () => {
        renderEventDetail();

        expect(await screen.findByText("Event Not Found")).toBeInTheDocument();
        // The error-state CTA in the page goes to `/events` (not the
        // public discovery route).
        expect(
            screen.getByRole("link", { name: /browse events/i })
        ).toHaveAttribute("href", "/events");
    });
});
