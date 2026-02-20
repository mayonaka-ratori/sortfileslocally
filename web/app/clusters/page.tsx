
import { Users } from 'lucide-react';

export default function ClustersPage() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] text-center p-8">
            <div className="bg-white/5 rounded-full p-6 mb-4">
                <Users className="w-12 h-12 text-blue-400" />
            </div>
            <h2 className="text-2xl font-bold mb-2">Face Clusters</h2>
            <p className="text-gray-400 max-w-md">
                AI-powered face recognition and clustering interface is coming soon.
                This feature will allow you to organize your collection by people.
            </p>
        </div>
    );
}
