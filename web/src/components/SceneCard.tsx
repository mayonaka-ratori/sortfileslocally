"use client";

import Image from "next/image";
import { Scene } from "@/lib/api";
import { useTranslations } from "next-intl";
import { formatTime, cn } from "@/lib/utils";
import { motion } from "framer-motion";

interface SceneCardProps {
    scene: Scene;
    isActive?: boolean;
    onClick?: () => void;
}

export function SceneCard({ scene, isActive, onClick }: SceneCardProps) {
    const t = useTranslations("scenes");
    return (
        <motion.div
            whileHover={{ scale: 1.03 }}
            transition={{ duration: 0.2 }}
            onClick={onClick}
            className={cn(
                "flex-none w-[200px] cursor-pointer rounded-lg overflow-hidden border-2 bg-zinc-900 transition-colors",
                isActive ? "border-blue-500 shadow-lg shadow-blue-500/20" : "border-transparent hover:border-zinc-700"
            )}
        >
            <div className="relative aspect-video w-full overflow-hidden">
                <Image
                    src={scene.thumbnail_url}
                    alt={scene.caption || t("sceneIndex", { index: scene.scene_index })}
                    fill
                    className="object-cover"
                    sizes="200px"
                />
                <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-medium text-white backdrop-blur-sm">
                    {formatTime(scene.start_time)} – {formatTime(scene.end_time)}
                </div>
            </div>

            <div className="p-3">
                <p className="text-xs text-zinc-200 line-clamp-2 min-h-[2.5rem] leading-relaxed mb-2">
                    {scene.caption || t("noCaption")}
                </p>

                <div className="flex flex-wrap gap-1">
                    {scene.tags.slice(0, 3).map((tag, i) => (
                        <span
                            key={i}
                            className="px-1.5 py-0.5 rounded-md bg-zinc-800 text-[10px] text-zinc-400 font-medium"
                        >
                            #{tag}
                        </span>
                    ))}
                    {scene.tags.length > 3 && (
                        <span className="px-1.5 py-0.5 rounded-md bg-zinc-800 text-[10px] text-zinc-400 font-medium font-mono">
                            +{scene.tags.length - 3}
                        </span>
                    )}
                </div>
            </div>
        </motion.div>
    );
}
