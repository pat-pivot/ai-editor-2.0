"use client";

import { useRef, useCallback } from "react";
import Editor, { OnMount, OnChange } from "@monaco-editor/react";
import type { editor } from "monaco-editor";
import { cn } from "@/lib/utils";

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  readOnly?: boolean;
  className?: string;
  minHeight?: number;
  maxHeight?: number;
}

export function PromptEditor({
  value,
  onChange,
  readOnly = false,
  className,
  minHeight = 200,
  maxHeight = 400,
}: PromptEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);

  const handleEditorDidMount: OnMount = useCallback((editor, monaco) => {
    editorRef.current = editor;

    // Define custom theme matching our design system
    monaco.editor.defineTheme("pivot-light", {
      base: "vs",
      inherit: true,
      rules: [
        { token: "comment", foreground: "6b7280", fontStyle: "italic" },
        { token: "keyword", foreground: "ea580c" },
        { token: "string", foreground: "059669" },
        { token: "number", foreground: "7c3aed" },
      ],
      colors: {
        "editor.background": "#fafaf9",
        "editor.foreground": "#1c1917",
        "editor.lineHighlightBackground": "#f5f5f4",
        "editor.selectionBackground": "#fed7aa",
        "editor.inactiveSelectionBackground": "#fef3c7",
        "editorLineNumber.foreground": "#a8a29e",
        "editorLineNumber.activeForeground": "#78716c",
        "editorCursor.foreground": "#ea580c",
        "editor.wordHighlightBackground": "#fef3c7",
        "editorBracketMatch.background": "#fed7aa",
        "editorBracketMatch.border": "#f97316",
      },
    });

    monaco.editor.setTheme("pivot-light");

    // Configure editor options
    editor.updateOptions({
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 13,
      lineHeight: 20,
      padding: { top: 16, bottom: 16 },
      minimap: { enabled: false },
      scrollBeyondLastLine: false,
      wordWrap: "on",
      lineNumbers: "on",
      renderLineHighlight: "line",
      folding: true,
      automaticLayout: true,
      tabSize: 2,
      insertSpaces: true,
      bracketPairColorization: { enabled: true },
      guides: {
        indentation: true,
        bracketPairs: true,
      },
    });

    // Focus editor
    if (!readOnly) {
      editor.focus();
    }
  }, [readOnly]);

  const handleChange: OnChange = useCallback(
    (value) => {
      onChange(value ?? "");
    },
    [onChange]
  );

  return (
    <div
      className={cn(
        "rounded-md border bg-stone-50 overflow-hidden",
        className
      )}
      style={{ minHeight, maxHeight }}
    >
      <Editor
        height="100%"
        defaultLanguage="markdown"
        value={value}
        onChange={handleChange}
        onMount={handleEditorDidMount}
        options={{
          readOnly,
          domReadOnly: readOnly,
        }}
        loading={
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            Loading editor...
          </div>
        }
      />
    </div>
  );
}
