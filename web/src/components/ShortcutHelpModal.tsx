"use client"

import React from "react"
import { useTranslations } from 'next-intl';
import { motion, AnimatePresence } from "framer-motion"
import { X } from "lucide-react"

interface ShortcutHelpModalProps {
    isOpen: boolean
    onClose: () => void
}

const KeyCap = ({ children }: { children: React.ReactNode }) => (
    <span className="inline-flex items-center justify-center min-w-[24px] px-1.5 py-0.5 text-[10px] font-bold text-zinc-300 bg-zinc-800 border border-zinc-700 rounded shadow-[0_2px_0_0_rgba(0,0,0,0.3)] mr-2">
        {children}
    </span>
)

export function ShortcutHelpModal({ isOpen, onClose }: ShortcutHelpModalProps) {
    const t = useTranslations('shortcuts');

    const shortcutGroups = [
        {
            group: t('groups.global'), items: [
                { key: "/", desc: t('descriptions.focusSearch') },
                { key: "?", desc: t('descriptions.toggleHelp') },
                { key: "Esc", desc: t('descriptions.closeModal') },
            ]
        },
        {
            group: t('groups.gallery'), items: [
                { key: "J", desc: t('descriptions.nextItem') },
                { key: "K", desc: t('descriptions.prevItem') },
                { key: "Enter", desc: t('descriptions.openDetail') },
                { key: "A", desc: t('descriptions.selectAll') },
                { key: "Shift+A", desc: t('descriptions.deselectAll') },
            ]
        },
        {
            group: t('groups.detailView'), items: [
                { key: "F", desc: t('descriptions.toggleFavorite') },
                { key: "T", desc: t('descriptions.focusTagEditor') },
                { key: "E", desc: t('descriptions.openExport') },
            ]
        }
    ]

    return (
        <AnimatePresence>
            {isOpen && (
                <div className="fixed inset-0 z-[100] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-labelledby="shortcuts-title">
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
                        data-testid="shortcut-modal"
                        className="relative w-full max-w-lg bg-zinc-900 border border-zinc-800 rounded-2xl shadow-2xl overflow-hidden"
                    >
                        <div className="p-6 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
                            <h2 id="shortcuts-title" className="text-xl font-bold text-white flex items-center gap-3">
                                <span className="w-8 h-8 rounded-lg bg-indigo-600/20 text-indigo-400 flex items-center justify-center text-lg">?</span>
                                {t('title')}
                            </h2>
                            <button
                                onClick={onClose}
                                className="p-2 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                                aria-label={t('close')}
                                title={t('close')}
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="p-6 max-h-[70vh] overflow-y-auto space-y-8">
                            {shortcutGroups.map((group) => (
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
                            <p className="text-[10px] text-zinc-500 font-medium uppercase tracking-widest">{t('pressEsc', { key: 'Esc' })}</p>
                        </div>
                    </motion.div>
                </div>
            )}
        </AnimatePresence>
    )
}
