import React, { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { Bot, ClipboardCopy, Volume2, Trash2, Check, Palette } from "lucide-react";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

interface HighlightMenuProps {
  position: { x: number; y: number; bottom: number; width: number };
  selectedText: string;
  isHighlighted?: boolean;
  menuRef: React.RefObject<HTMLDivElement>;
  onClose: () => void;
  onHighlight: (color: string) => void;
  onDeleteHighlight?: () => void;
  onCreateMiniAgent: () => void;
  onSpeak: () => void;
  onCopy: () => void;
  hasMiniAgent?: boolean;
  messageId?: string;
}

// Inline Color Picker Component
const AdvancedColorPickerContent = ({ onColorSelect }: { onColorSelect: (color: string) => void }) => {
  const [hue, setHue] = useState(50);
  const [saturation, setSaturation] = useState(100);
  const [brightness, setBrightness] = useState(87);
  const [opacity, setOpacity] = useState(100);
  const [hexInput, setHexInput] = useState("#FFD93D");
  const colorAreaRef = useRef<HTMLDivElement>(null);
  const [isDraggingSB, setIsDraggingSB] = useState(false);

  // Convert HSB to Hex
  const hsbToHex = (h: number, s: number, b: number): string => {
    const c = (b / 100) * (s / 100);
    const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
    const m = b / 100 - c;

    let r = 0, g = 0, bl = 0;
    if (h >= 0 && h < 60) { r = c; g = x; bl = 0; }
    else if (h >= 60 && h < 120) { r = x; g = c; bl = 0; }
    else if (h >= 120 && h < 180) { r = 0; g = c; bl = x; }
    else if (h >= 180 && h < 240) { r = 0; g = x; bl = c; }
    else if (h >= 240 && h < 300) { r = x; g = 0; bl = c; }
    else { r = c; g = 0; bl = x; }

    const toHex = (n: number) => {
      const hex = Math.round((n + m) * 255).toString(16);
      return hex.length === 1 ? '0' + hex : hex;
    };

    return `#${toHex(r)}${toHex(g)}${toHex(bl)}`.toUpperCase();
  };

  // Update hex when HSB changes
  useEffect(() => {
    const hex = hsbToHex(hue, saturation, brightness);
    setHexInput(hex);
  }, [hue, saturation, brightness]);

  // Handle color area drag
  const handleColorAreaMouseDown = (e: React.MouseEvent) => {
    setIsDraggingSB(true);
    updateSaturationBrightness(e);
  };

  const updateSaturationBrightness = (e: React.MouseEvent | MouseEvent) => {
    if (!colorAreaRef.current) return;
    const rect = colorAreaRef.current.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const y = Math.max(0, Math.min(e.clientY - rect.top, rect.height));
    
    const newSaturation = (x / rect.width) * 100;
    const newBrightness = 100 - (y / rect.height) * 100;
    
    setSaturation(newSaturation);
    setBrightness(newBrightness);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (isDraggingSB) updateSaturationBrightness(e);
    };

    const handleMouseUp = () => {
      setIsDraggingSB(false);
    };

    if (isDraggingSB) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDraggingSB]);

  const currentColor = hsbToHex(hue, saturation, brightness);
  const hueGradient = `hsl(${hue}, 100%, 50%)`;

  const handleApply = () => {
    // Get the final color with proper opacity
    const finalColor = hsbToHex(hue, saturation, brightness);
    const alpha = Math.round((opacity / 100) * 255).toString(16).padStart(2, '0');
    const colorWithOpacity = opacity < 100 ? finalColor + alpha : finalColor;
    onColorSelect(colorWithOpacity);
  };

  return (
    <div className="w-full max-w-[170px]">
      {/* Color Area (Saturation + Brightness) */}
      <div
        ref={colorAreaRef}
        className="relative w-full h-12 rounded-md mb-1 cursor-crosshair overflow-hidden"
        style={{
          background: `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, ${hueGradient})`,
        }}
        onMouseDown={handleColorAreaMouseDown}
      >
        {/* Cursor */}
        <div
          className="absolute w-2 h-2 border-2 border-white rounded-full shadow-lg pointer-events-none"
          style={{
            left: `${saturation}%`,
            top: `${100 - brightness}%`,
            transform: 'translate(-50%, -50%)',
          }}
        />
      </div>

      {/* Hue Slider */}
      <div className="mb-0.5">
        <div className="text-[9px] text-white/50 mb-0.5 uppercase tracking-wide">Hue</div>
        <div className="relative h-1 rounded-full overflow-hidden">
          <div
            className="absolute inset-0"
            style={{
              background: 'linear-gradient(to right, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000)',
            }}
          />
          <input
            type="range"
            min="0"
            max="360"
            value={hue}
            onChange={(e) => setHue(Number(e.target.value))}
            className="absolute inset-0 w-full appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-2 [&::-webkit-slider-thumb]:h-2 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border [&::-webkit-slider-thumb]:border-gray-800 [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer"
          />
        </div>
      </div>

      {/* Opacity Slider */}
      <div className="mb-0.5">
        <div className="text-[9px] text-white/50 mb-0.5 uppercase tracking-wide">Opacity</div>
        <div className="relative h-1 rounded-full overflow-hidden">
          <div
            className="absolute inset-0"
            style={{
              background: `linear-gradient(to right, transparent, ${currentColor})`,
              backgroundImage: `linear-gradient(to right, transparent, ${currentColor}), repeating-conic-gradient(#80808020 0% 25%, transparent 0% 50%) 50% / 10px 10px`,
            }}
          />
          <input
            type="range"
            min="0"
            max="100"
            value={opacity}
            onChange={(e) => setOpacity(Number(e.target.value))}
            className="absolute inset-0 w-full appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-2 [&::-webkit-slider-thumb]:h-2 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border [&::-webkit-slider-thumb]:border-gray-800 [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:cursor-pointer"
          />
        </div>
      </div>

      {/* HEX Input & Apply */}
      <div className="flex items-center gap-0.5">
        <input
          type="text"
          value={hexInput}
          onChange={(e) => setHexInput(e.target.value)}
          className="flex-1 bg-black/30 border border-white/20 rounded px-1 py-0.5 text-[10px] text-white font-mono focus:outline-none focus:border-primary"
          placeholder="#FFFFFF"
          maxLength={7}
        />
        <button
          onClick={handleApply}
          className="bg-primary hover:bg-primary/90 text-black rounded px-1.5 py-0.5 text-[10px] font-medium transition-colors flex items-center gap-0.5"
        >
          <Check className="w-2 h-2" />
          Apply
        </button>
      </div>
    </div>
  );
};

export const HighlightMenu = ({
  position,
  selectedText,
  isHighlighted,
  menuRef,
  onClose,
  onHighlight,
  onDeleteHighlight,
  onCreateMiniAgent,
  onSpeak,
  onCopy,
  hasMiniAgent,
  messageId,
}: HighlightMenuProps) => {
  const [copied, setCopied] = useState(false);
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [calculatedPos, setCalculatedPos] = useState<{ x: number; y: number; showAbove: boolean } | null>(null);
  
  // CLEAN POSITIONING - Always above with minimal gap
  useEffect(() => {
    if (!menuRef.current) return;
    
    const popup = menuRef.current;
    const popupWidth = popup.offsetWidth;
    const gap = 8; // 8px gap above selected text
    
    const viewportWidth = window.innerWidth;
    
    // Always position above: popup bottom at (selection.top - gap)
    const finalY = position.y - gap;
    
    // Center horizontally on selection
    let finalX = position.x;
    
    // Prevent overflow (left/right)
    const minX = popupWidth / 2 + 8;
    const maxX = viewportWidth - popupWidth / 2 - 8;
    if (finalX < minX) finalX = minX;
    if (finalX > maxX) finalX = maxX;
    
    setCalculatedPos({ x: finalX, y: finalY, showAbove: true });
  }, [position, showColorPicker, menuRef.current]);
  
  // Top 5 most used colors
  const topColors = [
    { name: "yellow", hex: "#FFD93D" },
    { name: "green", hex: "#3ED174" },
    { name: "blue", hex: "#4B9CFF" },
    { name: "red", hex: "#FF4B4B" },
    { name: "purple", hex: "#C36BFF" },
  ];
  
  const handleCopy = () => {
    onCopy();
    setCopied(true);
    setTimeout(() => setCopied(false), 1000);
  };

  const handleColorSelect = (colorHex: string) => {
    onHighlight(colorHex);
    onClose();
  };

  // Use calculated position or fallback (always above)
  const pos = calculatedPos || { x: position.x, y: position.y - 8, showAbove: true };

  return (
    <motion.div
      ref={menuRef}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.15 }}
      className="fixed z-[9998] bg-[rgba(40,40,40,0.95)] backdrop-blur-xl rounded-xl shadow-2xl border border-white/10 overflow-hidden"
      style={{
        left: pos.x,
        top: pos.y,
        transform: "translate(-50%, -100%)", // Always above: bottom of popup at pos.y
      }}
    >
      {/* Main Menu Content */}
      <div className="p-2.5">
        {/* Top Toolbar - Copy, Sub-Brain, Speak, Delete */}
        <div className="flex items-center gap-1 pb-2 mb-2 border-b border-white/10">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button onClick={handleCopy} className="p-1.5 rounded-lg hover:bg-white/10 transition-all">
                  {copied ? <Check className="w-4 h-4 text-green-400" /> : <ClipboardCopy className="w-4 h-4 text-white/80" />}
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">Copy</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button 
                  onClick={onCreateMiniAgent} 
                  className={`p-1.5 rounded-lg transition-all ${
                    hasMiniAgent 
                      ? 'bg-primary/20 hover:bg-primary/30 cursor-pointer' 
                      : 'hover:bg-white/10'
                  }`}
                  title={hasMiniAgent ? 'Update snippet (Sub-Brain exists)' : 'Open Sub-Brain'}
                >
                  <Bot className={`w-4 h-4 ${hasMiniAgent ? 'text-primary animate-pulse' : 'text-primary'}`} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">
                {hasMiniAgent ? 'Update snippet' : '🧠 Sub-Brain'}
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <button onClick={onSpeak} className="p-1.5 rounded-lg hover:bg-white/10 transition-all">
                  <Volume2 className="w-4 h-4 text-white/80" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">Speak</TooltipContent>
            </Tooltip>
          </TooltipProvider>
          {isHighlighted && onDeleteHighlight && (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button onClick={onDeleteHighlight} className="p-1.5 rounded-lg hover:bg-white/10 transition-all">
                    <Trash2 className="w-4 h-4 text-red-400" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs">Delete</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>

        {/* 5 Most Used Colors + Color Picker Icon */}
        <div className="flex items-center gap-1.5">
          {topColors.map((color, idx) => (
            <TooltipProvider key={idx}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <motion.button
                    onClick={() => handleColorSelect(color.hex)}
                    className="w-[18px] h-[18px] rounded-full border border-white/30 shadow-md transition-transform hover:scale-110 active:scale-95"
                    style={{ backgroundColor: color.hex }}
                    whileHover={{ scale: 1.15 }}
                    whileTap={{ scale: 0.9 }}
                  />
                </TooltipTrigger>
                <TooltipContent side="bottom" className="text-xs capitalize">{color.name}</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ))}
          
          {/* Color Picker Icon */}
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <motion.button
                  onClick={() => setShowColorPicker(!showColorPicker)}
                  className="w-[20px] h-[20px] rounded-full border border-white/30 shadow-md flex items-center justify-center transition-all hover:shadow-lg hover:border-white/50"
                  style={{
                    background: 'conic-gradient(from 0deg, #ff0000, #ffff00, #00ff00, #00ffff, #0000ff, #ff00ff, #ff0000)',
                  }}
                  whileHover={{ scale: 1.15 }}
                  whileTap={{ scale: 0.9 }}
                >
                  <Palette className="w-3 h-3 text-white drop-shadow-lg" />
                </motion.button>
              </TooltipTrigger>
              <TooltipContent side="bottom" className="text-xs">Custom Color</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </div>

      {/* Advanced Color Picker - Attached Below */}
      {showColorPicker && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          transition={{ duration: 0.2 }}
          className="border-t border-white/10 p-1 bg-[rgba(30,30,30,0.98)]"
        >
          <AdvancedColorPickerContent
            onColorSelect={(color) => {
              handleColorSelect(color);
              setShowColorPicker(false);
            }}
          />
        </motion.div>
      )}
    </motion.div>
  );
};
