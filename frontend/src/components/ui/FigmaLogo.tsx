import React from 'react';

interface FigmaLogoProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  showText?: boolean;
}

const FigmaLogo: React.FC<FigmaLogoProps> = ({ 
  className = '', 
  size = 'md',
  showText = true
}) => {
  const dimensions = {
    sm: { width: 24, height: 24, text: 'text-lg' },
    md: { width: 32, height: 32, text: 'text-xl' },
    lg: { width: 40, height: 40, text: 'text-2xl' }
  };

  const { width, height, text } = dimensions[size];

  return (
    <div className={`flex items-center space-x-3 ${className}`}>
      {/* Geometric Logo Mark */}
      <div className="relative">
        <svg
          width={width}
          height={height}
          viewBox="0 0 40 40"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Outer Ring */}
          <circle
            cx="20"
            cy="20"
            r="18"
            stroke="url(#figmaGradient)"
            strokeWidth="2"
            fill="none"
          />
          
          {/* Inner geometric pattern */}
          <path
            d="M20 8L28 16L20 24L12 16L20 8Z"
            fill="url(#figmaGradient)"
            opacity="0.8"
          />
          
          {/* Central dot */}
          <circle
            cx="20"
            cy="20"
            r="3"
            fill="url(#figmaGradient)"
          />
          
          {/* Corner accents */}
          <circle cx="12" cy="12" r="1.5" fill="url(#figmaGradient)" opacity="0.6" />
          <circle cx="28" cy="12" r="1.5" fill="url(#figmaGradient)" opacity="0.6" />
          <circle cx="12" cy="28" r="1.5" fill="url(#figmaGradient)" opacity="0.6" />
          <circle cx="28" cy="28" r="1.5" fill="url(#figmaGradient)" opacity="0.6" />
          
          <defs>
            <linearGradient id="figmaGradient" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#8B5CF6" />
              <stop offset="50%" stopColor="#A855F7" />
              <stop offset="100%" stopColor="#C084FC" />
            </linearGradient>
          </defs>
        </svg>
      </div>
      
      {/* Brand Text */}
      {showText && (
        <div className="flex flex-col">
          <span className={`font-bold gradient-text ${text}`}>
            Suchana.ai
          </span>
          <span className="text-xs text-muted-foreground -mt-1">
            AI Analytics
          </span>
        </div>
      )}
    </div>
  );
};

export default FigmaLogo;