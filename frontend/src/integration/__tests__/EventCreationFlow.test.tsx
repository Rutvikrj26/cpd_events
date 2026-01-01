import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "@/App";
import * as accountsApi from "@/api/accounts";
import * as eventsApi from "@/api/events";
import * as manifestApi from "@/api/auth/manifest";

// Mock API modules
vi.mock("@/api/accounts");
vi.mock("@/api/events");
vi.mock("@/api/auth/manifest");
vi.mock("@/lib/auth");

// Mock ScrollToTop
vi.mock("@/components/layout/ScrollToTop", () => ({
    default: () => null,
}));

// Mock ReactQuill to simple textarea
vi.mock("react-quill", () => ({
    default: ({ value, onChange, placeholder }: any) => (
        <textarea
            data-testid="quill-editor"
            placeholder={placeholder}
            value={value}
            onChange={(e) => onChange(e.target.value)}
        />
    ),
}));

// Mock DateTimePicker
vi.mock("@/components/ui/date-time-picker", () => ({
    DateTimePicker: ({ value, onDateTimeChange, label }: any) => (
        <div>
            <label>{label}</label>
            <input
                data-testid="date-picker-input"
                value={value || ""}
                onChange={(e) => onDateTimeChange(e.target.value)}
            />
        </div>
    ),
}));

// Mock Select component to simplify testing (Radix UI issues in JSDOM)
vi.mock("@/components/ui/select", () => ({
    Select: ({ onValueChange, value, children }: any) => (
        <div data-testid="mock-select-container">
            <select
                data-testid="mock-select"
                value={value}
                onChange={(e) => onValueChange(e.target.value)}
            >
                {children}
            </select>
        </div>
    ),
    SelectTrigger: ({ children }: any) => <div>{children}</div>,
    SelectValue: () => null,
    SelectContent: ({ children }: any) => <>{children}</>,
    SelectItem: ({ value, children }: any) => <option value={value}>{children}</option>,
}));

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
    observe() { }
    unobserve() { }
    disconnect() { }
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation(query => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// Mock scrollIntoView and Pointer capture for Radix UI
window.HTMLElement.prototype.scrollIntoView = vi.fn();
window.HTMLElement.prototype.hasPointerCapture = vi.fn(() => false);
window.HTMLElement.prototype.setPointerCapture = vi.fn();
window.HTMLElement.prototype.releasePointerCapture = vi.fn();

class MockPointerEvent extends Event {
    button: number;
    ctrlKey: boolean;
    metaKey: boolean;
    shiftKey: boolean;
    altKey: boolean;
    constructor(type: string, props: any) {
        super(type, props);
        this.button = props?.button || 0;
        this.ctrlKey = props?.ctrlKey || false;
        this.metaKey = props?.metaKey || false;
        this.shiftKey = props?.shiftKey || false;
        this.altKey = props?.altKey || false;
    }
}
global.PointerEvent = MockPointerEvent as any;

describe("Integration: Event Creation Flow", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        window.history.pushState({}, "Event Create", "/events/create");

        // Default manifest mock
        (manifestApi.getManifest as any).mockResolvedValue({
            routes: ["dashboard", "events", "profile"],
            features: {},
        });
    });

    it("completes event creation wizard", async () => {
        const user = userEvent.setup();

        // 1. Mock api responses
        (accountsApi.getCurrentUser as any).mockResolvedValue({
            uuid: "org-user-id",
            email: "organizer@example.com",
            account_type: "organizer",
            first_name: "Organizer",
            last_name: "User",
            display_name: "Organizer User"
        });

        (eventsApi.createEvent as any).mockResolvedValue({
            uuid: "new-event-uuid",
            title: "New Integration Event",
            slug: "new-integration-event"
        });

        (eventsApi.getEventSessions as any).mockResolvedValue([]);
        (eventsApi.getEvents as any).mockResolvedValue([]); // Prevent EventsPage crash on redirect

        render(<App />);

        // WAIT for page
        await waitFor(() => {
            expect(screen.getByText("Create New Event")).toBeInTheDocument();
        }, { timeout: 3000 });

        // Step 1: Basic Info should be visible
        expect(screen.getByText("Basic Information")).toBeInTheDocument();

        // --- STEP 1: Basic Info ---
        // Fill Title
        const titleInput = screen.getByLabelText(/event title/i);
        await user.clear(titleInput);
        await user.type(titleInput, "New Integration Event");

        // Fill Event Type
        const selects = screen.getAllByTestId("mock-select");
        const typeSelect = selects[0];
        await user.selectOptions(typeSelect, "webinar"); // Value is lowercase based on StepBasicInfo

        // Fill Format
        const formatSelect = selects[1];
        await user.selectOptions(formatSelect, "online"); // Value is lowercase

        // Verify values
        expect(titleInput).toHaveValue("New Integration Event");
        expect(typeSelect).toHaveValue("webinar");
        expect(formatSelect).toHaveValue("online");

        // Click Next
        const nextBtn = screen.getByRole("button", { name: /next/i });
        fireEvent.click(nextBtn);

        // Verify transition
        await waitFor(() => {
            expect(screen.queryByText("Basic Information")).not.toBeInTheDocument();
            expect(screen.getByRole("heading", { name: "Schedule" })).toBeInTheDocument();
        });

        // --- STEP 2: Schedule ---
        // Wait for form to settle
        await waitFor(() => {
            expect(screen.getByText("Start Date & Time")).toBeInTheDocument();
        });

        // Fill Date using mocked input
        const dateInput = screen.getByTestId("date-picker-input");
        await user.clear(dateInput);
        await user.type(dateInput, "2025-01-01T10:00:00.000Z"); // Type raw value into mocked input?
        // Wait, mocked input is simple input. user.type might behave weirdly with date string?
        // user.type is simulating keystrokes.
        // If input is text (default), it's fine.

        // Fill Duration (1 hour) to pass validation (min 15 mins)
        // Find inputs by type="number" inside the Duration section?
        // StepSchedule has two inputs.
        // Let's use getByLabelText if possible or generic input.
        // Label "Duration" is above them.
        // They have class "w-20".
        // Let's use user.type on specific inputs found by value maybe?
        const inputs = screen.getAllByRole("spinbutton");
        // Typically DatePicker might have inputs? No, mocked as text input.
        // So spinbuttons are Duration Hour and Min.
        const hourInput = inputs[0];
        await user.clear(hourInput);
        await user.type(hourInput, "1");

        // Click Next
        await user.click(screen.getByRole("button", { name: /next/i }));

        // --- STEP 3: Details ---
        await waitFor(() => {
            expect(screen.getByText("Event Details")).toBeInTheDocument();
        });

        // Fill description (mocked quill)
        const quill = screen.getByTestId("quill-editor");
        await user.type(quill, "This is a test description.");

        // Click Next
        await user.click(screen.getByRole("button", { name: /next/i }));

        // --- STEP 4: Settings ---
        await waitFor(() => {
            expect(screen.getByText("Settings")).toBeInTheDocument();
        });

        // Click Next
        await user.click(screen.getByRole("button", { name: /next/i }));

        // --- STEP 5: Review ---
        await waitFor(() => {
            expect(screen.getByText("Review & Create")).toBeInTheDocument();
        });

        // Click Create Event
        const createBtn = screen.getByRole("button", { name: /create event/i });
        await user.click(createBtn);

        // Verify API call
        await waitFor(() => {
            expect(eventsApi.createEvent).toHaveBeenCalledWith(expect.objectContaining({
                title: "New Integration Event",
                description: "This is a test description."
            }));
        });
    });
});
