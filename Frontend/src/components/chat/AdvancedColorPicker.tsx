import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check } from "lucide-react";

interface AdvancedColorPickerProps {
  initialColor?: string;
  onColorSelect: (color: string) => void;
  onClose: () => void;
  position: { x: number; y: number };
}

export const AdvancedColorPicker = ({
  initialColor = "#FFD93D",
  onColorSelect,
  onClose,
  position,
}: AdvancedColorPickerProps) => {
  const [hue, setHue] = useState(50);
  const [saturation, setSaturation] = useState(100);
  const [brightness, setBrightness] = useState(87);
  const [opacity, setOpacity] = useState(100);
  const [hexInput, setHexInput] = useState("#FFD93D");
  const pickerRef = useRef<HTMLDivElement>(null);
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

  // Convert Hex to HSB
  const hexToHSB = (hex: string): { h: number; s: number; b: number } => {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!result) return { h: 0, s: 0, b: 0 };

    const r = parseInt(result[1], 16) / 255;
    const g = parseInt(result[2], 16) / 255;
    const b = parseInt(result[3], 16) / 255;

    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const delta = max - min;

    let h = 0;
    if (delta !== 0) {
      if (max === r) h = ((g - b) / delta) % 6;
      else if (max === g) h = (b - r) / delta + 2;
      else h = (r - g) / delta + 4;
    }
    h = Math.round(h * 60);
    if (h < 0) h += 360;

    const s = max === 0 ? 0 : (delta / max) * 100;
    const br = max * 100;

    return { h, s, b: br };
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

  // Handle hex input
  const handleHexInputChange = (value: string) => {
    setHexInput(value);
    if (/^#[0-9A-Fa-f]{6}$/.test(value)) {
      const hsb = hexToHSB(value);
      setHue(hsb.h);
      setSaturation(hsb.s);
      setBrightness(hsb.b);
    }
  };

  // Apply color
  const handleApply = () => {
    const finalColor = hsbToHex(hue, saturation, brightness);
    const alpha = Math.round((opacity / 100) * 255).toString(16).padStart(2, '0');
    onColorSelect(finalColor + (opacity < 100 ? alpha : ''));
    onClose();
  };

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        onClose();
      }
    };

    setTimeout(() => {
      document.addEventListener('mousedown', handleClickOutside);
    }, 100);

    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [onClose]);

  const currentColor = hsbToHex(hue, saturation, brightness);
  const hueGradient = `hsl(${hue}, 100%, 50%)`;

  return (
    <AnimatePresence>
      <motion.div
        ref={pickerRef}
        initial={{ opacity: 0, scale: 0.9, y: -10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.15 }}
        className="absolute z-[9999] bg-[rgba(40,40,40,0.98)] backdrop-blur-xl rounded-xl shadow-2xl border border-white/10 p-4 w-[280px]"
        style={{
          left: position.x,
          top: position.y + 45,
        }}
      >
        {/* Color Area (Saturation + Brightness) */}
        <div
          ref={colorAreaRef}
          className="relative w-full h-40 rounded-lg mb-3 cursor-crosshair overflow-hidden"
          style={{
            background: `linear-gradient(to top, #000, transparent), linear-gradient(to right, #fff, ${hueGradient})`,
          }}
          onMouseDown={handleColorAreaMouseDown}
        >
          {/* Cursor */}
          <div
            className="absolute w-4 h-4 border-2 border-white rounded-full shadow-lg pointer-events-none"
            style={{
              left: `${saturation}%`,
              top: `${100 - brightness}%`,
              transform: 'translate(-50%, -50%)',
            }}
          />
        </div>

        {/* Hue Slider */}
        <div className="mb-3">
          <div className="text-[10px] text-white/60 mb-1 uppercase tracking-wide">Hue</div>
          <div className="relative h-3 rounded-full overflow-hidden">
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
              className="absolute inset-0 w-full appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-gray-800 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-pointer"
            />
          </div>
        </div>

        {/* Opacity Slider */}
        <div className="mb-3">
          <div className="text-[10px] text-white/60 mb-1 uppercase tracking-wide">Opacity</div>
          <div className="relative h-3 rounded-full overflow-hidden">
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
              className="absolute inset-0 w-full appearance-none bg-transparent cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-gray-800 [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-pointer"
            />
          </div>
        </div>

        {/* HEX Input */}
        <div className="mb-3">
          <div className="text-[10px] text-white/60 mb-1 uppercase tracking-wide">Hex Color</div>
          <input
            type="text"
            value={hexInput}
            onChange={(e) => handleHexInputChange(e.target.value)}
            className="w-full bg-black/30 border border-white/20 rounded-lg px-3 py-2 text-sm text-white font-mono focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary"
            placeholder="#FFFFFF"
            maxLength={7}
          />
        </div>

        {/* Preview & Apply */}
        <div className="flex items-center gap-2">
          <div
            className="w-12 h-12 rounded-lg border-2 border-white/20 shadow-inner"
            style={{ backgroundColor: currentColor }}
          />
          <button
            onClick={handleApply}
            className="flex-1 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg px-4 py-2.5 text-sm font-medium transition-colors flex items-center justify-center gap-2"
          >
            <Check className="w-4 h-4" />
            Apply Color
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
