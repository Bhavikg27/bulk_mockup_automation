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

export const generateBulkMockups = async (mockupId, designFiles, namingTemplate = null) => {
    const formData = new FormData();
    formData.append('mockup_id', mockupId);
    // Append each file with same key 'designs'
    for (let i = 0; i < designFiles.length; i++) {
        formData.append('designs', designFiles[i]);
    }
    // Add naming template if provided
    if (namingTemplate) {
        formData.append('naming_template', namingTemplate);
    }
    
    // Increase timeout for bulk ops
    const response = await api.post('/generate-bulk', formData, {
        timeout: 60000 
    });
    return response.data;
};

export default api;
