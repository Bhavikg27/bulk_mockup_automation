import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Stage, Layer, Image as KonvaImage, Circle, Line } from "react-konva";
import useImage from "use-image";
import {
  Upload,
  Save,
  Play,
  Layers,
  Check,
  RefreshCw,
  Columns,
} from "lucide-react";
import {
  uploadMockup,
  saveConfig,
  generateMockup,
  generateBulkMockups,
  getMockups,
  getImageUrl,
  getPreview,
} from "../services/api";
import clsx from "clsx";
import Toast from "../components/Toast";

const Editor = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [mockupId, setMockupId] = useState(id);
  const [mockupName, setMockupName] = useState("");
  const [imageUrl, setImageUrl] = useState(null);
  const [image] = useImage(imageUrl);
  const lineRef = useRef(null);

  // Preview State
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewImage] = useImage(previewUrl);
  const [sideBySide, setSideBySide] = useState(false);

  // Zoom & Pan State
  const [zoom, setZoom] = useState(1);
  const [stagePos, setStagePos] = useState({ x: 0, y: 0 });
  const [layout, setLayout] = useState({ scale: 1, offsetX: 0, offsetY: 0 });

  // Canvas dimensions (responsive)
  const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
  const containerRef = useRef(null);

  // Points: TopLeft, TopRight, BottomRight, BottomLeft
  const [points, setPoints] = useState([
    { x: 100, y: 100 },
    { x: 300, y: 100 },
    { x: 300, y: 300 },
    { x: 100, y: 300 },
  ]);

  const [designs, setDesigns] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [toast, setToast] = useState(null); // { message, type }

  // Initial Load
  useEffect(() => {
    if (id && id !== "new") {
      loadMockup(id);
    }
  }, [id]);

  // Handle resizing & Layout Calculation
  useEffect(() => {
    const updateLayout = () => {
      if (containerRef.current) {
        const cw = containerRef.current.offsetWidth;
        const ch = containerRef.current.offsetHeight;

        let newScale = 1;
        let newOffsetX = 0;
        let newOffsetY = 0;

        if (image) {
          const scaleW = cw / image.width;
          const scaleH = ch / image.height;
          newScale = Math.min(scaleW, scaleH) * 0.9; // 90% fit
          newOffsetX = (cw - image.width * newScale) / 2;
          newOffsetY = (ch - image.height * newScale) / 2;
        }

        setLayout({
          scale: newScale,
          offsetX: newOffsetX,
          offsetY: newOffsetY,
        });
        setStageSize({ width: cw, height: ch });
      }
    };
    updateLayout();
    window.addEventListener("resize", updateLayout);
    return () => window.removeEventListener("resize", updateLayout);
  }, [image]);

  const loadMockup = async (mid) => {
    const allMockups = await getMockups();
    const config = allMockups.find((m) => m.id === mid);
    if (config) {
      setMockupId(config.id);
      setMockupName(config.name);
      setImageUrl(getImageUrl(`/mockups/${config.name}`));
      if (config.points && config.points.length === 4) {
        setPoints(config.points);
      }
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      const res = await uploadMockup(file);
      setMockupName(res.filename);
      setImageUrl(getImageUrl(res.url));
      setMockupId(res.filename);
      navigate(`/editor/${res.filename}`, { replace: true });
    } catch (err) {
      console.error(err);
      setToast({ message: "Upload failed", type: "error" });
    }
  };

  const handleDesignUpload = (e) => {
    // Reset preview when new design is uploaded
    setDesigns([...e.target.files]);
    setPreviewUrl(null);
  };

  // Fetch preview from backend
  const updatePreview = async (currentPoints) => {
    if (designs.length === 0 || !mockupId) return;

    try {
      const url = await getPreview(mockupId, designs[0], currentPoints);
      setPreviewUrl(url);
    } catch (err) {
      console.error("Preview failed", err);
    }
  };

  // Helper to update line during drag without state update
  const handleDragMove = (index, e) => {
    if (!lineRef.current) return;

    const stagePoints = points.map((p) => ({
      x: p.x * layout.scale + layout.offsetX,
      y: p.y * layout.scale + layout.offsetY,
    }));

    // Update the moving point with current drag position
    stagePoints[index] = {
      x: e.target.x(),
      y: e.target.y(),
    };

    const flatPoints = [
      stagePoints[0].x,
      stagePoints[0].y,
      stagePoints[1].x,
      stagePoints[1].y,
      stagePoints[2].x,
      stagePoints[2].y,
      stagePoints[3].x,
      stagePoints[3].y,
      stagePoints[0].x,
      stagePoints[0].y,
    ];

    lineRef.current.points(flatPoints);
  };

  // Only update state on drag END to prevent re-render during drag
  const handleDragEnd = (index, e) => {
    const newPoints = [...points];

    // Calculate new position from where Konva placed the circle
    const newX = (e.target.x() - layout.offsetX) / layout.scale;
    const newY = (e.target.y() - layout.offsetY) / layout.scale;

    newPoints[index] = {
      x: newX,
      y: newY,
    };
    setPoints(newPoints);

    if (designs.length > 0) {
      updatePreview(newPoints);
    }
  };

  // Spacebar: Reset view to fit (same as Fit button)
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === "Space" && image && mockupId) {
        e.preventDefault();
        // Reset zoom and pan to fit view
        setZoom(1);
        setStagePos({ x: 0, y: 0 });
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [image, mockupId]);

  const handleSaveConfig = async () => {
    if (!mockupId) return;
    try {
      await saveConfig({
        id: mockupId,
        name: mockupName,
        points: points,
      });
      setToast({ message: "Configuration saved successfully!", type: "success" });
    } catch (err) {
      console.error(err);
      setToast({ message: "Failed to save config", type: "error" });
    }
  };

  const handleGenerate = async () => {
    if (designs.length === 0) return setToast({ message: "Please upload a design first", type: "error" });
    if (!mockupId) return setToast({ message: "No mockup selected", type: "error" });

    setGenerating(true);
    try {
      // Bulk Generation Logic
      const res = await generateBulkMockups(mockupId, designs);

      if (res.results && res.results.length > 0) {
        // Set the first one as preview
        const first = res.results[0];
        setGeneratedUrl(getImageUrl(first.url));

        // Show summary
        let msg = `Generations Complete! Created ${res.count} mockups.`;
        if (res.errors && res.errors.length > 0) {
          msg += ` (${res.errors.length} errors)`;
        }
        setToast({ message: msg, type: "success" });
      } else if (res.errors && res.errors.length > 0) {
        setToast({ message: `Failed to generate: ${res.errors.join(", ")}`, type: "error" });
      } else {
        // Fallback for single legacy response
        setGeneratedUrl(getImageUrl(res.url));
        setToast({ message: "Mockup generated successfully!", type: "success" });
      }
    } catch (err) {
      console.error(err);
      setToast({ message: "Generation failed", type: "error" });
    } finally {
      setGenerating(false);
    }
  };

  // Zoom Controls
  const handleZoom = (delta) => {
    const newZoom = Math.max(0.1, zoom + delta);
    setZoom(newZoom);
  };

  // Mouse Wheel Zoom
  const handleWheel = (e) => {
    e.evt.preventDefault();
    const scaleBy = 1.1;
    const oldScale = zoom;
    const stage = e.target.getStage();
    const pointer = stage.getPointerPosition();

    const mousePointTo = {
      x: (pointer.x - stage.x()) / oldScale,
      y: (pointer.y - stage.y()) / oldScale,
    };

    const newScale = e.evt.deltaY < 0 ? oldScale * scaleBy : oldScale / scaleBy;
    setZoom(newScale);

    const newPos = {
      x: pointer.x - mousePointTo.x * newScale,
      y: pointer.y - mousePointTo.y * newScale,
    };
    setStagePos(newPos);
  };

  return (
    <div className="h-full flex flex-col gap-6 relative">
      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
      {/* Toolbar */}
      <div className="flex justify-between items-center bg-white/80 backdrop-blur-md p-3 rounded-lg shadow-sm border border-gray-200">
        <h2 className="font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-blue-600">
          Editor Space
        </h2>
        <div className="flex gap-2">
          <button
            onClick={() => setSideBySide(!sideBySide)}
            className={clsx(
              "flex items-center px-3 py-1.5 rounded-md text-sm font-medium transition-colors",
              sideBySide
                ? "bg-primary text-white shadow-lg shadow-primary/30"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            )}
          >
            <Columns className="w-4 h-4 mr-2" />
            Side-by-Side
          </button>
          {mockupId && designs.length > 0 && (
            <button
              onClick={() => updatePreview(points)}
              className="flex items-center px-3 py-1.5 rounded-md text-sm font-medium bg-secondary/10 text-secondary hover:bg-secondary/20 transition-colors"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh Preview
            </button>
          )}
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 flex-1 h-0">
        {/* Left: Canvas Area */}
        <div className="flex-1 bg-gray-50 rounded-xl shadow-inner border border-gray-200 overflow-hidden flex flex-col relative group">
          <div className="flex-1 relative" ref={containerRef}>
            {!imageUrl ? (
              <div className="absolute inset-0 flex items-center justify-center text-gray-400">
                <div className="text-center">
                  <Upload className="w-12 h-12 mx-auto text-gray-300 mb-2" />
                  <p>Upload a mockup image to start</p>
                </div>
              </div>
            ) : (
              <>
                <Stage
                  width={stageSize.width}
                  height={stageSize.height}
                  onWheel={handleWheel}
                  scaleX={zoom}
                  scaleY={zoom}
                  x={stagePos.x}
                  y={stagePos.y}
                  draggable
                  onDragEnd={(e) => {
                    // Update stage pos for smooth panning tracking
                    setStagePos({ x: e.target.x(), y: e.target.y() });
                  }}
                >
                  <Layer>
                    {/* Base Mockup Image */}
                    {image && (
                      <KonvaImage
                        image={image}
                        scaleX={layout.scale}
                        scaleY={layout.scale}
                        x={layout.offsetX}
                        y={layout.offsetY}
                      />
                    )}

                    {/* PREVIEW LAYER */}
                    {previewImage && (
                      <KonvaImage
                        image={previewImage}
                        scaleX={layout.scale}
                        scaleY={layout.scale}
                        x={layout.offsetX}
                        y={layout.offsetY}
                        opacity={1}
                        listening={false}
                      />
                    )}

                    <Line
                      ref={lineRef}
                      points={[
                        points[0].x,
                        points[0].y,
                        points[1].x,
                        points[1].y,
                        points[2].x,
                        points[2].y,
                        points[3].x,
                        points[3].y,
                        points[0].x,
                        points[0].y,
                      ].map((v, i) => {
                        return (
                          v * layout.scale +
                          (i % 2 === 0 ? layout.offsetX : layout.offsetY)
                        );
                      })}
                      stroke="#3b82f6"
                      strokeWidth={1 / zoom} // Scale stroke so it stays thin
                      dash={[5, 5]}
                      closed
                    />

                    {points.map((pt, i) => (
                      <Circle
                        key={i}
                        x={pt.x * layout.scale + layout.offsetX}
                        y={pt.y * layout.scale + layout.offsetY}
                        radius={8 / zoom}
                        fill="#3b82f6"
                        stroke="white"
                        strokeWidth={2 / zoom}
                        draggable
                        onDragStart={(e) => {
                          e.cancelBubble = true;
                        }}
                        onDragMove={(e) => {
                            e.cancelBubble = true;
                            handleDragMove(i, e);
                        }}
                        onDragEnd={(e) => {
                          e.cancelBubble = true;
                          handleDragEnd(i, e);
                        }}
                        onMouseEnter={(e) => {
                          const container = e.target.getStage().container();
                          container.style.cursor = "move";
                        }}
                        onMouseLeave={(e) => {
                          const container = e.target.getStage().container();
                          container.style.cursor = "default";
                        }}
                      />
                    ))}
                  </Layer>
                </Stage>

                {/* FLOATING ZOOM CONTROLS */}
                <div className="absolute bottom-4 left-4 flex space-x-2">
                  <div className="bg-white/90 backdrop-blur shadow-lg rounded-lg border border-gray-200 p-1 flex items-center space-x-1">
                    <button
                      onClick={() => handleZoom(-0.1)}
                      className="p-1.5 hover:bg-gray-100 rounded text-gray-600"
                    >
                      -
                    </button>
                    <span className="text-xs font-mono w-12 text-center">
                      {Math.round(zoom * 100)}%
                    </span>
                    <button
                      onClick={() => handleZoom(0.1)}
                      className="p-1.5 hover:bg-gray-100 rounded text-gray-600"
                    >
                      +
                    </button>
                    <div className="w-px h-4 bg-gray-300 mx-1"></div>
                    <button
                      onClick={() => {
                        setZoom(1);
                        setStagePos({ x: 0, y: 0 });
                      }}
                      className="p-1.5 hover:bg-gray-100 rounded text-xs px-2 text-gray-600"
                    >
                      Fit
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Area */}
        {sideBySide ? (
          <div className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden flex flex-col relative">
            <div className="bg-gray-50 p-3 border-b border-gray-100 font-medium text-gray-700">
              Live Result
            </div>
            <div className="flex-1 bg-gray-100 flex items-center justify-center p-4">
              {previewUrl ? (
                <div className="relative shadow-lg rounded-lg overflow-hidden group">
                  <img
                    src={imageUrl}
                    alt="base"
                    className="max-h-[500px] object-contain"
                  />
                  <img
                    src={previewUrl}
                    alt="warp"
                    className="absolute inset-0 w-full h-full object-contain"
                  />
                </div>
              ) : (
                <p className="text-gray-400 text-sm">
                  Upload a design and set points to see result
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="w-full lg:w-80 flex flex-col space-y-6 overflow-y-auto">
            {/* Define Mockup Card */}
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
              <h3 className="font-bold text-gray-900 flex items-center mb-4">
                <Layers className="w-5 h-5 mr-2 text-primary" />
                Mockup Base
              </h3>

              {!mockupId ? (
                <label className="block w-full border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:bg-gray-50 cursor-pointer transition-colors">
                  <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                  <span className="text-sm font-medium text-gray-600">
                    Upload Base Image
                  </span>
                  <input
                    type="file"
                    className="hidden"
                    onChange={handleFileUpload}
                    accept="image/*"
                  />
                </label>
              ) : (
                <div className="space-y-4">
                  <div className="text-sm text-gray-600 truncate">
                    Using:{" "}
                    <span className="font-medium text-gray-900">
                      {mockupName}
                    </span>
                  </div>
                  <button
                    onClick={handleSaveConfig}
                    className="w-full bg-gray-900 hover:bg-black text-white py-2.5 rounded-lg text-sm font-medium flex items-center justify-center transition-colors"
                  >
                    <Save className="w-4 h-4 mr-2" />
                    Save Coordinates
                  </button>
                </div>
              )}
            </div>

            {/* Generate Card */}
            <div
              className={clsx(
                "bg-white p-6 rounded-xl shadow-sm border border-gray-100 transition-opacity",
                !mockupId && "opacity-50 pointer-events-none"
              )}
            >
              <h3 className="font-bold text-gray-900 flex items-center mb-4">
                <Play className="w-5 h-5 mr-2 text-secondary" />
                Design & Generate
              </h3>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Upload Designs ({designs.length})
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="file"
                      multiple
                      className="block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                      onChange={handleDesignUpload}
                      accept="image/*"
                    />
                  </div>
                  {designs.length > 0 && (
                    <button
                      onClick={() => updatePreview(points)}
                      className="mt-2 text-xs text-primary underline flex items-center"
                    >
                      <RefreshCw className="w-3 h-3 mr-1" /> Refresh Preview
                      (First Design)
                    </button>
                  )}
                </div>

                <button
                  onClick={handleGenerate}
                  disabled={generating || designs.length === 0}
                  className="w-full bg-gradient-to-r from-primary to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white py-3 rounded-lg text-sm font-bold flex items-center justify-center transition-all disabled:opacity-70 shadow-md"
                >
                  {generating
                    ? "Processing..."
                    : `Generate ${
                        designs.length > 1 ? "All " + designs.length : "Mockup"
                      }`}
                </button>
              </div>
            </div>

            {/* Instructions */}
            <div className="bg-blue-50 p-4 rounded-xl border border-blue-100">
              <h4 className="font-bold text-blue-900 text-sm mb-2">
                How to use
              </h4>
              <ul className="text-xs text-blue-800 space-y-1.5 list-disc pl-4">
                <li>Upload a generic mockup image.</li>
                <li>Drag the 4 dots to defined the print area.</li>
                <li>
                  Upload a design to see a <strong>Live Preview</strong>.
                </li>
                <li>Use "Side-by-Side" to compare.</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Editor;
