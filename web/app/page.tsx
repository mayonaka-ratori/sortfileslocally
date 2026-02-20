
import Gallery from '@/components/gallery/Gallery';

export default function Home() {
    return (
        <main className="min-h-screen bg-black text-white">
            <header className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-white/10 p-4 flex items-center justify-between">
                <h1 className="text-xl font-bold tracking-tight">LocalCurator Prime</h1>
                <div className="flex gap-4 text-sm text-gray-400">
                    <span>Gallery</span>
                    <span>Clusters</span>
                    <span>Organize</span>
                </div>
            </header>

            <div className="pt-20">
                <Gallery />
            </div>
        </main>
    );
}
