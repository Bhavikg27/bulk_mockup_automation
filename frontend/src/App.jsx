import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Editor from './pages/Editor';
import Gallery from './pages/Gallery';
import Optimizer from './pages/Optimizer';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="editor/new" element={<Editor />} />
          <Route path="editor/:id" element={<Editor />} />
          <Route path="optimizer" element={<Optimizer />} />
          <Route path="gallery" element={<Gallery />} />
          {/* Catch all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
