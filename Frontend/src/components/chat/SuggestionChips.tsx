
import { motion } from 'framer-motion';
import { useChatStore } from '@/stores/chatStore';
import { cn } from '@/lib/utils';
import { Sparkles } from 'lucide-react';

interface SuggestionChipsProps {
    suggestions: string[];
    chatId?: string;
}

export function SuggestionChips({ suggestions, chatId }: SuggestionChipsProps) {
    if (!suggestions || suggestions.length === 0) return null;

    const handleSuggestionClick = (suggestion: string) => {
        if (!chatId) return;
        useChatStore.getState().addMessage(chatId, {
            role: "user",
            content: suggestion
        });
    };

    return (
        <div className="flex flex-wrap gap-2 mt-4">
            {suggestions.map((suggestion, index) => (
                <motion.button
                    key={index}
                    initial={{ opacity: 0, scale: 0.9, y: 5 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: index * 0.05 }}
                    onClick={() => handleSuggestionClick(suggestion)}
                    className={cn(
                        "group flex items-center gap-2 px-3 py-1.5 rounded-full",
                        "bg-primary/5 hover:bg-primary/10 border border-primary/10 hover:border-primary/20",
                        "text-xs font-medium text-primary/80 hover:text-primary",
                        "transition-all duration-200 cursor-pointer"
                    )}
                >
                    <Sparkles className="w-3 h-3 opacity-50 group-hover:opacity-100 transition-opacity" />
                    {suggestion}
                </motion.button>
            ))}
        </div>
    );
}
