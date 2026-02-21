"use client"

import React, { useState, useRef, useEffect } from "react"
import { MediaItem, getOriginalUrl, chatWithImage } from "@/lib/api"
import { X, Send, Loader2 } from "lucide-react"

interface ChatPanelProps {
    item: MediaItem | null
    onClose: () => void
}

interface Message {
    role: "user" | "assistant"
    content: string
}

export function ChatPanel({ item, onClose }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Reset chat when item changes
    useEffect(() => {
        setMessages([])
        if (item) {
            setMessages([
                {
                    role: "assistant",
                    content: "Hi! I'm analyzing this image. What would you like to know?"
                }
            ])
        }
    }, [item])

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages])

    if (!item) return null

    const handleSend = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!input.trim() || isLoading) return

        const userMessage = input.trim()
        setInput("")
        setMessages((prev) => [...prev, { role: "user", content: userMessage }])
        setIsLoading(true)

        try {
            const response = await chatWithImage(item.file_path, userMessage)
            setMessages((prev) => [...prev, { role: "assistant", content: response }])
        } catch (error) {
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Sorry, I encountered an error while analyzing the image." }
            ])
        } finally {
            setIsLoading(false)
        }
    }

    return (
        <div className="w-96 flex flex-col h-full bg-zinc-900 border-l border-zinc-800 shadow-2xl overflow-hidden flex-shrink-0">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/50 px-4">
                <h3 className="font-semibold text-zinc-100 flex items-center gap-2">
                    ✨ Chat with Image
                </h3>
                <button
                    onClick={onClose}
                    className="p-1 hover:bg-zinc-800 rounded-md transition-colors text-zinc-400 hover:text-white"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Image Preview */}
            <div className="relative w-full h-48 bg-black border-b border-zinc-800 flex-shrink-0">
                <img
                    src={getOriginalUrl(item.id)}
                    alt="Selected"
                    className="w-full h-full object-contain"
                />
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg, idx) => (
                    <div
                        key={idx}
                        className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"
                            }`}
                    >
                        <div
                            className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed ${msg.role === "user"
                                    ? "bg-indigo-600 text-white rounded-br-sm"
                                    : "bg-zinc-800 text-zinc-200 rounded-bl-sm"
                                }`}
                        >
                            {msg.content}
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-zinc-800 text-zinc-400 rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2 text-sm">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Thinking...
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 bg-zinc-900 border-t border-zinc-800">
                <form onSubmit={handleSend} className="relative flex items-center">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Ask about this image..."
                        className="w-full bg-zinc-950 border border-zinc-800 rounded-xl py-3 pl-4 pr-12 text-sm text-zinc-100 placeholder-zinc-500 focus:outline-none focus:border-indigo-500 transition-colors"
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="absolute right-2 p-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-zinc-800 disabled:text-zinc-600 text-white rounded-lg transition-colors"
                    >
                        <Send className="w-4 h-4" />
                    </button>
                </form>
            </div>
        </div>
    )
}
