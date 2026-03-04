"use client"

import React, { Component, ErrorInfo, ReactNode } from "react"
import { AlertCircle, RefreshCcw } from "lucide-react"

interface Props {
    children?: ReactNode
}

interface State {
    hasError: boolean
    error: Error | null
}

export class GlobalErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null
    }

    public static getDerivedStateFromError(error: Error): State {
        // Update state so the next render will show the fallback UI.
        return { hasError: true, error }
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo)
    }

    private handleReload = () => {
        window.location.reload()
    }

    public render() {
        if (this.state.hasError) {
            const isNetworkError =
                this.state.error?.message?.includes("Failed to fetch") ||
                this.state.error?.message?.includes("NetworkError") ||
                this.state.error?.message?.includes("Load failed");

            return (
                <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
                    <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-md w-full shadow-2xl flex flex-col items-center text-center">
                        <div className="w-12 h-12 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
                            <AlertCircle className="w-6 h-6 text-red-500" />
                        </div>

                        <h2 className="text-lg font-semibold text-zinc-100 mb-2">
                            {isNetworkError ? "バックエンドに接続できません" : "予期せぬエラーが発生しました"}
                        </h2>

                        <p className="text-sm text-zinc-400 mb-6">
                            {isNetworkError
                                ? "バックエンドプロセスが停止しているか、通信に問題があります。"
                                : this.state.error?.message || "アプリケーションをリロードしてもう一度お試しください。"}
                        </p>

                        <button
                            onClick={this.handleReload}
                            className="bg-zinc-100 hover:bg-white text-zinc-900 px-4 py-2 rounded-lg font-medium text-sm flex items-center gap-2 transition-colors"
                        >
                            <RefreshCcw className="w-4 h-4" />
                            再読み込み / Reload
                        </button>
                    </div>
                </div>
            )
        }

        return this.props.children
    }
}
