import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppDispatch, useAppSelector } from '@hooks/index';
import { logoutUser, updateUserProfile, clearError } from '@store/slices/authSlice';
import Button from '@components/ui/Button';
import Input from '@components/ui/Input';
import Alert from '@components/ui/Alert';
import Loader from '@components/ui/Loader';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@components/ui/Card';

export default function UserProfile() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { user, isLoading, error, isAuthenticated } = useAppSelector((state) => state.auth);

  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    bio: '',
    organization: '',
    phone: '',
  });

  // Load profile on mount
  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (user) {
      setFormData({
        name: user.name || '',
        bio: user.profile?.bio || '',
        organization: user.profile?.organization || '',
        phone: user.profile?.phone || '',
      });
    }
  }, [isAuthenticated, user, navigate]);

  if (!isAuthenticated || !user) {
    return null;
  }

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSave = async () => {
    dispatch(clearError());
    await dispatch(
      updateUserProfile({
        name: formData.name,
        profile: {
          bio: formData.bio,
          organization: formData.organization,
          phone: formData.phone,
        },
      })
    );
    setIsEditing(false);
  };

  const handleLogout = () => {
    dispatch(logoutUser());
    navigate('/login');
  };

  const storagePercentage = user.storage?.percentage_used || 0;
  const storageStatus =
    storagePercentage > 90 ? 'destructive' : storagePercentage > 70 ? 'warning' : 'default';

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-slate-100">Account Settings</h1>
        <p className="text-slate-400 mt-1">Manage your profile and preferences</p>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          {error}
        </Alert>
      )}

      {/* Profile Card */}
      <Card className="border-slate-700 bg-slate-800">
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>Your account details</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Display Mode */}
          {!isEditing && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium text-slate-300">Name</p>
                <p className="text-slate-200">{user.name}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-slate-300">Email</p>
                <p className="text-slate-200">{user.email}</p>
              </div>

              <div>
                <p className="text-sm font-medium text-slate-300">Member Since</p>
                <p className="text-slate-200">
                  {new Date(user.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </p>
              </div>

              {user.profile?.bio && (
                <div>
                  <p className="text-sm font-medium text-slate-300">Bio</p>
                  <p className="text-slate-200">{user.profile.bio}</p>
                </div>
              )}

              {user.profile?.organization && (
                <div>
                  <p className="text-sm font-medium text-slate-300">Organization</p>
                  <p className="text-slate-200">{user.profile.organization}</p>
                </div>
              )}

              <Button
                onClick={() => setIsEditing(true)}
                variant="secondary"
                disabled={isLoading}
              >
                Edit Profile
              </Button>
            </div>
          )}

          {/* Edit Mode */}
          {isEditing && (
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium text-slate-300 mb-2">Name</p>
                <Input
                  name="name"
                  value={formData.name}
                  onChange={handleChange}
                  disabled={isLoading}
                />
              </div>

              <div>
                <p className="text-sm font-medium text-slate-300 mb-2">Bio</p>
                <Input
                  name="bio"
                  placeholder="Tell us about yourself"
                  value={formData.bio}
                  onChange={handleChange}
                  disabled={isLoading}
                />
              </div>

              <div>
                <p className="text-sm font-medium text-slate-300 mb-2">Organization</p>
                <Input
                  name="organization"
                  placeholder="Your organization"
                  value={formData.organization}
                  onChange={handleChange}
                  disabled={isLoading}
                />
              </div>

              <div>
                <p className="text-sm font-medium text-slate-300 mb-2">Phone</p>
                <Input
                  name="phone"
                  type="tel"
                  placeholder="Your phone number"
                  value={formData.phone}
                  onChange={handleChange}
                  disabled={isLoading}
                />
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={handleSave}
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader className="w-4 h-4 mr-2" />
                      Saving...
                    </>
                  ) : (
                    'Save Changes'
                  )}
                </Button>
                <Button
                  onClick={() => setIsEditing(false)}
                  variant="outline"
                  disabled={isLoading}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Storage Card */}
      <Card className="border-slate-700 bg-slate-800">
        <CardHeader>
          <CardTitle>Storage</CardTitle>
          <CardDescription>Your data usage</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <div className="flex justify-between items-center mb-2">
                <p className="text-sm font-medium text-slate-300">Storage Used</p>
                <p className="text-sm text-slate-400">
                  {user.storage?.used_mb || 0} MB / {user.storage?.max_mb || 100} MB
                </p>
              </div>
              <div className="w-full bg-slate-700 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all ${
                    storageStatus === 'destructive'
                      ? 'bg-red-500'
                      : storageStatus === 'warning'
                      ? 'bg-yellow-500'
                      : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(storagePercentage, 100)}%` }}
                ></div>
              </div>
              <p className="text-xs text-slate-400 mt-2">
                {storagePercentage.toFixed(1)}% used
              </p>
            </div>

            {storagePercentage > 90 && (
              <Alert variant="destructive" className="text-sm">
                You are running out of storage. Please delete some datasets or contact support.
              </Alert>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Session Card */}
      <Card className="border-slate-700 bg-slate-800">
        <CardHeader>
          <CardTitle>Session</CardTitle>
          <CardDescription>Manage your account access</CardDescription>
        </CardHeader>
        <CardContent>
          <Button
            onClick={handleLogout}
            variant="destructive"
          >
            Sign Out
          </Button>
          <p className="text-xs text-slate-400 mt-4">
            You will be logged out from this device. Other sessions will remain active.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
