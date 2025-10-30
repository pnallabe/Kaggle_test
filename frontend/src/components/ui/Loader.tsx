import { FC } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '@utils/cn';

interface LoaderProps {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

const Loader: FC<LoaderProps> = ({ className, size = 'md' }) => {
  const sizes = {
    sm: 'h-4 w-4',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  };

  return (
    <Loader2 className={cn('animate-spin text-primary', sizes[size], className)} />
  );
};

export default Loader;
