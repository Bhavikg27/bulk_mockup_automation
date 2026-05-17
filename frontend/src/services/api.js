import axios from 'axios';

const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
});

export const getMockups = async () => {
    const response = await api.get('/mockups');
    return response.data;
};

export const uploadMockup = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await api.post('/upload-mockup', formData);
    return response.data;
};

export const saveConfig = async (config) => {
    const response = await api.post('/save-config', config);
    return response.data;
};

export const generateMockup = async (mockupId, designFile, namingTemplate = null) => {
    const formData = new FormData();
    formData.append('mockup_id', mockupId);
    formData.append('design', designFile);
    if (namingTemplate) {
        formData.append('naming_template', namingTemplate);
    }
    const response = await api.post('/generate', formData);
    return response.data;
};

export const getImageUrl = (path) => {
    return `${API_URL}${path}`;
}

export const getExportZipUrl = (jobId) => {
    return `${API_URL}/api/exports/${jobId}/download`;
};

export const getGeneratedImages = async () => {
    const response = await api.get('/generated-images');
    return response.data;
};

export const getPreview = async (mockupId, designFile, points) => {
    const formData = new FormData();
    formData.append('mockup_id', mockupId);
    formData.append('design', designFile);
    formData.append('points', JSON.stringify(points));

    // We expect a blob (image) back
    const response = await api.post('/preview', formData, {
        responseType: 'blob'
    });
    return URL.createObjectURL(response.data);
};

export const createMockupJob = async (mockupId, designFiles, namingTemplate = null, targetKb = 100) => {
    const formData = new FormData();
    formData.append('mockup_id', mockupId);
    formData.append('target_kb', String(targetKb));
    for (let i = 0; i < designFiles.length; i++) {
        formData.append('designs', designFiles[i]);
    }
    if (namingTemplate) {
        formData.append('naming_template', namingTemplate);
    }

    const response = await api.post('/api/jobs/mockup-batch', formData, { timeout: 300000 });
    return response.data;
};

export const createOptimizerJob = async (imageFiles, options = {}) => {
    const formData = new FormData();
    formData.append('target_kb', String(options.targetKb ?? 100));
    formData.append('quality', String(options.quality ?? 90));
    if (options.maxWidth) formData.append('max_width', String(options.maxWidth));
    if (options.maxHeight) formData.append('max_height', String(options.maxHeight));
    for (let i = 0; i < imageFiles.length; i++) {
        formData.append('images', imageFiles[i]);
    }

    const response = await api.post('/api/jobs/optimize-batch', formData, { timeout: 300000 });
    return response.data;
};

export const generateBulkMockups = createMockupJob;

export const getJob = async (jobId) => {
    const response = await api.get(`/api/jobs/${jobId}`);
    return response.data;
};

export const getJobs = async (limit = 20) => {
    const response = await api.get('/api/jobs', { params: { limit } });
    return response.data;
};

export const cancelJob = async (jobId) => {
    const response = await api.post(`/api/jobs/${jobId}/cancel`);
    return response.data;
};

export const subscribeToJob = (jobId, onMessage, onError) => {
    const source = new EventSource(`${API_URL}/api/jobs/${jobId}/events`);
    source.onmessage = (event) => {
        onMessage(JSON.parse(event.data));
    };
    source.onerror = (event) => {
        if (onError) onError(event);
    };
    return source;
};

export default api;
