import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { EventDetail } from "../EventDetail";

// Mock the API calls
vi.mock("@/api/events", () => ({
    getPublicEvent: vi.fn().mockRejectedValue(new Error("Not found")),
}));

vi.mock("@/api/registrations", () => ({
    getMyRegistrations: vi.fn().mockResolvedValue([]),
}));

vi.mock("@/contexts/AuthContext", () => ({
    useAuth: () => ({
        isAuthenticated: false,
        user: null,
    }),
}));

const renderEventDetail = (id = "test-event-id") => {
    return render(
        <MemoryRouter initialEntries={[`/events/${id}`]}>
            <Routes>
                <Route path="/events/:id" element={<EventDetail />} />
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

        // The component shows a loader while fetching
        expect(document.querySelector(".animate-spin")).toBeInTheDocument();
        await screen.findByText("Event Not Found");
    });

    it("shows error state when event not found", async () => {
        renderEventDetail();

        // Wait for the error state
        expect(await screen.findByText("Event Not Found")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: /browse events/i })).toHaveAttribute(
            "href",
            "/events/browse"
        );
    });
});
