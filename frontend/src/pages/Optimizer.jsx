import React, { useEffect, useRef, useState } from 'react';
import { Download, ImagePlus, Settings2, Sparkles, Trash2 } from 'lucide-react';
import LiveJobPanel from '../components/LiveJobPanel';
import { createOptimizerJob, subscribeToJob } from '../services/api';

export default function Optimizer() {
  const [files, setFiles] = useState([]);
  const [targetKb, setTargetKb] = useState(100);
  const [quality, setQuality] = useState(90);
  const [maxWidth, setMaxWidth] = useState('');
  const [maxHeight, setMaxHeight] = useState('');
  const [currentJob, setCurrentJob] = useState(null);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');
  const sourceRef = useRef(null);

  useEffect(() => {
    return () => {
      if (sourceRef.current) sourceRef.current.close();
    };
  }, []);

  const handleFiles = (event) => {
    const next = Array.from(event.target.files || []);
    setFiles((prev) => [...prev, ...next]);
    setError('');
  };

  const clearFiles = () => {
    setFiles([]);
    setError('');
  };

  const startJob = async () => {
    if (!files.length) {
      setError('Add images before starting optimizer.');
      return;
    }
    if (sourceRef.current) {
      sourceRef.current.close();
      sourceRef.current = null;
    }
    setWorking(true);
    setError('');
    setCurrentJob(null);

    try {
      const res = await createOptimizerJob(files, {
        targetKb,
        quality,
        maxWidth: maxWidth ? Number(maxWidth) : undefined,
        maxHeight: maxHeight ? Number(maxHeight) : undefined,
      });
      setCurrentJob(res.job);
      sourceRef.current = subscribeToJob(
        res.job_id,
        (job) => {
          setCurrentJob(job);
          if (['completed', 'completed_with_errors', 'failed', 'canceled'].includes(job.status)) {
            setWorking(false);
            sourceRef.current?.close();
            sourceRef.current = null;
          }
        },
        () => setError('Live optimizer progress disconnected.')
      );
    } catch (err) {
      console.error(err);
      setError('Optimizer job failed to start.');
      setWorking(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-5 text-[#454036]">
      <header className="rounded-[15px] border border-stone-300 bg-[#DBD1C0] p-5">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-[3px] bg-[#0F0F10] text-white">
            <Sparkles className="size-5" />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-[#625F59]">Optimizer</p>
            <h1 className="text-3xl font-bold text-[#201F1D]">Convert and downsize images</h1>
          </div>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
        <section className="rounded-[15px] border border-stone-300 bg-[#ECE9E0] p-5">
          <label className="flex min-h-64 cursor-pointer flex-col items-center justify-center rounded-[15px] border-2 border-dashed border-stone-400 bg-white/40 p-8 text-center hover:bg-[#DBD1C0]">
            <ImagePlus className="mb-3 size-10 text-[#625F59]" />
            <span className="text-lg font-semibold text-[#201F1D]">Drop or choose images</span>
            <span className="mt-1 text-sm text-[#625F59]">PNG, JPG, JPEG, WEBP. Backend converts to WebP.</span>
            <input
              type="file"
              className="hidden"
              multiple
              accept="image/png,image/jpeg,image/webp"
              onChange={handleFiles}
            />
          </label>

          {!!files.length && (
            <div className="mt-4 rounded-[3px] border border-stone-300 bg-white/50">
              <div className="flex items-center justify-between border-b border-stone-300 px-3 py-2">
                <span className="text-sm font-semibold">{files.length} files ready</span>
                <button
                  type="button"
                  onClick={clearFiles}
                  className="inline-flex items-center gap-2 rounded-[3px] px-2 py-1 text-sm hover:bg-[#DBD1C0]"
                >
                  <Trash2 className="size-4" />
                  Clear
                </button>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {files.map((file) => (
                  <div key={`${file.name}-${file.size}`} className="flex items-center justify-between border-b border-stone-200 px-3 py-2 last:border-b-0">
                    <span className="truncate text-sm">{file.name}</span>
                    <span className="ml-3 shrink-0 text-xs tabular-nums text-[#625F59]">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <aside className="flex flex-col gap-5">
          <section className="rounded-[15px] border border-stone-300 bg-[#DBD1C0] p-5">
            <div className="mb-4 flex items-center gap-2">
              <Settings2 className="size-5" />
              <h2 className="text-lg font-semibold text-[#201F1D]">Output preset</h2>
            </div>

            <div className="space-y-4">
              <label className="block text-sm font-medium">
                Target size
                <span className="float-right font-mono">{targetKb} KB</span>
                <input
                  type="range"
                  min="40"
                  max="500"
                  step="10"
                  value={targetKb}
                  onChange={(e) => setTargetKb(Number(e.target.value))}
                  className="mt-2 w-full accent-indigo-700"
                  disabled={working}
                />
              </label>

              <label className="block text-sm font-medium">
                Max quality
                <span className="float-right font-mono">{quality}%</span>
                <input
                  type="range"
                  min="20"
                  max="95"
                  step="5"
                  value={quality}
                  onChange={(e) => setQuality(Number(e.target.value))}
                  className="mt-2 w-full accent-indigo-700"
                  disabled={working}
                />
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="text-sm font-medium">
                  Max width
                  <input
                    type="number"
                    value={maxWidth}
                    onChange={(e) => setMaxWidth(e.target.value)}
                    placeholder="Auto"
                    className="mt-1 w-full rounded-[3px] border border-stone-400 bg-[#ECE9E0] px-3 py-2"
                    disabled={working}
                  />
                </label>
                <label className="text-sm font-medium">
                  Max height
                  <input
                    type="number"
                    value={maxHeight}
                    onChange={(e) => setMaxHeight(e.target.value)}
                    placeholder="Auto"
                    className="mt-1 w-full rounded-[3px] border border-stone-400 bg-[#ECE9E0] px-3 py-2"
                    disabled={working}
                  />
                </label>
              </div>

              {error && <p className="rounded-[3px] bg-red-100 px-3 py-2 text-sm text-red-700">{error}</p>}

              <button
                type="button"
                onClick={startJob}
                disabled={working || !files.length}
                className="inline-flex w-full items-center justify-center gap-2 rounded-[3px] bg-[#0F0F10] px-4 py-3 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                <Download className="size-4" />
                {working ? 'Optimizing...' : 'Start optimizer job'}
              </button>
            </div>
          </section>

          <LiveJobPanel job={currentJob} onJobUpdate={setCurrentJob} />
        </aside>
      </div>
    </div>
  );
}
