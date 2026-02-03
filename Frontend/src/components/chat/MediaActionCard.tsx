import { useState, useEffect, useMemo, useCallback } from 'react';
import { ExternalLink, Play, X } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useChatStore } from '@/stores/chatStore';
import { MediaPlayPayload } from '@/types/chat';

interface MediaActionCardProps {
    payload: Partial<MediaPlayPayload> | null | undefined;
    chatId?: string | null;
    messageId?: string;
}

export function MediaActionCard({ payload, chatId, messageId }: MediaActionCardProps) {
    const markActionExecuted = useChatStore(state => state.markActionExecuted);
    const [isPlaying, setIsPlaying] = useState(false);
    const [isHovered, setIsHovered] = useState(false);
    const [imageLoaded, setImageLoaded] = useState(false);
    const [thumbnailSrc, setThumbnailSrc] = useState<string>('');

    const safePayload = useMemo(() => {
        if (!payload || typeof payload !== 'object') return null;
        const basePayload = {
            mode: payload.mode || 'video',
            url: payload.url || '',
            video_id: payload.video_id || '',
            query: payload.query || 'Video',
        };
        if (!basePayload.video_id && basePayload.url) {
            const match = basePayload.url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
            if (match) basePayload.video_id = match[1];
        }
        return basePayload;
    }, [payload]);

    const video_id = safePayload?.video_id || '';
    const query = safePayload?.query || 'Video';

    useEffect(() => {
        if (video_id) {
            setImageLoaded(false);
            setThumbnailSrc(`https://img.youtube.com/vi/${video_id}/maxresdefault.jpg`);
        }
    }, [video_id]);

    useEffect(() => {
        if (chatId && messageId) {
            markActionExecuted(chatId, messageId);
        }
    }, [chatId, messageId, markActionExecuted]);

    const handlePlay = useCallback(() => {
        if (!video_id) return;
        setIsPlaying(true);
    }, [video_id]);

    const handleStop = useCallback(() => {
        setIsPlaying(false);
    }, []);

    const handleOpenYouTube = useCallback(() => {
        window.open(`https://www.youtube.com/watch?v=${video_id}`, "_blank");
    }, [video_id]);

    const handleImageError = useCallback(() => {
        if (thumbnailSrc.includes('maxresdefault')) {
            setThumbnailSrc(`https://img.youtube.com/vi/${video_id}/hqdefault.jpg`);
        }
    }, [thumbnailSrc, video_id]);

    if (!safePayload || !video_id) return null;

    const embedUrl = `https://www.youtube.com/embed/${video_id}?autoplay=1&rel=0&modestbranding=1&playsinline=1`;

    return (
        <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: [0.23, 1, 0.32, 1] }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            className="w-full my-4"
        >
            <motion.div
                animate={{ 
                    scale: isHovered && !isPlaying ? 1.015 : 1,
                    y: isHovered && !isPlaying ? -3 : 0 
                }}
                transition={{ duration: 0.35, ease: [0.23, 1, 0.32, 1] }}
                className="relative w-full rounded-xl overflow-hidden"
                style={{
                    aspectRatio: '16 / 9',
                    boxShadow: isHovered 
                        ? '0 24px 48px -12px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(255,255,255,0.08)' 
                        : '0 8px 32px -8px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255,255,255,0.05)'
                }}
            >
                <AnimatePresence mode="wait">
                    {!isPlaying ? (
                        <motion.div
                            key="thumbnail"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="absolute inset-0 cursor-pointer"
                            onClick={handlePlay}
                        >
                            {/* Thumbnail - fills entire card */}
                            <div className="absolute inset-0 overflow-hidden bg-neutral-900">
                                <motion.img
                                    src={thumbnailSrc}
                                    alt={query}
                                    className="absolute inset-0 w-full h-full"
                                    style={{
                                        objectFit: 'cover',
                                        objectPosition: 'center center',
                                    }}
                                    animate={{ scale: isHovered ? 1.06 : 1 }}
                                    transition={{ duration: 0.5, ease: [0.23, 1, 0.32, 1] }}
                                    onLoad={() => setImageLoaded(true)}
                                    onError={handleImageError}
                                />
                                
                                {/* Loading placeholder */}
                                <AnimatePresence>
                                    {!imageLoaded && (
                                        <motion.div 
                                            className="absolute inset-0 bg-neutral-800 animate-pulse"
                                            exit={{ opacity: 0 }}
                                            transition={{ duration: 0.3 }}
                                        />
                                    )}
                                </AnimatePresence>
                            </div>
                            
                            {/* Gradient overlay */}
                            <div 
                                className="absolute inset-0 pointer-events-none"
                                style={{
                                    background: 'linear-gradient(180deg, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.5) 75%, rgba(0,0,0,0.9) 100%)'
                                }}
                            />
                            
                            {/* Play Button - Center */}
                            <div className="absolute inset-0 flex items-center justify-center">
                                <motion.div
                                    animate={{ 
                                        scale: isHovered ? 1.12 : 1,
                                        opacity: isHovered ? 1 : 0.9
                                    }}
                                    whileTap={{ scale: 0.92 }}
                                    transition={{ duration: 0.25, ease: "easeOut" }}
                                    className="w-16 h-16 sm:w-[72px] sm:h-[72px] rounded-full flex items-center justify-center"
                                    style={{
                                        background: 'rgba(255, 0, 0, 0.95)',
                                        boxShadow: isHovered 
                                            ? '0 12px 40px rgba(255, 0, 0, 0.5), 0 0 0 4px rgba(255,255,255,0.15)'
                                            : '0 8px 28px rgba(255, 0, 0, 0.4)'
                                    }}
                                >
                                    <Play className="w-7 h-7 sm:w-8 sm:h-8 text-white fill-white ml-1" />
                                </motion.div>
                            </div>

                            {/* Title - Bottom Left */}
                            <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-5">
                                <motion.h3 
                                    className="text-white font-semibold text-base sm:text-lg line-clamp-2 capitalize"
                                    style={{ textShadow: '0 2px 12px rgba(0,0,0,0.8)' }}
                                    animate={{ y: isHovered ? -2 : 0 }}
                                    transition={{ duration: 0.25 }}
                                >
                                    {query}
                                </motion.h3>
                                <motion.p 
                                    className="text-white/60 text-xs mt-2 flex items-center gap-1.5"
                                    animate={{ opacity: isHovered ? 0.9 : 0.6 }}
                                >
                                    <Play className="w-3 h-3 fill-current" />
                                    Click to play
                                </motion.p>
                            </div>
                        </motion.div>
                    ) : (
                        /* Playing State - YouTube iframe */
                        <motion.div
                            key="player"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            transition={{ duration: 0.25 }}
                            className="absolute inset-0 bg-black"
                        >
                            <iframe
                                src={embedUrl}
                                title={query}
                                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                                allowFullScreen
                                className="absolute inset-0 w-full h-full border-0"
                            />
                            
                            {/* Top bar with title and controls */}
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute top-0 left-0 right-0 p-3 flex items-center justify-between z-10"
                                style={{
                                    background: 'linear-gradient(180deg, rgba(0,0,0,0.8) 0%, rgba(0,0,0,0) 100%)'
                                }}
                            >
                                {/* Title on left */}
                                <div className="flex items-center gap-2 flex-1 min-w-0 mr-3">
                                    <svg className="w-4 h-4 text-red-500 flex-shrink-0" viewBox="0 0 24 24" fill="currentColor">
                                        <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z"/>
                                        <path fill="#fff" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
                                    </svg>
                                    <span className="text-white text-sm font-medium truncate">
                                        {query}
                                    </span>
                                </div>
                                
                                {/* Controls on right */}
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    {/* Watch on YouTube */}
                                    <motion.button
                                        onClick={handleOpenYouTube}
                                        whileHover={{ scale: 1.05 }}
                                        whileTap={{ scale: 0.95 }}
                                        className="px-2.5 py-1.5 rounded-md text-white/90 hover:text-white text-xs font-medium flex items-center gap-1.5"
                                        style={{ 
                                            background: 'rgba(255,255,255,0.15)',
                                            backdropFilter: 'blur(4px)'
                                        }}
                                    >
                                        <ExternalLink className="w-3 h-3" />
                                        <span className="hidden sm:inline">YouTube</span>
                                    </motion.button>
                                    
                                    {/* Close button */}
                                    <motion.button
                                        onClick={handleStop}
                                        whileHover={{ scale: 1.1, background: 'rgba(255,255,255,0.25)' }}
                                        whileTap={{ scale: 0.95 }}
                                        className="p-1.5 rounded-md text-white"
                                        style={{ 
                                            background: 'rgba(255,255,255,0.15)',
                                        }}
                                    >
                                        <X className="w-4 h-4" />
                                    </motion.button>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </motion.div>
    );
}
