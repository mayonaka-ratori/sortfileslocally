"use client"

import React from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

interface ShortcutHelpModalProps {
    isOpen: boolean
    onClose: () => void
}

const shortcuts = [
    {
        group: "Global", items: [
            { key: "/", desc: "Focus search bar" },
            { key: "?", desc: "Toggle shortcut help" },
            { key: "Esc", desc: "Close modal/detail view" },
        ]
    },
    {
        group: "Gallery", items: [
            { key: "J", desc: "Select next item" },
            { key: "K", desc: "Select previous item" },
            { key: "Enter", desc: "Open detail view" },
            { key: "A", desc: "Select all visible items" },
            { key: "Shift+A", desc: "Deselect all" },
        ]
    },
    {
        group: "Detail View", items: [
            { key: "F", desc: "Toggle favorite" },
            { key: "T", desc: "Focus tag editor" },
            { key: "E", desc: "Open export modal" },
        ]
    }
]

const KeyCap = ({ children }: { children: React.ReactNode }) => (
    <span className="inline-flex items-center justify-center min-w-[24px] px-1.5 py-0.5 text-[10px] font-bold text-zinc-300 bg-zinc-800 border border-zinc-700 rounded shadow-[0_2px_0_0_rgba(0,0,0,0.3)] mr-2">
        {children}
    </span>
)

export function ShortcutHelpModal({ isOpen, onClose }: ShortcutHelpModalProps) {
    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    />
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95, y: 20 }}
                        className="relative w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden"
                    >
                        <div className="p-6 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
                            <h2 className="text-xl font-bold text-white flex items-center gap-3">
                                <span className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-lg">?</span>
                                Keyboard Shortcuts
                            </h2>
                            <button
                                onClick={onClose}
                                className="p-2 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                                title="Close"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-6 max-h-[70vh] overflow-y-auto space-y-8">
                            {shortcuts.map((group) => (
                                <div key={group.group}>
                                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-zinc-500 mb-4 px-1">{group.group}</h3>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-4">
                                        {group.items.map((item) => (
                                            <div key={item.key} className="flex items-center justify-between py-1 border-b border-zinc-800/50 group">
                                                <span className="text-sm text-zinc-400 group-hover:text-zinc-200 transition-colors">{item.desc}</span>
                                                <div className="flex items-center">
                                                    {item.key.split('+').map((k, i, arr) => (
                                                        <React.Fragment key={k}>
                                                            <KeyCap>{k}</KeyCap>
                                                            {i < arr.length - 1 && <span className="text-zinc-600 text-[10px] mr-2">+</span>}
                                                        </React.Fragment>
                                                    ))}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>

                        <div className="p-4 bg-zinc-950/50 border-t border-zinc-800 text-center">
                            <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest">Press <span className="text-zinc-400">Esc</span> to close</p>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}
