"use client";

import { useEffect, useRef } from "react";

interface Props {
  logs: string[];
}

export function LogConsole({ logs }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  if (logs.length === 0) return null;

  return (
    <div className="rounded-lg border border-gray-800 bg-black p-3 font-mono text-xs max-h-40 overflow-y-auto">
      {logs.map((log, i) => (
        <div key={i} className="text-green-400 leading-5">
          <span className="text-gray-600 select-none mr-2">›</span>
          {log}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
