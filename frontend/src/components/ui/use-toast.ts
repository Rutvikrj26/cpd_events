// Compatibility shim: forwards the legacy shadcn `useToast` / `toast` API to Sonner.
// The shadcn toaster was removed in favour of Sonner; this shim avoids touching
// the ~50 existing call sites that still pass `{ title, description, variant }`.
import * as React from "react"
import { toast as sonnerToast, type ExternalToast } from "sonner"

type LegacyToastInput = {
    title?: React.ReactNode
    description?: React.ReactNode
    variant?: "default" | "destructive"
    duration?: number
    action?: React.ReactNode
}

function asString(node: React.ReactNode): string | undefined {
    return typeof node === "string" ? node : undefined
}

export function toast(input: LegacyToastInput) {
    const headline = asString(input.title) ?? asString(input.description) ?? ""
    const opts: ExternalToast = {}
    if (input.description !== undefined && input.title !== undefined) {
        opts.description = input.description as ExternalToast["description"]
    }
    if (input.duration !== undefined) opts.duration = input.duration
    if (input.action !== undefined) opts.action = input.action as ExternalToast["action"]
    if (input.variant === "destructive") return sonnerToast.error(headline, opts)
    return sonnerToast(headline, opts)
}

export function useToast() {
    return {
        toast,
        dismiss: (id?: string | number) => sonnerToast.dismiss(id),
    }
}
