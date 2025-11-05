import React from 'react';

interface LogoProps {
  className?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'light' | 'dark' | 'gradient';
}

const Logo: React.FC<LogoProps> = ({ 
  className = '', 
  size = 'md', 
  variant = 'gradient' 
}) => {
  const sizeClasses = {
    xs: 'w-6 h-6',
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16'
  };

  const iconSizes = {
    xs: 'w-4 h-4',
    sm: 'w-5 h-5',
    md: 'w-6 h-6',
    lg: 'w-7 h-7',
    xl: 'w-9 h-9'
  };

  const getLogoStyles = () => {
    switch (variant) {
      case 'light':
        return 'bg-white text-primary';
      case 'dark':
        return 'bg-gray-900 text-white';
      case 'gradient':
      default:
        return 'bg-gradient-primary text-white';
    }
  };

  return (
    <div className={`${sizeClasses[size]} ${getLogoStyles()} rounded-2xl flex items-center justify-center shadow-lg ${className}`}>
      <svg
        className={iconSizes[size]}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Modern S lettermark with geometric design */}
        <path
          d="M16 2C8.268 2 2 8.268 2 16s6.268 14 14 14 14-6.268 14-14S23.732 2 16 2z"
          fill="url(#logoGradient)"
          fillOpacity="0.1"
        />
        
        {/* Main S Letter */}
        <path
          d="M21 12.5c0 2.485-2.015 4.5-4.5 4.5h-1c-.275 0-.5.225-.5.5s.225.5.5.5h3c.827 0 1.5.673 1.5 1.5s-.673 1.5-1.5 1.5h-6c-2.485 0-4.5-2.015-4.5-4.5V15h3v1.5c0 .827.673 1.5 1.5 1.5h1c.275 0 .5-.225.5-.5s-.225-.5-.5-.5h-3c-.827 0-1.5-.673-1.5-1.5s.673-1.5 1.5-1.5h6c2.485 0 4.5 2.015 4.5 4.5v1.5h-3V12.5z"
          fill="currentColor"
        />
        
        {/* Geometric accent elements */}
        <circle cx="24" cy="8" r="1.5" fill="currentColor" opacity="0.3" />
        <circle cx="8" cy="24" r="1.5" fill="currentColor" opacity="0.3" />
        <rect x="6" y="6" width="2" height="2" rx="1" fill="currentColor" opacity="0.4" />
        <rect x="24" y="24" width="2" height="2" rx="1" fill="currentColor" opacity="0.4" />
        
        {/* Connecting elements */}
        <path
          d="M6 26L9 23M23 9L26 6"
          stroke="currentColor"
          strokeWidth="1"
          strokeLinecap="round"
          opacity="0.25"
        />
        
        <defs>
          <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8B5CF6" />
            <stop offset="50%" stopColor="#A855F7" />
            <stop offset="100%" stopColor="#C084FC" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
};

export default Logo;