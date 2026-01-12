import "@testing-library/jest-dom";
import { vi } from "vitest";

// Mock react-pdf which requires browser-only globals (DOMMatrix, etc.)
vi.mock("react-pdf", () => ({
    Document: () => null,
    Page: () => null,
    pdfjs: { GlobalWorkerOptions: { workerSrc: "" } },
}));

// Mock DOMMatrix for pdfjs-dist if it gets imported elsewhere
if (typeof globalThis.DOMMatrix === "undefined") {
    globalThis.DOMMatrix = class DOMMatrix {
        constructor() { }
        static fromMatrix() {
            return new DOMMatrix();
        }
    } as unknown as typeof DOMMatrix;
}

// Mock window.matchMedia for theme-provider and other components
Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(), // deprecated
        removeListener: vi.fn(), // deprecated
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
    })),
});

// Mock window.scrollTo
Object.defineProperty(window, "scrollTo", {
    writable: true,
    value: vi.fn(),
});

// Mock ResizeObserver for Radix UI components
global.ResizeObserver = class ResizeObserver {
    observe() { }
    unobserve() { }
    disconnect() { }
};

const suppressedWarnings = [
    "React Router Future Flag Warning: React Router will begin wrapping state updates in `React.startTransition` in v7.",
    "React Router Future Flag Warning: Relative route resolution within Splat routes is changing in v7.",
];
const originalWarn = console.warn;
console.warn = (...args: unknown[]) => {
    const firstArg = args[0];
    if (typeof firstArg === "string" && suppressedWarnings.some((msg) => firstArg.includes(msg))) {
        return;
    }
    originalWarn(...args);
};
