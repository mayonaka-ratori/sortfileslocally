"use client"

import React, { useState, useRef, useEffect } from "react"
import { MediaItem, getOriginalUrl, chatWithImage, FaceData, getFaces, nameFace, exportMetadata } from "@/lib/api"
import { X, Send, Loader2, Users, MessageSquare, Search, Edit2, Check, Save, Settings2 } from "lucide-react"
import Image from "next/image"
import { MetadataExportOptions, ExportMode } from "./MetadataExportOptions"

interface ChatPanelProps {
    item: MediaItem | null
    onClose: () => void
    onFaceSearch?: (faceId: number) => void
}

interface Message {
    role: "user" | "assistant"
    content: string
}

export function ChatPanel({ item, onClose, onFaceSearch }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    const [activeTab, setActiveTab] = useState<"chat" | "faces">("chat")
    const [faces, setFaces] = useState<FaceData[]>([])
    const [editingFaceId, setEditingFaceId] = useState<number | null>(null)
    const [editName, setEditName] = useState("")
    const [isExporting, setIsExporting] = useState(false)
    const [exportMode, setExportMode] = useState<ExportMode>("xmp")
    const [showExportOptions, setShowExportOptions] = useState(false)

    // Reset chat and faces when item changes
    useEffect(() => {
        setMessages([])
        setFaces([])
        setActiveTab("chat")
        setEditingFaceId(null)
        setShowExportOptions(false)
        if (item) {
            setMessages([
                {
                    role: "assistant",
                    content: "Hi! I'm analyzing this image. What would you like to know?"
                }
            ])
            getFaces(item.id).then(setFaces).catch(console.error)
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
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: "Sorry, I encountered an error while analyzing the image." }
            ])
        } finally {
            setIsLoading(false)
        }
    }

    const handleNameFace = async (faceId: number) => {
        if (!editName.trim()) {
            setEditingFaceId(null)
            return
        }
        try {
            await nameFace(faceId, editName.trim())
            setFaces(prev => prev.map(f => f.id === faceId ? { ...f, person_name: editName.trim() } : f))
            setEditingFaceId(null)
        } catch (error) {
            console.error("Failed to name face", error)
        }
    }

    const handleExport = async () => {
        if (!item || isExporting) return
        setIsExporting(true)
        try {
            const result = await exportMetadata([item.id], exportMode)
            if (result.success > 0) {
                alert(`Metadata exported successfully as ${exportMode.toUpperCase()}!`)
                setShowExportOptions(false)
            } else {
                alert("Export failed or no data to export.")
            }
        } catch {
            alert("Export encountered an error.")
        } finally {
            setIsExporting(false)
        }
    }

    return (
        <div className="w-96 flex flex-col h-full bg-zinc-900 border-l border-zinc-800 shadow-2xl overflow-hidden flex-shrink-0 relative">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-zinc-800 bg-zinc-900/50 px-4 shrink-0">
                <div className="flex gap-4">
                    <button
                        onClick={() => setActiveTab("chat")}
                        className={`font-semibold flex items-center gap-2 transition-colors ${activeTab === 'chat' ? 'text-indigo-400' : 'text-zinc-500 hover:text-zinc-300'}`}
                    >
                        <MessageSquare className="w-4 h-4" /> Chat
                    </button>
                    <button
                        onClick={() => setActiveTab("faces")}
                        className={`font-semibold flex items-center gap-2 transition-colors ${activeTab === 'faces' ? 'text-indigo-400' : 'text-zinc-500 hover:text-zinc-300'}`}
                    >
                        <Users className="w-4 h-4" /> Faces {faces.length > 0 && `(${faces.length})`}
                    </button>
                </div>
                <div className="flex gap-2 items-center">
                    <button
                        onClick={() => setShowExportOptions(!showExportOptions)}
                        className={`p-1.5 rounded-md transition-colors ${showExportOptions ? 'bg-indigo-600 text-white' : 'text-zinc-400 hover:text-white hover:bg-zinc-800'}`}
                        title="Export Options"
                    >
                        <Settings2 className="w-4 h-4" />
                    </button>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-zinc-800 rounded-md transition-colors text-zinc-400 hover:text-white"
                        title="Close Panel"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* Export Options Overlay */}
            {showExportOptions && (
                <div className="absolute top-[57px] left-0 right-0 bg-zinc-900 border-b border-zinc-800 p-4 z-20 shadow-xl animate-in slide-in-from-top-4 duration-200">
                    <MetadataExportOptions
                        selectedMode={exportMode}
                        onModeChange={setExportMode}
                        items={item ? [{ file_path: item.file_path }] : []}
                    />
                    <button
                        onClick={handleExport}
                        disabled={isExporting}
                        className="w-full mt-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold py-2 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-lg shadow-indigo-900/40"
                    >
                        {isExporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                        Execute Export
                    </button>
                </div>
            )}

            {/* Image Preview */}
            <div className="relative w-full h-48 bg-black border-b border-zinc-800 flex-shrink-0 group">
                <Image
                    src={getOriginalUrl(item.id)}
                    alt="Selected"
                    width={400}
                    height={300}
                    className="w-full h-full object-contain"
                    unoptimized
                />
            </div>

            {/* Main Content Area */}
            {activeTab === "chat" ? (
                <>
                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
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
                    <div className="p-4 bg-zinc-900 border-t border-zinc-800 flex-shrink-0">
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
                </>
            ) : (
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                    {faces.length === 0 ? (
                        <div className="text-zinc-500 text-sm text-center py-8">
                            No faces detected in this media.
                        </div>
                    ) : (
                        faces.map((face, i) => (
                            <div key={face.id} className="bg-zinc-800/50 border border-zinc-800 rounded-lg p-3 flex items-center justify-between group">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-zinc-700 flex items-center justify-center text-xs text-zinc-400 font-mono">
                                        F{i + 1}
                                    </div>
                                    {editingFaceId === face.id ? (
                                        <div className="flex items-center gap-2">
                                            <input
                                                autoFocus
                                                type="text"
                                                value={editName}
                                                onChange={e => setEditName(e.target.value)}
                                                onKeyDown={e => e.key === 'Enter' && handleNameFace(face.id)}
                                                className="bg-zinc-950 border border-zinc-700 rounded px-2 py-1 text-sm text-white w-32 focus:outline-none focus:border-indigo-500"
                                                placeholder="Name..."
                                            />
                                            <button onClick={() => handleNameFace(face.id)} className="text-green-500 hover:text-green-400">
                                                <Check className="w-4 h-4" />
                                            </button>
                                            <button onClick={() => setEditingFaceId(null)} className="text-zinc-500 hover:text-zinc-400">
                                                <X className="w-4 h-4" />
                                            </button>
                                        </div>
                                    ) : (
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium text-zinc-200">
                                                {face.person_name || "Unknown Person"}
                                            </span>
                                            <span className="text-xs text-zinc-500">
                                                {face.timestamp > 0 ? `@ ${face.timestamp.toFixed(1)}s` : "Image Face"}
                                            </span>
                                        </div>
                                    )}
                                </div>

                                {editingFaceId !== face.id && (
                                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <button
                                            onClick={() => {
                                                setEditName(face.person_name || "")
                                                setEditingFaceId(face.id)
                                            }}
                                            className="p-1.5 hover:bg-zinc-700 text-zinc-400 rounded transition-colors"
                                            title="Edit Name"
                                        >
                                            <Edit2 className="w-4 h-4" />
                                        </button>
                                        <button
                                            onClick={() => onFaceSearch && onFaceSearch(face.id)}
                                            className="p-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded transition-colors"
                                            title="Search for this person"
                                        >
                                            <Search className="w-4 h-4" />
                                        </button>
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    )
}
