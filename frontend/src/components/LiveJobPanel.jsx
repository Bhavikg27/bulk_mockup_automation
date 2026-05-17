import React from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Download,
  Loader2,
  PauseCircle,
  XCircle,
} from 'lucide-react';
import ProgressBar from './ProgressBar';
import { cancelJob, getExportZipUrl, getImageUrl } from '../services/api';

const terminalStatuses = new Set(['completed', 'completed_with_errors', 'failed', 'canceled']);

const statusLabel = {
  queued: 'Queued',
  running: 'Running',
  completed: 'Complete',
  completed_with_errors: 'Complete with errors',
  failed: 'Failed',
  canceled: 'Canceled',
};

const stageLabel = {
  queued: 'Queued',
  uploading: 'Uploading',
  decoding: 'Decoding',
  rendering: 'Rendering mockup',
  optimizing: 'Optimizing WebP',
  saving: 'Saving file',
  done: 'Done',
  completed: 'Complete',
  completed_with_errors: 'Complete with errors',
  failed: 'Failed',
  canceled: 'Canceled',
};

function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${(bytes / (1024 ** index)).toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function itemIcon(item) {
  if (item.status === 'done') return <CheckCircle2 className="size-4 text-emerald-600" />;
  if (item.status === 'failed') return <AlertCircle className="size-4 text-red-600" />;
  if (item.status === 'canceled') return <PauseCircle className="size-4 text-stone-500" />;
  if (item.status === 'running') return <Loader2 className="size-4 animate-spin text-indigo-600" />;
  return <Clock className="size-4 text-stone-400" />;
}

export default function LiveJobPanel({ job, onJobUpdate, onDone }) {
  if (!job) return null;

  const total = job.total || job.items?.length || 0;
  const finished = (job.completed || 0) + (job.failed || 0);
  const isTerminal = terminalStatuses.has(job.status);
  const canDownload = job.items?.some((item) => item.status === 'done' && item.output_url);

  const handleCancel = async () => {
    const updated = await cancelJob(job.id);
    onJobUpdate?.(updated);
  };

  return (
    <section className="rounded-[15px] border border-stone-300 bg-[#DBD1C0] p-4 text-[#454036] shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold uppercase tracking-wide text-[#625F59]">
              Live Queue
            </span>
            <span className="rounded-[3px] bg-[#ECE9E0] px-2 py-1 text-xs font-medium">
              {statusLabel[job.status] || job.status}
            </span>
          </div>
          <h3 className="mt-1 text-xl font-semibold text-[#201F1D]">
            {stageLabel[job.stage] || job.stage}
          </h3>
          <p className="mt-1 text-sm text-[#625F59]">
            {finished}/{total} files finished
            {job.current_file ? ` - ${job.current_file}` : ''}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {canDownload && (
            <a
              href={getExportZipUrl(job.id)}
              className="inline-flex items-center gap-2 rounded-[3px] bg-[#0F0F10] px-3 py-2 text-sm font-medium text-white"
            >
              <Download className="size-4" />
              ZIP
            </a>
          )}
          {!isTerminal && (
            <button
              type="button"
              onClick={handleCancel}
              className="inline-flex items-center gap-2 rounded-[3px] border border-stone-400 px-3 py-2 text-sm font-medium text-[#454036] hover:bg-[#ECE9E0]"
            >
              <XCircle className="size-4" />
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex justify-between text-xs tabular-nums text-[#625F59]">
          <span>Real processing progress</span>
          <span>{job.percent || 0}%</span>
        </div>
        <ProgressBar progress={job.percent || 0} />
      </div>

      <div className="mt-4 max-h-72 overflow-y-auto rounded-[3px] border border-stone-300 bg-[#ECE9E0]">
        {(job.items || []).map((item) => (
          <div
            key={item.id}
            className="grid grid-cols-[24px_1fr_auto] items-center gap-3 border-b border-stone-300 px-3 py-2 last:border-b-0"
          >
            {itemIcon(item)}
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-[#201F1D]" title={item.filename}>
                {item.filename}
              </p>
              <p className="text-xs text-[#625F59]">
                {stageLabel[item.stage] || item.stage}
                {item.error ? ` - ${item.error}` : ''}
              </p>
            </div>
            <div className="text-right text-xs tabular-nums text-[#625F59]">
              {item.output_size ? formatBytes(item.output_size) : `${item.percent || 0}%`}
              {item.output_url && (
                <a
                  href={getImageUrl(item.output_url)}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-3 font-semibold text-indigo-700"
                >
                  Open
                </a>
              )}
            </div>
          </div>
        ))}
      </div>

      {isTerminal && onDone && (
        <button
          type="button"
          onClick={onDone}
          className="mt-4 w-full rounded-[3px] bg-[#0F0F10] px-3 py-2 text-sm font-semibold text-white"
        >
          Open gallery
        </button>
      )}
    </section>
  );
}
