"use client"

import { useEffect } from "react"

interface ShortcutConfig {
    [key: string]: () => void
}

const isTyping = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement
    const tag = target.tagName
    return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable
}

export function useKeyboardShortcuts(config: ShortcutConfig) {
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Don't fire shortcuts if user is typing
            if (isTyping(e)) return

            const key = e.key.toLowerCase()
            const isShift = e.shiftKey

            // Handle Shift+Key combinations if needed
            const combo = isShift ? `shift+${key}` : key

            // Try combo first, then single key
            if (config[combo]) {
                e.preventDefault()
                config[combo]()
            } else if (config[key]) {
                // Special case for '/' to prevent search bar focus from typing the '/'
                if (key === '/') e.preventDefault()
                config[key]()
            }
        }

        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, [config])
}
