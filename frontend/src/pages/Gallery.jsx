import React, { useEffect, useState } from 'react';
import { getGeneratedImages, getImageUrl } from '../services/api';
import { Download, ExternalLink } from 'lucide-react';

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
    <div>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Gallery</h1>
      <p className="text-gray-500 mb-8">View and download your generated mockups.</p>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
           {[1, 2, 3, 4].map((n) => (
            <div key={n} className="h-64 bg-gray-200 rounded-xl animate-pulse"></div>
          ))}
        </div>
      ) : images.length === 0 ? (
        <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
          <h3 className="text-lg font-medium text-gray-900">No mockups generated yet</h3>
          <p className="text-gray-500 mt-1">Go to the Dashboard to create some.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6">
          {images.map((img) => (
            <div key={img.filename} className="group relative bg-white rounded-xl overflow-hidden shadow-sm border border-gray-100">
              <div className="aspect-[4/5] bg-gray-100 relative overflow-hidden">
                <img 
                  src={getImageUrl(img.url)} 
                  alt={img.filename}
                  className="w-full h-full object-cover"
                />
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center space-x-4">
                  <a 
                    href={getImageUrl(img.url)} 
                    download
                    target="_blank"
                    className="p-2 bg-white rounded-full hover:bg-gray-100 text-gray-900 transition-colors"
                    title="Download/Open"
                  >
                    <Download className="w-5 h-5" />
                  </a>
                </div>
              </div>
              <div className="p-3">
                <p className="text-xs text-gray-500 truncate">{img.filename}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Gallery;
