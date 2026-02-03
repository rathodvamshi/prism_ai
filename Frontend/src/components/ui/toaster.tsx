import { useToast } from "@/hooks/use-toast";
import { Toast, ToastClose, ToastDescription, ToastProvider, ToastTitle, ToastViewport, ToastIcon } from "@/components/ui/toast";

export function Toaster() {
  const { toasts } = useToast();

  // Helper to detect variant from title emoji
  const getVariant = (title?: string, variant?: string) => {
    if (variant) return variant as any;
    if (!title) return "default";
    if (title.includes("✅") || title.includes("success")) return "success";
    if (title.includes("❌") || title.includes("error") || title.includes("fail")) return "destructive";
    if (title.includes("⚠️") || title.includes("warning")) return "warning";
    if (title.includes("ℹ️") || title.includes("info")) return "info";
    return "default";
  };

  // Clean title by removing emoji prefix
  const cleanTitle = (title?: string) => {
    if (!title) return title;
    return title.replace(/^[\u{1F300}-\u{1F9FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}✅❌⚠️ℹ️👋🗑️]+\s*/u, "");
  };

  return (
    <ToastProvider>
      {toasts.map(function ({ id, title, description, action, variant, ...props }) {
        const detectedVariant = getVariant(title as string, variant as string);
        const displayTitle = cleanTitle(title as string);
        
        return (
          <Toast key={id} variant={detectedVariant} {...props}>
            <ToastIcon variant={detectedVariant} />
            <div className="flex-1 grid gap-0.5">
              {displayTitle && <ToastTitle>{displayTitle}</ToastTitle>}
              {description && <ToastDescription>{description}</ToastDescription>}
            </div>
            {action}
            <ToastClose />
          </Toast>
        );
      })}
      <ToastViewport />
    </ToastProvider>
  );
}
