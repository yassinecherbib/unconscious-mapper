"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";

const ChatContent = dynamic(() => import("./ChatContent"), { ssr: false });

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "60vh" }}>
          <div style={{
            width: 32, height: 32, borderRadius: "50%",
            border: "2px solid var(--neon-violet)", borderTopColor: "transparent",
            animation: "spin 1s linear infinite",
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      }
    >
      <ChatContent />
    </Suspense>
  );
}
