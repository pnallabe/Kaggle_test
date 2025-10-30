import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@hooks/index';
import { registerUser, clearError } from '@store/slices/authSlice';
import Button from '@components/ui/Button';
import Input from '@components/ui/Input';
import Alert from '@components/ui/Alert';
import Loader from '@components/ui/Loader';

export default function Register() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { isLoading, error, isAuthenticated } = useAppSelector((state) => state.auth);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});

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
    // Clear validation error for this field
    if (validationErrors[e.target.name]) {
      setValidationErrors({
        ...validationErrors,
        [e.target.name]: '',
      });
    }
  };

  const validate = () => {
    const errors: Record<string, string> = {};

    if (!formData.name.trim()) {
      errors.name = 'Name is required';
    }

    if (!formData.email.trim()) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email';
    }

    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 6) {
      errors.password = 'Password must be at least 6 characters';
    }

    if (!formData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    dispatch(clearError());

    if (!validate()) {
      return;
    }

    // Dispatch register
    const result = await dispatch(
      registerUser({
        email: formData.email.toLowerCase(),
        password: formData.password,
        name: formData.name,
      })
    );

    // Redirect on success
    if (result.type === registerUser.fulfilled.type) {
      navigate('/');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">AI Data Analyst</h1>
          <p className="text-slate-400">Create your account</p>
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
          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Name */}
            <div>
              <Input
                type="text"
                name="name"
                placeholder="Full name"
                value={formData.name}
                onChange={handleChange}
                disabled={isLoading}
                className={`text-base ${validationErrors.name ? 'border-red-500' : ''}`}
              />
              {validationErrors.name && (
                <p className="text-sm text-red-400 mt-2">{validationErrors.name}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <Input
                type="email"
                name="email"
                placeholder="Email address"
                value={formData.email}
                onChange={handleChange}
                disabled={isLoading}
                className={`text-base ${validationErrors.email ? 'border-red-500' : ''}`}
              />
              {validationErrors.email && (
                <p className="text-sm text-red-400 mt-2">{validationErrors.email}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <Input
                type="password"
                name="password"
                placeholder="Password (min. 6 characters)"
                value={formData.password}
                onChange={handleChange}
                disabled={isLoading}
                className={`text-base ${validationErrors.password ? 'border-red-500' : ''}`}
              />
              {validationErrors.password && (
                <p className="text-sm text-red-400 mt-2">{validationErrors.password}</p>
              )}
            </div>

            {/* Confirm Password */}
            <div>
              <Input
                type="password"
                name="confirmPassword"
                placeholder="Confirm password"
                value={formData.confirmPassword}
                onChange={handleChange}
                disabled={isLoading}
                className={`text-base ${validationErrors.confirmPassword ? 'border-red-500' : ''}`}
              />
              {validationErrors.confirmPassword && (
                <p className="text-sm text-red-400 mt-2">{validationErrors.confirmPassword}</p>
              )}
            </div>

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={isLoading}
              className="w-full mt-6"
            >
              {isLoading ? (
                <>
                  <Loader className="w-4 h-4 mr-2" />
                  Creating account...
                </>
              ) : (
                'Create account'
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
                Already have an account?
              </span>
            </div>
          </div>

          {/* Login Link */}
          <Link to="/login">
            <Button
              type="button"
              variant="outline"
              className="w-full"
              disabled={isLoading}
            >
              Sign in
            </Button>
          </Link>
        </div>

        {/* Info */}
        <div className="mt-8 text-center">
          <p className="text-xs text-slate-400">
            By signing up, you agree to our Terms of Service and Privacy Policy
          </p>
        </div>
      </div>
    </div>
  );
}
