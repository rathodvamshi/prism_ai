/**
 * 🪝 CODE BEAUTIFIER HOOK
 * 
 * React hook for managing code beautification settings and stats
 */

import { useState, useEffect, useCallback } from 'react';
import { beautifyCode, BeautifyOptions, BeautifyResult } from '../lib/codeBeautifier';

export interface BeautifierSettings {
  enabled: boolean;
  autoDetectLanguage: boolean;
  showBeautificationIndicator: boolean;
  indentSize: number;
  maxLineLength: number;
}

export interface BeautifierStats {
  totalCodeBlocks: number;
  beautifiedBlocks: number;
  successRate: number;
  languages: Record<string, number>;
  timesSaved: number;
}

const DEFAULT_SETTINGS: BeautifierSettings = {
  enabled: true,
  autoDetectLanguage: true,
  showBeautificationIndicator: true,
  indentSize: 2,
  maxLineLength: 80,
};

const STORAGE_KEY = 'prism-beautifier-settings';
const STATS_KEY = 'prism-beautifier-stats';

/**
 * 🎯 Main beautifier hook
 */
export const useCodeBeautifier = () => {
  // Load settings from localStorage
  const [settings, setSettings] = useState<BeautifierSettings>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      return saved ? { ...DEFAULT_SETTINGS, ...JSON.parse(saved) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  // Load stats from localStorage
  const [stats, setStats] = useState<BeautifierStats>(() => {
    try {
      const saved = localStorage.getItem(STATS_KEY);
      return saved ? JSON.parse(saved) : {
        totalCodeBlocks: 0,
        beautifiedBlocks: 0,
        successRate: 0,
        languages: {},
        timesSaved: 0,
      };
    } catch {
      return {
        totalCodeBlocks: 0,
        beautifiedBlocks: 0,
        successRate: 0,
        languages: {},
        timesSaved: 0,
      };
    }
  });

  // Save settings to localStorage when changed
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    } catch (error) {
      console.warn('Failed to save beautifier settings:', error);
    }
  }, [settings]);

  // Save stats to localStorage when changed
  useEffect(() => {
    try {
      localStorage.setItem(STATS_KEY, JSON.stringify(stats));
    } catch (error) {
      console.warn('Failed to save beautifier stats:', error);
    }
  }, [stats]);

  /**
   * 🎨 Beautify code with stats tracking
   */
  const beautify = useCallback((
    code: string,
    language?: string,
    options?: BeautifyOptions
  ): BeautifyResult => {
    if (!settings.enabled) {
      return {
        code,
        language: language || 'text',
        success: false,
        errors: ['Beautifier is disabled']
      };
    }

    const beautifyOptions: BeautifyOptions = {
      indentSize: settings.indentSize,
      maxLineLength: settings.maxLineLength,
      ...options,
    };

    const result = beautifyCode(code, language, beautifyOptions);

    // Update stats
    setStats(prev => {
      const newStats = { ...prev };
      newStats.totalCodeBlocks++;
      
      if (result.success) {
        newStats.beautifiedBlocks++;
        newStats.languages[result.language] = (newStats.languages[result.language] || 0) + 1;
      }
      
      newStats.successRate = (newStats.beautifiedBlocks / newStats.totalCodeBlocks) * 100;
      
      return newStats;
    });

    return result;
  }, [settings]);

  /**
   * ⚙️ Update settings
   */
  const updateSettings = useCallback((newSettings: Partial<BeautifierSettings>) => {
    setSettings(prev => ({ ...prev, ...newSettings }));
  }, []);

  /**
   * 📊 Reset stats
   */
  const resetStats = useCallback(() => {
    setStats({
      totalCodeBlocks: 0,
      beautifiedBlocks: 0,
      successRate: 0,
      languages: {},
      timesSaved: 0,
    });
  }, []);

  /**
   * 💾 Track save action
   */
  const trackSave = useCallback(() => {
    setStats(prev => ({
      ...prev,
      timesSaved: prev.timesSaved + 1,
    }));
  }, []);

  /**
   * 🏆 Get achievement badges based on stats
   */
  const getAchievements = useCallback(() => {
    const achievements: string[] = [];
    
    if (stats.totalCodeBlocks >= 10) achievements.push('📝 Code Formatter');
    if (stats.totalCodeBlocks >= 50) achievements.push('🎨 Beautification Master');
    if (stats.totalCodeBlocks >= 100) achievements.push('🚀 Code Wizard');
    
    if (stats.successRate >= 90) achievements.push('🎯 High Precision');
    if (stats.successRate === 100 && stats.totalCodeBlocks >= 10) achievements.push('💎 Perfect Score');
    
    if (Object.keys(stats.languages).length >= 3) achievements.push('🌐 Polyglot');
    if (Object.keys(stats.languages).length >= 5) achievements.push('🔥 Multi-Language Expert');
    
    if (stats.timesSaved >= 10) achievements.push('💾 Frequent Saver');
    
    return achievements;
  }, [stats]);

  return {
    // Main beautification function
    beautify,
    
    // Settings management
    settings,
    updateSettings,
    
    // Stats and analytics
    stats,
    resetStats,
    trackSave,
    getAchievements: getAchievements(),
    
    // Convenience methods
    isEnabled: settings.enabled,
    toggle: () => updateSettings({ enabled: !settings.enabled }),
    
    // Quick settings toggles
    toggleAutoDetect: () => updateSettings({ autoDetectLanguage: !settings.autoDetectLanguage }),
    toggleIndicator: () => updateSettings({ showBeautificationIndicator: !settings.showBeautificationIndicator }),
  };
};

/**
 * 🎪 Demo hook for testing beautifier
 */
export const useBeautifierDemo = () => {
  const [demoCode, setDemoCode] = useState('');
  const [demoLanguage, setDemoLanguage] = useState('javascript');
  const [result, setResult] = useState<BeautifyResult | null>(null);
  
  const { beautify } = useCodeBeautifier();
  
  const runDemo = useCallback((code: string, language?: string) => {
    const result = beautify(code, language);
    setResult(result);
    return result;
  }, [beautify]);
  
  return {
    demoCode,
    setDemoCode,
    demoLanguage,
    setDemoLanguage,
    result,
    runDemo,
  };
};

export default useCodeBeautifier;