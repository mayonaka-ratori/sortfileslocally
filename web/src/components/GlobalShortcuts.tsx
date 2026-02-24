"use client"

import { useState, useCallback } from "react"
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts"
import { ShortcutHelpModal } from "@/components/ShortcutHelpModal"

export function GlobalShortcuts() {
    const [isHelpOpen, setIsHelpOpen] = useState(false)

    const toggleHelp = useCallback(() => {
        setIsHelpOpen(prev => !prev)
    }, [])

    const focusSearch = useCallback(() => {
        const searchInput = document.querySelector('input[placeholder*="Search"]') as HTMLInputElement
        if (searchInput) {
            searchInput.focus()
            searchInput.select()
        }
    }, [])

    const closeModals = useCallback(() => {
        // If help modal is open, close it
        if (isHelpOpen) {
            setIsHelpOpen(false)
            return
        }

        // Custom event to signal other components to close (like detail view)
        window.dispatchEvent(new CustomEvent('close-modals'))
    }, [isHelpOpen])

    useKeyboardShortcuts({
        '?': toggleHelp,
        '/': focusSearch,
        'escape': closeModals,
    })

    return (
        <ShortcutHelpModal
            isOpen={isHelpOpen}
            onClose={() => setIsHelpOpen(false)}
        />
    )
}
