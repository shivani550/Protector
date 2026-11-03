import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Navbar } from './components/Navbar';
import Login from './pages/Login';
import PatientsList from './pages/PatientsList';
import PatientDetail from './pages/PatientDetail';
import AdminDashboard from './pages/AdminDashboard';
import MagicUpload from './pages/MagicUpload';
import PatientSelfPortal from './pages/PatientSelfPortal';
import { User } from './types';
import { api } from './api';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,
      retry: 1,
    },
  },
});

function ProtectedRoute({ 
  user, 
  allowedRoles, 
  children 
}: { 
  user: User | null; 
  allowedRoles?: string[]; 
  children: React.ReactNode 
}) {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    if (user.role === 'patient') {
      return <Navigate to="/me" replace />;
    } else {
      return <Navigate to="/patients" replace />;
    }
  }

  return <>{children}</>;
}

import { Footer } from './components/Footer';

function MainLayout({ 
  user, 
  onLogout 
}: { 
  user: User | null; 
  onLogout: () => void 
}) {
  const location = useLocation();
  const isLoginPage = location.pathname === '/login';
  const isPublicPage = location.pathname.startsWith('/upload/') || isLoginPage;

  return (
    <div className="min-h-screen bg-cf-bg flex flex-col font-body text-cf-text antialiased selection:bg-cf-plum selection:text-cf-violet-900">
      {!isPublicPage && <Navbar user={user} onLogout={onLogout} />}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/upload/:token" element={<MagicUpload />} />

          <Route
            path="/patients"
            element={
              <ProtectedRoute user={user} allowedRoles={['admin', 'case_worker']}>
                <PatientsList />
              </ProtectedRoute>
            }
          />

          <Route
            path="/patients/:id"
            element={
              <ProtectedRoute user={user} allowedRoles={['admin', 'case_worker']}>
                <PatientDetail />
              </ProtectedRoute>
            }
          />

          <Route
            path="/admin"
            element={
              <ProtectedRoute user={user} allowedRoles={['admin']}>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />

          <Route
            path="/me"
            element={
              <ProtectedRoute user={user} allowedRoles={['patient', 'admin']}>
                <PatientSelfPortal />
              </ProtectedRoute>
            }
          />

          <Route
            path="/"
            element={
              user ? (
                user.role === 'patient' ? (
                  <Navigate to="/me" replace />
                ) : user.role === 'admin' ? (
                  <Navigate to="/admin" replace />
                ) : (
                  <Navigate to="/patients" replace />
                )
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {!isLoginPage && <Footer />}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState<User | null>(() => {
    const cached = localStorage.getItem('user');
    return cached ? JSON.parse(cached) : null;
  });

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.getMe().then(u => {
        setUser(u);
        localStorage.setItem('user', JSON.stringify(u));
      }).catch(() => {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        setUser(null);
      });
    }
  }, []);

  const handleLogout = () => {
    setUser(null);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <MainLayout user={user} onLogout={handleLogout} />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
