import { cn } from "@/lib/utils";

interface SeparatorProps {
  className?: string;
}

/**
 * Premium horizontal separator component
 * Used to divide content sections with subtle, GPT-like styling
 */
export const Separator = ({ className }: SeparatorProps) => {
  return (
    <div 
      className={cn(
        "border-t border-gray-300/40 dark:border-gray-700/40 my-4 w-full",
        className
      )} 
    />
  );
};

/**
 * Thin separator for smaller spacing
 */
export const ThinSeparator = ({ className }: SeparatorProps) => {
  return (
    <div 
      className={cn(
        "border-t border-gray-200/30 dark:border-gray-800/30 my-2 w-full",
        className
      )} 
    />
  );
};
