import React, { useEffect, useState } from 'react';
import { getGeneratedImages, getImageUrl } from '../services/api';
import { Download, RefreshCw } from 'lucide-react';

const Gallery = () => {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      const data = await getGeneratedImages();
      setImages(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="text-[#454036]">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-[#625F59]">Exports</p>
          <h1 className="text-4xl font-bold text-[#201F1D]">Gallery</h1>
          <p className="mt-2 text-[#625F59]">View and download generated mockups and optimized WebP files.</p>
        </div>
        <button
          type="button"
          onClick={loadImages}
          className="inline-flex items-center gap-2 rounded-[3px] border border-stone-400 px-3 py-2 text-sm font-medium hover:bg-[#DBD1C0]"
        >
          <RefreshCw className="size-4" />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
           {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-64 rounded-[15px] border border-stone-300 bg-[#DBD1C0]"></div>
          ))}
        </div>
      ) : images.length === 0 ? (
        <div className="rounded-[15px] border border-dashed border-stone-400 bg-[#ECE9E0] py-20 text-center">
          <h3 className="text-lg font-medium text-[#201F1D]">No outputs yet</h3>
          <p className="mt-1 text-[#625F59]">Run a batch or optimizer job first.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {images.map((img) => (
            <div key={img.filename} className="group relative overflow-hidden rounded-[15px] border border-stone-300 bg-[#DBD1C0] shadow-sm">
              <div className="relative aspect-[4/5] overflow-hidden bg-[#ECE9E0]">
                <img 
                  src={getImageUrl(img.url)} 
                  alt={img.filename}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 flex items-center justify-center bg-black/45 opacity-0 transition-opacity duration-150 group-hover:opacity-100">
                  <a 
                    href={getImageUrl(img.url)} 
                    download
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-[3px] bg-white p-2 text-[#201F1D] transition-colors hover:bg-[#ECE9E0]"
                    title="Download/Open"
                  >
                    <Download className="size-5" />
                  </a>
                </div>
              </div>
              <div className="p-3">
                <p className="truncate text-xs font-medium text-[#201F1D]">{img.filename}</p>
                {img.size_bytes && (
                  <p className="mt-1 text-xs tabular-nums text-[#625F59]">
                    {(img.size_bytes / 1024).toFixed(1)} KB
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Gallery;
