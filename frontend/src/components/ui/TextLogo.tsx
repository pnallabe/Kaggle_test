import React from 'react';

interface TextLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'light' | 'dark' | 'gradient';
}

const TextLogo: React.FC<TextLogoProps> = ({ 
  className = '', 
  size = 'md', 
  variant = 'gradient' 
}) => {
  const sizeClasses = {
    sm: 'text-lg',
    md: 'text-xl',
    lg: 'text-2xl',
    xl: 'text-3xl'
  };

  const getTextStyles = () => {
    switch (variant) {
      case 'light':
        return 'text-white';
      case 'dark':
        return 'text-gray-900';
      case 'gradient':
      default:
        return 'gradient-text';
    }
  };

  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      {/* Stylized S mark */}
      <div className="relative">
        <svg
          width="32"
          height="32"
          viewBox="0 0 32 32"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Background circle */}
          <circle
            cx="16"
            cy="16"
            r="14"
            fill="url(#textLogoGradient)"
            stroke="url(#textLogoGradient)"
            strokeWidth="2"
          />
          
          {/* Modern S */}
          <path
            d="M20 11c0 1.5-1.2 2.7-2.7 2.7h-1.6c-.4 0-.7.3-.7.7s.3.7.7.7h2.6c1.1 0 2 .9 2 2s-.9 2-2 2h-5.6c-1.5 0-2.7-1.2-2.7-2.7V15h2v1.3c0 .4.3.7.7.7h1.6c.4 0 .7-.3.7-.7s-.3-.7-.7-.7h-2.6c-1.1 0-2-.9-2-2s.9-2 2-2h5.6c1.5 0 2.7 1.2 2.7 2.7V13h-2v-2z"
            fill="white"
          />
          
          <defs>
            <linearGradient id="textLogoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8B5CF6" />
              <stop offset="100%" stopColor="#A855F7" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      {/* Brand name */}
      <span className={`font-bold ${sizeClasses[size]} ${getTextStyles()}`}>
        Suchana.ai
      </span>
    </div>
  );
};

export default TextLogo;