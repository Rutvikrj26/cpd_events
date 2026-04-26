import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect } from "vitest";
import {
    Dialog,
    DialogTrigger,
    DialogContent,
    DialogHeader,
    DialogTitle,
    DialogDescription,
    DialogFooter,
    DialogClose,
} from "../dialog";
import { Button } from "../button";

describe("Dialog", () => {
    it("opens when trigger is clicked", async () => {
        const user = userEvent.setup();
        render(
            <Dialog>
                <DialogTrigger asChild>
                    <Button>Open Dialog</Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Test Dialog</DialogTitle>
                        <DialogDescription>This is a test dialog</DialogDescription>
                    </DialogHeader>
                </DialogContent>
            </Dialog>
        );

        // Dialog should not be visible initially
        expect(screen.queryByText("Test Dialog")).not.toBeInTheDocument();

        // Click the trigger
        await user.click(screen.getByRole("button", { name: /open dialog/i }));

        // Dialog should now be visible
        await waitFor(() => {
            expect(screen.getByText("Test Dialog")).toBeInTheDocument();
        });
        expect(screen.getByText("This is a test dialog")).toBeInTheDocument();
    });

    it("closes when close button is clicked", async () => {
        const user = userEvent.setup();
        render(
            <Dialog>
                <DialogTrigger asChild>
                    <Button>Open Dialog</Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Test Dialog</DialogTitle>
                        <DialogDescription>Close dialog description</DialogDescription>
                    </DialogHeader>
                </DialogContent>
            </Dialog>
        );

        // Open the dialog
        await user.click(screen.getByRole("button", { name: /open dialog/i }));

        await waitFor(() => {
            expect(screen.getByText("Test Dialog")).toBeInTheDocument();
        });

        // Click the close button (X icon with sr-only "Close" text)
        const closeButton = screen.getByRole("button", { name: /close/i });
        await user.click(closeButton);

        // Dialog should be closed
        await waitFor(() => {
            expect(screen.queryByText("Test Dialog")).not.toBeInTheDocument();
        });
    });

    it("renders footer with actions", async () => {
        const user = userEvent.setup();
        render(
            <Dialog>
                <DialogTrigger asChild>
                    <Button>Open</Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Confirm Action</DialogTitle>
                        <DialogDescription>Confirm action description</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <DialogClose asChild>
                            <Button variant="outline">Cancel</Button>
                        </DialogClose>
                        <Button>Confirm</Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        );

        await user.click(screen.getByRole("button", { name: /open/i }));

        await waitFor(() => {
            expect(screen.getByRole("button", { name: /cancel/i })).toBeInTheDocument();
            expect(screen.getByRole("button", { name: /confirm/i })).toBeInTheDocument();
        });
    });

    it("closes when DialogClose is clicked", async () => {
        const user = userEvent.setup();
        render(
            <Dialog>
                <DialogTrigger asChild>
                    <Button>Open</Button>
                </DialogTrigger>
                <DialogContent>
                    <DialogHeader>
                        <DialogTitle>Test</DialogTitle>
                        <DialogDescription>Test dialog description</DialogDescription>
                    </DialogHeader>
                    <DialogFooter>
                        <DialogClose asChild>
                            <Button variant="outline">Cancel</Button>
                        </DialogClose>
                    </DialogFooter>
                </DialogContent>
            </Dialog>
        );

        await user.click(screen.getByRole("button", { name: /open/i }));

        await waitFor(() => {
            expect(screen.getByText("Test")).toBeInTheDocument();
        });

        await user.click(screen.getByRole("button", { name: /cancel/i }));

        await waitFor(() => {
            expect(screen.queryByText("Test")).not.toBeInTheDocument();
        });
    });
});
