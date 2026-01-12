import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import type { ReactElement } from "react";

// Helper to wrap components with necessary providers
const renderWithRouter = (component: ReactElement) => {
    // App already includes BrowserRouter, so we render it directly
    return render(component);
};

describe("App", () => {
    it("renders without crashing", () => {
        // App includes all providers internally, so we just render it
        render(<App />);
        // Basic smoke test - the app should render without throwing
        expect(document.body).toBeDefined();
    });
});
