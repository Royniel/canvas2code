"use client";

import { useState } from "react";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [framework, setFramework] = useState("React");
  
  // NEW: State to track if the code has just been copied
  const [copied, setCopied] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      setFile(selectedFile);
      setPreview(URL.createObjectURL(selectedFile));
      setCode(null);
      setError(null);
      setCopied(false);
    }
  };

  const handleGenerate = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setCopied(false);

    const formData = new FormData();
    formData.append("file", file);
    formData.append("framework", framework);

    try {
      const response = await fetch("http://127.0.0.1:8000/generate", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.status === "success") {
        setCode(data.code);
      } else {
        setError(data.message || "Failed to generate code.");
      }
    } catch (err) {
      setError("Cannot connect to backend. Is the Python server running?");
    } finally {
      setLoading(false);
    }
  };

  // NEW: The copy function
  const handleCopy = () => {
    if (code) {
      navigator.clipboard.writeText(code);
      setCopied(true);
      // Reset the button back to "Copy" after 2 seconds
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <main className="min-h-screen bg-neutral-950 text-white p-8 font-sans">
      <div className="max-w-4xl mx-auto space-y-8">
        
        <header className="text-center space-y-2">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            canvas2code
          </h1>
          <p className="text-neutral-400">Upload a UI sketch and let Gemini build it.</p>
        </header>

        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-6 shadow-2xl space-y-6">
          
          <div className="flex flex-col items-center space-y-2">
            <label className="text-sm font-medium text-neutral-400">Select Output Framework</label>
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

          <div className="flex flex-col items-center justify-center border-2 border-dashed border-neutral-700 rounded-lg p-10 hover:border-purple-500 transition-colors">
            <input 
              type="file" 
              accept="image/*" 
              onChange={handleFileChange}
              className="text-sm text-neutral-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-purple-500/10 file:text-purple-400 hover:file:bg-purple-500/20 cursor-pointer"
            />
          </div>

          {preview && (
            <div className="flex flex-col items-center space-y-4">
              <img src={preview} alt="Upload preview" className="max-h-64 rounded-lg shadow-md" />
              
              {/* The Circular Spinner Button */}
              <button 
                onClick={handleGenerate}
                disabled={loading}
                className="relative w-full py-3 bg-purple-600 hover:bg-purple-700 disabled:bg-neutral-900 disabled:border disabled:border-purple-500/30 text-white font-bold rounded-lg transition-all overflow-hidden flex justify-center items-center h-[52px]"
              >
                {loading ? (
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
                      Processing
                    </span>
                  </div>
                ) : (
                  `Generate ${framework} Code`
                )}
              </button>
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-900/30 border border-red-800 text-red-300 rounded-lg">
              {error}
            </div>
          )}

          {/* UPGRADED: Results Area with Copy Button */}
          {code && (
            <div className="mt-8 space-y-2">
              <div className="flex justify-between items-center">
                <h3 className="text-lg font-semibold text-neutral-300">Generated {framework} Code:</h3>
                
                <button
                  onClick={handleCopy}
                  className={`flex items-center space-x-2 text-sm py-1.5 px-3 rounded-md transition-all ${
                    copied 
                      ? "bg-green-500/20 text-green-400 border border-green-500/50" 
                      : "bg-neutral-800 hover:bg-neutral-700 text-neutral-300 border border-transparent"
                  }`}
                >
                  {copied ? (
                    <>
                      {/* Checkmark Icon */}
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path></svg>
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      {/* Copy Document Icon */}
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>
                      <span>Copy Code</span>
                    </>
                  )}
                </button>

              </div>
              <div className="bg-neutral-950 p-4 rounded-lg overflow-x-auto border border-neutral-800">
                <pre className="text-sm text-green-400">
                  <code>{code}</code>
                </pre>
              </div>
            </div>
          )}

        </div>
      </div>
    </main>
  );
}