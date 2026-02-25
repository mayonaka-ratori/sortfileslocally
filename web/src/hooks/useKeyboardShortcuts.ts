"use client"

import { useEffect, useRef } from "react"

interface ShortcutConfig {
    [key: string]: () => void
}

const isTyping = (e: KeyboardEvent) => {
    const target = e.target as HTMLElement
    const tag = target.tagName
    return tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable
}

export function useKeyboardShortcuts(config: ShortcutConfig) {
    const configRef = useRef(config)

    useEffect(() => {
        configRef.current = config
    })

    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            // Don't fire shortcuts if user is typing
            if (isTyping(e)) return

            const key = e.key.toLowerCase()
            const isShift = e.shiftKey

            // Handle Shift+Key combinations - using capitalized 'Shift+' to match user request style
            const combo = isShift ? `Shift+${e.key}` : key

            // Try combo first, then single key
            if (configRef.current[combo]) {
                e.preventDefault()
                configRef.current[combo]()
            } else if (configRef.current[key]) {
                // Special case for '/' to prevent search bar focus from typing the '/'
                if (key === '/') e.preventDefault()
                configRef.current[key]()
            }
        }

        window.addEventListener("keydown", handleKeyDown)
        return () => window.removeEventListener("keydown", handleKeyDown)
    }, []) // Stable listener
}
