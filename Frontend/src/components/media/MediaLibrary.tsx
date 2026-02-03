/**
 * Media Library Component - PRO LEVEL ⚡
 * 
 * Features:
 * - Premium card design with glassmorphism
 * - Lazy loading (only visible videos)
 * - Thumbnail-first with gradient overlay
 * - Play on hover/click
 * - Redis cached backend
 * - Debounced search
 * - Error handling with retry
 * - Smooth animations
 * - Responsive design
 * - Delete media support
 */
import { useState, useEffect, useRef, useCallback, memo } from 'react';
import { Heart, Music, Loader2, Play, AlertCircle, RefreshCw, ExternalLink, Clock, Disc3, Trash2, MoreVertical, Share2, Copy, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";

// 🔧 DEBUG MODE - Set to false in production
const DEBUG = false;
const log = (...args: unknown[]) => DEBUG && console.log('[MediaLibrary]', ...args);
const logError = (...args: unknown[]) => console.error('[MediaLibrary]', ...args);

interface MediaItem {
    video_id: string;
    title: string;
    artist?: string;
    query: string;
    thumbnail: string;
    category: string;
    plays: number;
    last_played: string;
    is_favorite?: boolean;
}

interface MediaLibraryProps {
    searchQuery?: string;
    filter?: 'all' | 'favorite';
}

// 🎨 Premium Media Card Component - Minimal & Elegant
const MediaCard = memo(({
    media,
    onToggleFavorite,
    onDelete,
    index
}: {
    media: MediaItem;
    onToggleFavorite: (id: string, status: boolean) => void;
    onDelete: (id: string) => void;
    index: number;
}) => {
    const [isPlaying, setIsPlaying] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [imageError, setImageError] = useState(false);
    const [copied, setCopied] = useState(false);
    const [embedFailed, setEmbedFailed] = useState(false);
    const cardRef = useRef<HTMLDivElement>(null);

    const formatDate = (dateStr: string) => {
        if (!dateStr) return 'Recently';
        try {
            const date = new Date(dateStr);
            const now = new Date();
            const diffMs = now.getTime() - date.getTime();
            const diffMins = Math.floor(diffMs / 60000);
            if (diffMins < 1) return 'Just now';
            if (diffMins < 60) return `${diffMins}m`;
            if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h`;
            return `${Math.floor(diffMins / 1440)}d`;
        } catch {
            return 'Recently';
        }
    };

    // High quality thumbnail
    const thumbnailUrl = !imageError && media.thumbnail
        ? media.thumbnail
        : `https://img.youtube.com/vi/${media.video_id}/hqdefault.jpg`;

    const handlePlayClick = () => setIsPlaying(true);
    
    const handleOpenExternal = (e: React.MouseEvent) => {
        e.stopPropagation();
        window.open(`https://www.youtube.com/watch?v=${media.video_id}`, '_blank', 'noopener,noreferrer');
    };

    const handleCopyLink = (e: React.MouseEvent) => {
        e.stopPropagation();
        navigator.clipboard.writeText(`https://www.youtube.com/watch?v=${media.video_id}`);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleShare = async (e: React.MouseEvent) => {
        e.stopPropagation();
        if (navigator.share) {
            try {
                await navigator.share({ title: media.title || media.query, url: `https://www.youtube.com/watch?v=${media.video_id}` });
            } catch { handleCopyLink(e); }
        } else { handleCopyLink(e); }
    };

    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        onDelete(media.video_id);
    };

    return (
        <motion.div
            ref={cardRef}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, delay: Math.min(index * 0.04, 0.2) }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="group relative"
        >
            {/* Main Card Container */}
            <div className={cn(
                "relative rounded-2xl overflow-hidden transition-all duration-300",
                "bg-black/40 backdrop-blur-xl",
                "border border-white/[0.08] hover:border-white/20",
                "shadow-[0_2px_20px_rgba(0,0,0,0.3)]",
                isHovered && "shadow-[0_8px_40px_rgba(0,0,0,0.5)] -translate-y-0.5"
            )}>
                {/* Video Container - 16:9 Aspect Ratio */}
                <div className="relative w-full" style={{ paddingBottom: '56.25%' }}>
                    <div className="absolute inset-0">
                        {isPlaying && !embedFailed ? (
                            // YouTube Player
                            <iframe
                                src={`https://www.youtube.com/embed/${media.video_id}?autoplay=1&rel=0&modestbranding=1&playsinline=1&fs=1`}
                                title={media.title}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
                                allowFullScreen
                                className="w-full h-full"
                                style={{ border: 'none' }}
                                onError={() => setEmbedFailed(true)}
                            />
                        ) : isPlaying && embedFailed ? (
                            // Fallback when embed fails
                            <div className="w-full h-full flex flex-col items-center justify-center bg-gradient-to-br from-zinc-900 to-black gap-3 p-4">
                                <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 flex items-center justify-center">
                                    <AlertCircle className="w-6 h-6 text-red-400" />
                                </div>
                                <p className="text-xs text-white/50 text-center">Can't play here</p>
                                <button
                                    onClick={handleOpenExternal}
                                    className="px-4 py-2 rounded-full bg-white text-black text-xs font-semibold hover:bg-white/90 transition-colors flex items-center gap-1.5"
                                >
                                    <Play className="w-3 h-3 fill-black" />
                                    Watch on YouTube
                                </button>
                            </div>
                        ) : (
                            // Thumbnail View
                            <div className="relative w-full h-full cursor-pointer" onClick={handlePlayClick}>
                                {/* Loading Skeleton */}
                                {!imageLoaded && (
                                    <div className="absolute inset-0 bg-gradient-to-br from-zinc-800 to-zinc-900 animate-pulse flex items-center justify-center">
                                        <Disc3 className="w-8 h-8 text-white/20 animate-spin" />
                                    </div>
                                )}
                                
                                {/* Thumbnail Image */}
                                <img
                                    src={thumbnailUrl}
                                    alt={media.title}
                                    onLoad={() => setImageLoaded(true)}
                                    onError={() => { setImageError(true); setImageLoaded(true); }}
                                    className={cn(
                                        "w-full h-full object-cover transition-all duration-700",
                                        imageLoaded ? "opacity-100" : "opacity-0",
                                        isHovered && "scale-[1.03]"
                                    )}
                                    loading="lazy"
                                />
                                
                                {/* Gradient Overlays */}
                                <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/20 to-transparent" />
                                
                                {/* Play Button - Center */}
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <motion.div
                                        initial={{ scale: 0.9 }}
                                        animate={{ scale: isHovered ? 1.05 : 1 }}
                                        whileTap={{ scale: 0.95 }}
                                        className={cn(
                                            "w-12 h-12 rounded-full flex items-center justify-center",
                                            "bg-white/95 shadow-2xl",
                                            "transition-all duration-300",
                                            isHovered && "bg-white shadow-[0_0_30px_rgba(255,255,255,0.3)]"
                                        )}
                                    >
                                        <Play className="w-5 h-5 text-black ml-0.5 fill-black" />
                                    </motion.div>
                                </div>

                                {/* Top Actions Bar */}
                                <div className="absolute top-0 left-0 right-0 p-2.5 flex items-center justify-between">
                                    {/* Duration/Quality Badge */}
                                    <motion.div
                                        initial={{ opacity: 0, x: -10 }}
                                        animate={{ opacity: isHovered ? 1 : 0.7, x: 0 }}
                                        className="px-2 py-0.5 rounded-md bg-black/60 backdrop-blur-md text-[10px] font-bold text-white/90 tracking-wide"
                                    >
                                        HD
                                    </motion.div>

                                    {/* Action Buttons */}
                                    <motion.div 
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: isHovered ? 1 : 0 }}
                                        className="flex items-center gap-1.5"
                                    >
                                        {/* Favorite */}
                                        <button
                                            onClick={(e) => { e.stopPropagation(); onToggleFavorite(media.video_id, media.is_favorite || false); }}
                                            className={cn(
                                                "w-7 h-7 rounded-full flex items-center justify-center transition-all",
                                                media.is_favorite
                                                    ? "bg-red-500 text-white"
                                                    : "bg-black/50 hover:bg-black/70 text-white/80 hover:text-white backdrop-blur-sm"
                                            )}
                                        >
                                            <Heart className={cn("w-3.5 h-3.5", media.is_favorite && "fill-current")} />
                                        </button>

                                        {/* Menu */}
                                        <DropdownMenu>
                                            <DropdownMenuTrigger asChild>
                                                <button
                                                    onClick={(e) => e.stopPropagation()}
                                                    className="w-7 h-7 rounded-full flex items-center justify-center bg-black/50 hover:bg-black/70 backdrop-blur-sm text-white/80 hover:text-white transition-all"
                                                >
                                                    <MoreVertical className="w-3.5 h-3.5" />
                                                </button>
                                            </DropdownMenuTrigger>
                                            <DropdownMenuContent align="end" className="min-w-[140px]">
                                                <DropdownMenuItem onClick={handleOpenExternal} className="gap-2 text-xs">
                                                    <ExternalLink className="w-3.5 h-3.5" />
                                                    Watch on YouTube
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={handleCopyLink} className="gap-2 text-xs">
                                                    {copied ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                                                    {copied ? "Copied!" : "Copy Link"}
                                                </DropdownMenuItem>
                                                <DropdownMenuItem onClick={handleShare} className="gap-2 text-xs">
                                                    <Share2 className="w-3.5 h-3.5" />
                                                    Share
                                                </DropdownMenuItem>
                                                <DropdownMenuSeparator />
                                                <DropdownMenuItem onClick={handleDelete} className="gap-2 text-xs text-red-400 focus:text-red-400">
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                    Remove
                                                </DropdownMenuItem>
                                            </DropdownMenuContent>
                                        </DropdownMenu>
                                    </motion.div>
                                </div>

                                {/* Bottom Info */}
                                <div className="absolute bottom-0 left-0 right-0 p-3">
                                    <h4 className="font-semibold text-sm text-white line-clamp-2 leading-snug drop-shadow-lg">
                                        {media.title || media.query || 'Untitled'}
                                    </h4>
                                    {media.artist && (
                                        <p className="text-[11px] text-white/60 mt-1 line-clamp-1 font-medium">
                                            {media.artist}
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Footer Stats - Minimal */}
                <div className="px-3 py-2.5 flex items-center justify-between border-t border-white/[0.05]">
                    <div className="flex items-center gap-4 text-[11px] text-white/40 font-medium">
                        <span className="flex items-center gap-1">
                            <Play className="w-3 h-3" />
                            {media.plays || 0} plays
                        </span>
                        <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {formatDate(media.last_played)}
                        </span>
                    </div>
                    {media.is_favorite && (
                        <Heart className="w-3 h-3 text-red-500 fill-red-500" />
                    )}
                </div>
            </div>
        </motion.div>
    );
});

MediaCard.displayName = 'MediaCard';

// 🎵 Main Media Library Component
export function MediaLibrary({ searchQuery = '', filter = 'all' }: MediaLibraryProps) {
    const [library, setLibrary] = useState<MediaItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const searchTimeoutRef = useRef<NodeJS.Timeout>();
    const mountedRef = useRef(true);

    // Debounced fetch
    const fetchLibrary = useCallback(async () => {
        if (!mountedRef.current) return;
        
        try {
            setLoading(true);
            setError(null);

            const url = `/api/media/library?limit=100${filter === 'favorite' ? '&favorites_only=true' : ''}`;

            log('Fetching library:', { url, filter, searchQuery });

            const response = await fetch(url, {
                credentials: 'include'
            });

            if (!mountedRef.current) return;

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Please log in to view your media library');
                }
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            log('Library fetched:', data);

            // Client-side search filter
            let filteredLibrary = data.library || [];
            if (searchQuery.trim()) {
                const query = searchQuery.toLowerCase();
                filteredLibrary = filteredLibrary.filter((item: MediaItem) =>
                    item.title?.toLowerCase().includes(query) ||
                    item.artist?.toLowerCase().includes(query) ||
                    item.query?.toLowerCase().includes(query)
                );
                log('Filtered by search:', filteredLibrary.length, 'results');
            }

            if (mountedRef.current) {
                setLibrary(filteredLibrary);
            }
        } catch (err) {
            if (!mountedRef.current) return;
            const errorMsg = err instanceof Error ? err.message : 'Failed to load library';
            logError('Fetch error:', err);
            setError(errorMsg);
        } finally {
            if (mountedRef.current) {
                setLoading(false);
            }
        }
    }, [filter, searchQuery]);

    // Cleanup on unmount
    useEffect(() => {
        mountedRef.current = true;
        return () => {
            mountedRef.current = false;
        };
    }, []);

    // Debounced effect
    useEffect(() => {
        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        searchTimeoutRef.current = setTimeout(() => {
            fetchLibrary();
        }, searchQuery ? 300 : 0);

        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, [fetchLibrary, searchQuery]);

    const toggleFavorite = useCallback(async (video_id: string, currentStatus: boolean) => {
        try {
            // Optimistic UI update
            setLibrary(prevLibrary =>
                prevLibrary.map(item =>
                    item.video_id === video_id
                        ? { ...item, is_favorite: !item.is_favorite }
                        : item
                )
            );

            log('Toggling favorite:', video_id);

            const response = await fetch('/api/media/library/favorite', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ video_id })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Please log in to manage favorites');
                }
                throw new Error('Failed to toggle favorite');
            }

            const data = await response.json();
            log('Favorite toggled:', data);

            // Refresh if in favorites view and unfavoriting
            if (filter === 'favorite' && currentStatus) {
                setTimeout(() => fetchLibrary(), 300);
            }
        } catch (err) {
            logError('Toggle favorite error:', err);
            // Revert on error
            setLibrary(prevLibrary =>
                prevLibrary.map(item =>
                    item.video_id === video_id
                        ? { ...item, is_favorite: currentStatus }
                        : item
                )
            );
        }
    }, [filter, fetchLibrary]);

    // Delete media from library
    const deleteMedia = useCallback(async (video_id: string) => {
        const originalLibrary = library;
        
        // Optimistic UI update
        setLibrary(prevLibrary => prevLibrary.filter(item => item.video_id !== video_id));

        try {
            log('Deleting media:', video_id);

            const response = await fetch(`/api/media/library?video_id=${video_id}`, {
                method: 'DELETE',
                credentials: 'include',
            });

            if (!response.ok) {
                if (response.status === 401) {
                    throw new Error('Please log in to delete media');
                }
                throw new Error('Failed to delete media');
            }

            log('Media deleted:', video_id);
        } catch (err) {
            logError('Delete media error:', err);
            // Revert on error
            setLibrary(originalLibrary);
        }
    }, [library]);

    return (
        <div className="h-full flex flex-col min-h-0">
            {/* Library Grid */}
            <div className="flex-1 overflow-y-auto px-0.5 min-h-0">
                {/* Loading State */}
                <AnimatePresence mode="wait">
                    {loading && (
                        <motion.div
                            key="loading"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-12 gap-3"
                        >
                            <div className="relative">
                                <Disc3 className="w-10 h-10 text-primary animate-spin" />
                                <div className="absolute inset-0 w-10 h-10 rounded-full border-2 border-primary/20 animate-ping" />
                            </div>
                            <p className="text-sm text-muted-foreground">Loading your library...</p>
                        </motion.div>
                    )}

                    {/* Error State */}
                    {!loading && error && (
                        <motion.div
                            key="error"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-12 text-center px-4"
                        >
                            <div className="w-14 h-14 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
                                <AlertCircle className="w-7 h-7 text-destructive" />
                            </div>
                            <h3 className="text-sm font-semibold text-foreground mb-1.5">
                                Failed to load library
                            </h3>
                            <p className="text-xs text-muted-foreground mb-4 max-w-[200px]">
                                {error}
                            </p>
                            <button
                                onClick={() => fetchLibrary()}
                                className="flex items-center gap-1.5 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-xs font-medium"
                            >
                                <RefreshCw className="w-3.5 h-3.5" />
                                Try Again
                            </button>
                        </motion.div>
                    )}

                    {/* Empty State */}
                    {!loading && !error && library.length === 0 && (
                        <motion.div
                            key="empty"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center py-12 text-center px-4"
                        >
                            {filter === 'favorite' ? (
                                <>
                                    <div className="w-14 h-14 rounded-full bg-red-500/10 flex items-center justify-center mb-4">
                                        <Heart className="w-7 h-7 text-red-500/50" />
                                    </div>
                                    <h3 className="text-sm font-semibold text-foreground mb-1.5">
                                        No favorites yet
                                    </h3>
                                    <p className="text-xs text-muted-foreground max-w-[200px]">
                                        Tap the heart icon on any video to save it here
                                    </p>
                                </>
                            ) : (
                                <>
                                    <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                                        <Music className="w-7 h-7 text-primary/50" />
                                    </div>
                                    <h3 className="text-sm font-semibold text-foreground mb-1.5">
                                        Your library is empty
                                    </h3>
                                    <p className="text-xs text-muted-foreground max-w-[200px]">
                                        Ask me to play a song and I'll save it here! 🎵
                                    </p>
                                </>
                            )}
                        </motion.div>
                    )}

                    {/* Library Grid */}
                    {!loading && !error && library.length > 0 && (
                        <motion.div
                            key="library"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="space-y-3 pb-4"
                        >
                            {library.map((media, index) => (
                                <MediaCard
                                    key={media.video_id}
                                    media={media}
                                    onToggleFavorite={toggleFavorite}
                                    onDelete={deleteMedia}
                                    index={index}
                                />
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
