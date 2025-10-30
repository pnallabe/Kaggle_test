import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAppDispatch } from '@hooks/useAppDispatch';
import { restoreAuth } from '@store/slices/authSlice';
import Layout from '@components/layout/Layout';
import { PrivateRoute } from '@components/PrivateRoute';
import Dashboard from '@components/pages/Dashboard';
import QueryConsole from '@components/pages/QueryConsole';
import DatasetManager from '@components/pages/DatasetManager';
import UserProfile from '@components/pages/UserProfile';
import APITest from '@components/pages/APITest';
import Login from '@components/pages/Login';
import Register from '@components/pages/Register';
import NotFound from '@components/pages/NotFound';

function App() {
  const dispatch = useAppDispatch();

  // Restore auth state from localStorage on app load
  useEffect(() => {
    dispatch(restoreAuth());
  }, [dispatch]);

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Protected Routes */}
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="query" element={<QueryConsole />} />
          <Route path="datasets" element={<DatasetManager />} />
          <Route path="profile" element={<UserProfile />} />
          <Route path="api-test" element={<APITest />} />
          <Route path="*" element={<NotFound />} />
        </Route>

        {/* Catch all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
