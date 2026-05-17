import React, { useState, useEffect, useMemo } from "react";
import { Settings, ChevronDown, ChevronUp, Copy, Check, Info } from "lucide-react";
import clsx from "clsx";

/**
 * NamingConfig Component
 * 
 * A collapsible panel for configuring mockup output filename templates.
 * Supports placeholders, live preview, and various formatting options.
 */

const PLACEHOLDER_INFO = {
  poster_name: "Design/artwork filename (without extension)",
  mockup_name: "Mockup template name (without extension)",
  width: "Poster width in pixels",
  height: "Poster height in pixels",
  orientation: "Detected orientation (portrait/landscape/square)",
  size: "Combined dimensions (e.g., 1920x1080)",
  date: "Generation date (YYYY-MM-DD)",
  time: "Generation time (HH-MM-SS)",
  timestamp: "Unix timestamp",
  index: "Batch index (padded)",
  batch_id: "Unique batch identifier",
};

const CASE_STYLES = [
  { value: "snake", label: "snake_case" },
  { value: "kebab", label: "kebab-case" },
  { value: "camel", label: "camelCase" },
  { value: "pascal", label: "PascalCase" },
  { value: "original", label: "Original" },
];

const COLLISION_STRATEGIES = [
  { value: "suffix", label: "Add suffix (file_001)" },
  { value: "prefix", label: "Add prefix (001_file)" },
  { value: "timestamp", label: "Add timestamp" },
];

export default function NamingConfig({ 
  onTemplateChange, 
  initialTemplate = "{poster_name}_{mockup_name}",
  mockupName = "frame_mockup",
  posterName = "my_poster"
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [template, setTemplate] = useState(initialTemplate);
  const [caseStyle, setCaseStyle] = useState("snake");
  const [separator, setSeparator] = useState("_");
  const [collisionStrategy, setCollisionStrategy] = useState("suffix");
  const [copied, setCopied] = useState(false);

  const preview = useMemo(() => {
    let result = template;
    const replacements = {
      poster_name: posterName || "my_poster",
      mockup_name: mockupName || "frame_mockup",
      width: "1920",
      height: "1080",
      orientation: "landscape",
      size: "1920x1080",
      date: "2026-05-17",
      time: "18-30-00",
      timestamp: "1789583400",
      index: "001",
      batch_id: "abc123",
    };

    Object.entries(replacements).forEach(([key, value]) => {
      result = result.replace(new RegExp(`\\{${key}\\}`, "g"), value);
    });

    result = applyCaseStyle(result, caseStyle);
    result = result.replace(/(?<!\d)(\d)(?!\d)/g, "0$1");
    return `${result || "mockup"}.webp`;
  }, [template, caseStyle, mockupName, posterName]);

  // Notify parent of template changes
  useEffect(() => {
    if (onTemplateChange) {
      onTemplateChange(template);
    }
  }, [template, onTemplateChange]);

  function applyCaseStyle(text, style) {
    if (style === "original") return text;
    
    // Normalize to words
    const words = text.replace(/[-_\s]+/g, ' ').split(' ').filter(w => w);
    
    switch (style) {
      case "snake":
        return words.join('_').toLowerCase();
      case "kebab":
        return words.join('-').toLowerCase();
      case "camel":
        return words[0].toLowerCase() + words.slice(1).map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('');
      case "pascal":
        return words.map(w => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()).join('');
      default:
        return text;
    }
  }

  const insertPlaceholder = (placeholder) => {
    setTemplate(prev => prev + `{${placeholder}}`);
  };

  const copyTemplate = () => {
    navigator.clipboard.writeText(template);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const presetTemplates = [
    { label: "Simple", value: "{poster_name}_{mockup_name}" },
    { label: "With Size", value: "{poster_name}_{mockup_name}_{size}" },
    { label: "Indexed", value: "{mockup_name}_{poster_name}_{index}" },
    { label: "Timestamped", value: "{poster_name}_{mockup_name}_{timestamp}" },
    { label: "Full", value: "{poster_name}_{mockup_name}_{size}_{date}" },
  ];

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      {/* Header - Always visible */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Settings className="w-4 h-4 text-purple-400" />
          <span className="font-medium text-gray-200">Naming Configuration</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400 truncate max-w-[200px]">
            {preview || "Configure template..."}
          </span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-700">
          {/* Template Input */}
          <div className="pt-4">
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Naming Template
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={template}
                onChange={(e) => setTemplate(e.target.value)}
                className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-3 py-2 text-sm text-gray-200 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
                placeholder="{poster_name}_{mockup_name}"
              />
              <button
                onClick={copyTemplate}
                className="p-2 bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors"
                title="Copy template"
              >
                {copied ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>

          {/* Preset Templates */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Quick Presets
            </label>
            <div className="flex flex-wrap gap-2">
              {presetTemplates.map((preset) => (
                <button
                  key={preset.value}
                  onClick={() => setTemplate(preset.value)}
                  className={clsx(
                    "px-3 py-1.5 text-xs rounded-full border transition-colors",
                    template === preset.value
                      ? "bg-purple-600 border-purple-500 text-white"
                      : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
                  )}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </div>

          {/* Placeholder Picker */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Insert Placeholder
            </label>
            <div className="flex flex-wrap gap-2">
              {Object.entries(PLACEHOLDER_INFO).map(([key, desc]) => (
                <button
                  key={key}
                  onClick={() => insertPlaceholder(key)}
                  className="group relative px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded hover:bg-purple-600 hover:border-purple-500 transition-colors"
                  title={desc}
                >
                  <span className="text-purple-300 group-hover:text-white">{`{${key}}`}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Settings Row */}
          <div className="grid grid-cols-3 gap-4">
            {/* Case Style */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Case Style
              </label>
              <select
                value={caseStyle}
                onChange={(e) => setCaseStyle(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-gray-200"
              >
                {CASE_STYLES.map((style) => (
                  <option key={style.value} value={style.value}>
                    {style.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Separator */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Separator
              </label>
              <select
                value={separator}
                onChange={(e) => setSeparator(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-gray-200"
              >
                <option value="_">Underscore (_)</option>
                <option value="-">Dash (-)</option>
                <option value="">None</option>
              </select>
            </div>

            {/* Collision Strategy */}
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1">
                Duplicates
              </label>
              <select
                value={collisionStrategy}
                onChange={(e) => setCollisionStrategy(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm text-gray-200"
              >
                {COLLISION_STRATEGIES.map((strategy) => (
                  <option key={strategy.value} value={strategy.value}>
                    {strategy.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Live Preview */}
          <div className="bg-gray-900 rounded-lg p-3 border border-gray-700">
            <div className="flex items-center gap-2 mb-2">
              <Info className="w-3 h-3 text-blue-400" />
              <span className="text-xs font-medium text-gray-400">Preview</span>
            </div>
            <code className="text-sm text-green-400 break-all">
              {preview || "Enter a template above..."}
            </code>
            <p className="mt-2 text-xs text-gray-500">
              Numbers like 1, 2, 3 will be automatically padded to 01, 02, 03
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
