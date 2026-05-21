"use client";

import { useState } from "react";

type ChatMessage = { role: "user" | "assistant"; content: string };

type Judgment = {
  score: number;
  critique: string;
  iteration: number;
};

type ProviderState = {
  status:
    | "idle"
    | "generating"
    | "rendering"
    | "judging"
    | "refining"
    | "done"
    | "error";
  code?: string;
  error?: string;
  screenshot?: string;
  renderError?: string;
  judgments: Judgment[];
  view: "code" | "preview";
};

const PROVIDERS = ["gemini", "groq", "openrouter"] as const;
type Provider = (typeof PROVIDERS)[number];

const PROVIDER_LABELS: Record<Provider, string> = {
  gemini: "Gemini 2.5 Flash",
  groq: "Llama 3.2 Vision (Groq)",
  openrouter: "Qwen-VL (OpenRouter)",
};

const IDLE_PROVIDER_STATES: Record<Provider, ProviderState> = {
  gemini: { status: "idle", view: "code", judgments: [] },
  groq: { status: "idle", view: "code", judgments: [] },
  openrouter: { status: "idle", view: "code", judgments: [] },
};

const GENERATING_PROVIDER_STATES: Record<Provider, ProviderState> = {
  gemini: { status: "generating", view: "code", judgments: [] },
  groq: { status: "generating", view: "code", judgments: [] },
  openrouter: { status: "generating", view: "code", judgments: [] },
};

const scoreClass = (score: number) =>
  score >= 0.85
    ? "bg-green-500/20 text-green-400"
    : score >= 0.5
    ? "bg-yellow-500/20 text-yellow-400"
    : "bg-red-500/20 text-red-400";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [framework, setFramework] = useState("React");
  const [copied, setCopied] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [providerStates, setProviderStates] =
    useState<Record<Provider, ProviderState>>(IDLE_PROVIDER_STATES);
  const [selectedProvider, setSelectedProvider] = useState<Provider | null>(null);
  const [currentCode, setCurrentCode] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [refinementInput, setRefinementInput] = useState("");

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setError(null);
      setCopied(null);
      setThreadId(crypto.randomUUID());
      setProviderStates(IDLE_PROVIDER_STATES);
      setSelectedProvider(null);
      setCurrentCode(null);
      setMessages([]);
      setRefinementInput("");
    }
  };

  const updateProvider = (provider: Provider, patch: Partial<ProviderState>) => {
    setProviderStates((prev) => ({
      ...prev,
      [provider]: { ...prev[provider], ...patch },
    }));
  };

  const appendJudgment = (provider: Provider, judgment: Judgment) => {
    setProviderStates((prev) => ({
      ...prev,
      [provider]: {
        ...prev[provider],
        judgments: [...prev[provider].judgments, judgment],
      },
    }));
  };

  const consumeSSE = async (response: Response) => {
    if (!response.body) {
      setError("No response body from backend.");
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const event of events) {
        if (!event.startsWith("data: ")) continue;
        const payload = JSON.parse(event.slice(6));
        switch (payload.type) {
          case "status":
            setStatus(payload.message);
            break;
          case "code":
            setCurrentCode(payload.content);
            setMessages((m) => [
              ...m,
              { role: "assistant", content: "Code updated." },
            ]);
            break;
          case "error":
            setError(payload.message);
            break;
          case "provider_status":
            updateProvider(payload.provider as Provider, {
              status: payload.status,
            });
            break;
          case "provider_code":
            updateProvider(payload.provider as Provider, {
              code: payload.content,
            });
            break;
          case "provider_screenshot":
            updateProvider(payload.provider as Provider, {
              screenshot: payload.image_base64,
            });
            break;
          case "provider_error":
            if (payload.stage === "rendering") {
              updateProvider(payload.provider as Provider, {
                renderError: payload.message,
              });
            } else {
              updateProvider(payload.provider as Provider, {
                status: "error",
                error: payload.message,
              });
            }
            break;
          case "judgment":
            appendJudgment(payload.provider as Provider, {
              score: payload.score,
              critique: payload.critique,
              iteration: payload.iteration,
            });
            break;
          case "refining":
            // Visual feedback that a new iteration started for this provider.
            updateProvider(payload.provider as Provider, {
              status: "refining",
            });
            break;
        }
      }
    }
  };

  const handleGenerate = async () => {
    if (!file || !threadId) return;

    setLoading(true);
    setError(null);
    setCopied(null);
    setStatus("");
    setCurrentCode(null);
    setSelectedProvider(null);
    setProviderStates(GENERATING_PROVIDER_STATES);
    setMessages([
      { role: "user", content: `Generate ${framework} code from this sketch.` },
    ]);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("framework", framework);
    formData.append("thread_id", threadId);

    try {
      const response = await fetch("http://127.0.0.1:8000/generate", {
        method: "POST",
        body: formData,
      });
      await consumeSSE(response);
    } catch (err) {
      setError("Cannot connect to backend. Is the Python server running?");
    } finally {
      setLoading(false);
      setStatus("");
    }
  };

  const handleSelectWinner = async (provider: Provider) => {
    if (!threadId) return;
    const state = providerStates[provider];
    if (!state.code) return;

    try {
      const res = await fetch("http://127.0.0.1:8000/select-winner", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, provider }),
      });
      if (!res.ok) {
        const text = await res.text();
        setError(`Failed to select winner: ${text}`);
        return;
      }
      setSelectedProvider(provider);
      setCurrentCode(state.code);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `Selected ${PROVIDER_LABELS[provider]}.`,
        },
      ]);
    } catch {
      setError("Cannot connect to backend.");
    }
  };

  const handleRefine = async () => {
    const trimmed = refinementInput.trim();
    if (!trimmed || !threadId || loading || !selectedProvider) return;

    setLoading(true);
    setError(null);
    setStatus("");
    setMessages((m) => [...m, { role: "user", content: trimmed }]);
    setRefinementInput("");

    try {
      const response = await fetch("http://127.0.0.1:8000/refine", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, message: trimmed }),
      });
      await consumeSSE(response);
    } catch (err) {
      setError("Cannot connect to backend. Is the Python server running?");
    } finally {
      setLoading(false);
      setStatus("");
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const switchModel = () => {
    setSelectedProvider(null);
    setCurrentCode(null);
  };

  const finalScores: Record<Provider, number> = {
    gemini: providerStates.gemini.judgments.at(-1)?.score ?? -1,
    groq: providerStates.groq.judgments.at(-1)?.score ?? -1,
    openrouter: providerStates.openrouter.judgments.at(-1)?.score ?? -1,
  };
  const maxScore = Math.max(...Object.values(finalScores));
  const winner: Provider | null =
    maxScore > 0
      ? (PROVIDERS.find((p) => finalScores[p] === maxScore) ?? null)
      : null;

  const anyComparisonAvailable = PROVIDERS.some(
    (p) => providerStates[p].status !== "idle"
  );

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-8 font-sans">
      <div className="max-w-7xl mx-auto space-y-8">

        <header className="text-center space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            canvas2code
          </h1>
          <p className="text-neutral-400">
            Three vision models generate, render, and self-correct against the original sketch.
          </p>
        </header>

        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 shadow-2xl space-y-6">

          <div className="flex flex-col items-center space-y-2">
            <label className="text-sm font-medium text-neutral-400">
              Select Output Framework
            </label>
            <select
              value={framework}
              onChange={(e) => setFramework(e.target.value)}
              className="bg-neutral-950 border border-neutral-700 text-white text-sm rounded-lg focus:ring-purple-500 focus:border-purple-500 block w-64 p-2.5 outline-none transition-all cursor-pointer"
            >
              <option value="React">React (Next.js)</option>
              <option value="Vue 3">Vue 3 (Composition API)</option>
              <option value="HTML/CSS">Vanilla HTML/CSS</option>
            </select>
          </div>

          <label className="relative flex flex-col items-center justify-center border-2 border-dashed border-neutral-700 rounded-lg p-10 hover:border-purple-500 transition-all bg-neutral-900/50 hover:bg-neutral-800/50 cursor-pointer group">
            <div className="flex flex-col items-center space-y-3 pointer-events-none">
              <div className="p-3 bg-purple-500/10 rounded-full text-purple-400 group-hover:bg-purple-500/20 transition-colors">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path>
                </svg>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-neutral-200">
                  {file ? file.name : "Click to upload an image"}
                </p>
                <p className="text-xs text-neutral-500 mt-1">PNG, JPG, WebP up to 10MB</p>
              </div>
            </div>

            <input
              id="file-upload"
              type="file"
              accept="image/*"
              onChange={handleFileChange}
              className="sr-only"
            />
          </label>

          {preview && (
            <div className="flex flex-col items-center">
              <img src={preview} alt="Upload preview" className="max-h-64 rounded-lg shadow-md" />
            </div>
          )}

          <button
            onClick={handleGenerate}
            disabled={loading || !file}
            className="relative w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-neutral-800 disabled:text-neutral-500 disabled:opacity-50 disabled:cursor-not-allowed disabled:border-transparent text-white font-bold rounded-lg transition-all overflow-hidden flex justify-center items-center h-[52px]"
          >
            {loading && !selectedProvider ? (
              <div className="flex items-center space-x-3">
                <style>{`
                  .spinner-circle {
                    stroke-dasharray: 1, 200;
                    stroke-dashoffset: 0;
                    animation: dash 1.5s ease-in-out infinite;
                  }
                  @keyframes dash {
                    0% { stroke-dasharray: 1, 200; stroke-dashoffset: 0; }
                    50% { stroke-dasharray: 89, 200; stroke-dashoffset: -35px; }
                    100% { stroke-dasharray: 89, 200; stroke-dashoffset: -124px; }
                  }
                `}</style>
                <svg className="animate-spin h-5 w-5 text-purple-400 drop-shadow-[0_0_8px_rgba(168,85,247,0.8)]" viewBox="25 25 50 50">
                  <circle className="spinner-circle" cx="50" cy="50" r="20" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
                </svg>
                <span className="text-purple-400 font-mono text-sm uppercase tracking-widest animate-pulse">
                  {status || "Processing"}
                </span>
              </div>
            ) : selectedProvider ? (
              `Re-generate (starts a new comparison)`
            ) : (
              `Generate ${framework} Code`
            )}
          </button>

          {error && (
            <div className="p-4 bg-red-900/30 border border-red-800 text-red-300 rounded-lg">
              {error}
            </div>
          )}

          {/* Comparison view */}
          {anyComparisonAvailable && !selectedProvider && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {PROVIDERS.map((p) => {
                const ps = providerStates[p];
                const inProgress =
                  ps.status === "generating" ||
                  ps.status === "rendering" ||
                  ps.status === "judging" ||
                  ps.status === "refining";
                const pillClass =
                  ps.status === "done"
                    ? "bg-green-500/20 text-green-400"
                    : ps.status === "error"
                    ? "bg-red-500/20 text-red-400"
                    : inProgress
                    ? "bg-purple-500/20 text-purple-400 animate-pulse"
                    : "bg-neutral-700 text-neutral-400";

                const canPreview = !!ps.screenshot;
                const latestScore = ps.judgments.at(-1)?.score ?? null;
                const isWinner = winner === p;

                return (
                  <div
                    key={p}
                    className={`bg-neutral-950 border rounded-lg p-4 flex flex-col ${
                      isWinner
                        ? "border-purple-500 shadow-lg shadow-purple-500/20"
                        : "border-neutral-800"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2 gap-2">
                      <h3 className="text-sm font-semibold text-neutral-200 truncate">
                        {PROVIDER_LABELS[p]}
                      </h3>
                      <div className="flex items-center gap-1">
                        {latestScore !== null && (
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-mono ${scoreClass(latestScore)}`}
                            title="Visual fidelity score"
                          >
                            {(latestScore * 100).toFixed(0)}
                          </span>
                        )}
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase tracking-wider ${pillClass}`}
                        >
                          {ps.status}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1 mb-2">
                      <button
                        onClick={() => updateProvider(p, { view: "code" })}
                        className={`text-[10px] px-2 py-0.5 rounded ${
                          ps.view === "code"
                            ? "bg-purple-600 text-white"
                            : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                        }`}
                      >
                        Code
                      </button>
                      <button
                        onClick={() => updateProvider(p, { view: "preview" })}
                        disabled={!canPreview}
                        className={`text-[10px] px-2 py-0.5 rounded ${
                          ps.view === "preview" && canPreview
                            ? "bg-purple-600 text-white"
                            : "bg-neutral-800 text-neutral-400 hover:bg-neutral-700"
                        } disabled:opacity-30 disabled:cursor-not-allowed`}
                      >
                        Preview
                      </button>
                      {ps.renderError && (
                        <span
                          className="text-[10px] text-red-400 ml-1"
                          title={ps.renderError}
                        >
                          render failed
                        </span>
                      )}
                    </div>

                    <div className="flex-1 min-h-[200px] max-h-[400px] overflow-auto bg-neutral-900 rounded border border-neutral-800 p-2 mb-3">
                      {ps.error ? (
                        <div className="text-xs text-red-300 whitespace-pre-wrap">
                          {ps.error}
                        </div>
                      ) : ps.view === "preview" && ps.screenshot ? (
                        <img
                          src={`data:image/png;base64,${ps.screenshot}`}
                          alt={`${PROVIDER_LABELS[p]} preview`}
                          className="w-full"
                        />
                      ) : ps.code ? (
                        <pre className="text-xs text-green-400 whitespace-pre-wrap">
                          {ps.code}
                        </pre>
                      ) : (
                        <div className="text-xs text-neutral-500 italic">Waiting...</div>
                      )}
                    </div>

                    {ps.judgments.length > 0 && (
                      <div className="mb-3 space-y-1 max-h-32 overflow-y-auto border-l-2 border-neutral-800 pl-2">
                        {ps.judgments.map((j, i) => (
                          <div key={i} className="text-[10px] leading-snug">
                            <span className="font-mono text-neutral-400">
                              {j.iteration === 0 ? "Initial" : `Iter ${j.iteration}`}:{" "}
                            </span>
                            <span className={`font-mono ${
                              j.score >= 0.75 ? "text-green-400" : "text-yellow-400"
                            }`}>
                              {(j.score * 100).toFixed(0)}%
                            </span>
                            <span className="text-neutral-500"> — {j.critique}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex gap-2">
                      <button
                        onClick={() => ps.code && handleCopy(ps.code, p)}
                        disabled={!ps.code}
                        className="text-xs px-2 py-1 bg-neutral-800 hover:bg-neutral-700 disabled:opacity-30 disabled:cursor-not-allowed text-neutral-300 rounded"
                      >
                        {copied === p ? "Copied!" : "Copy"}
                      </button>
                      <button
                        onClick={() => handleSelectWinner(p)}
                        disabled={!ps.code || loading}
                        className={`flex-1 text-xs px-2 py-1 disabled:opacity-30 disabled:cursor-not-allowed text-white font-medium rounded ${
                          isWinner
                            ? "bg-purple-500 hover:bg-purple-600 ring-1 ring-purple-300/50"
                            : "bg-purple-600 hover:bg-purple-700"
                        }`}
                      >
                        {isWinner ? "★ Use this" : "Use this"}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Refinement view (after selection) */}
          {selectedProvider && currentCode && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-neutral-300">
                  Refining with{" "}
                  <span className="text-purple-400">
                    {PROVIDER_LABELS[selectedProvider]}
                  </span>
                </h3>
                <button
                  onClick={switchModel}
                  className="text-xs px-3 py-1.5 bg-neutral-800 hover:bg-neutral-700 text-neutral-300 rounded"
                >
                  Switch model
                </button>
              </div>

              <div className="bg-neutral-950 p-4 rounded-lg overflow-x-auto border border-neutral-800 relative">
                <button
                  onClick={() => handleCopy(currentCode, "current")}
                  className={`absolute top-2 right-2 text-xs px-2 py-1 rounded ${
                    copied === "current"
                      ? "bg-green-500/20 text-green-400"
                      : "bg-neutral-800 hover:bg-neutral-700 text-neutral-300"
                  }`}
                >
                  {copied === "current" ? "Copied!" : "Copy"}
                </button>
                <pre className="text-sm text-green-400">
                  <code>{currentCode}</code>
                </pre>
              </div>

              <div className="space-y-3">
                <h4 className="text-sm font-semibold text-neutral-300">Conversation</h4>

                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {messages.map((m, i) => (
                    <div
                      key={i}
                      className={`px-3 py-2 rounded-lg text-sm ${
                        m.role === "user"
                          ? "bg-purple-900/30 text-purple-100 border border-purple-800/50"
                          : "bg-neutral-800 text-neutral-300 border border-neutral-700"
                      }`}
                    >
                      <div className="text-[10px] uppercase tracking-wider text-neutral-500 mb-1">
                        {m.role}
                      </div>
                      <div>{m.content}</div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={refinementInput}
                    onChange={(e) => setRefinementInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !loading) handleRefine();
                    }}
                    placeholder="Ask for a change…"
                    disabled={loading}
                    className="flex-1 bg-neutral-950 border border-neutral-700 text-white text-sm rounded-lg p-2.5 outline-none focus:border-purple-500 disabled:opacity-50"
                  />
                  <button
                    onClick={handleRefine}
                    disabled={loading || !refinementInput.trim()}
                    className="px-4 bg-purple-600 hover:bg-purple-700 disabled:bg-neutral-800 disabled:text-neutral-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-all"
                  >
                    {loading ? "..." : "Send"}
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </main>
  );
}
