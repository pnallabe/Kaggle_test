import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@hooks/index';
import { loginUser, clearError } from '@store/slices/authSlice';
import Button from '@components/ui/Button';
import Input from '@components/ui/Input';
import Alert from '@components/ui/Alert';
import Loader from '@components/ui/Loader';

export default function Login() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { isLoading, error, isAuthenticated } = useAppSelector((state) => state.auth);

  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });

  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate('/');
    return null;
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(clearError());

    // Validation
    if (!formData.email || !formData.password) {
      return;
    }

    // Dispatch login
    const result = await dispatch(
      loginUser({
        email: formData.email.toLowerCase(),
        password: formData.password,
      })
    );

    // Redirect on success
    if (result.type === loginUser.fulfilled.type) {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">AI Data Analyst</h1>
          <p className="text-slate-400">Welcome back</p>
        </div>

        {/* Card */}
        <div className="bg-slate-800 rounded-lg border border-slate-700 p-8">
          {/* Error Alert */}
          {error && (
            <Alert variant="destructive" className="mb-6">
              {error}
            </Alert>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Email */}
            <Input
              type="email"
              name="email"
              placeholder="Email address"
              value={formData.email}
              onChange={handleChange}
              disabled={isLoading}
              className="text-base"
            />

            {/* Password */}
            <Input
              type="password"
              name="password"
              placeholder="Password"
              value={formData.password}
              onChange={handleChange}
              disabled={isLoading}
              className="text-base"
            />

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={isLoading || !formData.email || !formData.password}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader className="w-4 h-4 mr-2" />
                  Signing in...
                </>
              ) : (
                'Sign in'
              )}
            </Button>
          </form>

          {/* Divider */}
          <div className="relative my-8">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-700"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-slate-800 text-slate-400">
                Don't have an account?
              </span>
            </div>
          </div>

          {/* Register Link */}
          <Link to="/register">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={isLoading}
            >
              Create account
            </Button>
          </Link>
        </div>

        {/* Demo Credentials */}
        <div className="mt-8 p-4 bg-slate-800 rounded-lg border border-slate-700">
          <p className="text-xs font-semibold text-slate-300 mb-2">Demo Account:</p>
          <p className="text-xs text-slate-400">
            Email: <span className="text-slate-200">demo@example.com</span>
          </p>
          <p className="text-xs text-slate-400">
            Password: <span className="text-slate-200">demo123</span>
          </p>
          <p className="text-xs text-slate-500 mt-2">
            Or register a new account to get started
          </p>
        </div>
      </div>
    </div>
  );
}
