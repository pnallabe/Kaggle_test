import { FC, ReactNode } from 'react';
import { cn } from '@utils/cn';

interface AlertProps {
  className?: string;
  children: ReactNode;
  variant?: 'default' | 'destructive' | 'success' | 'warning';
}

const Alert: FC<AlertProps> = ({ className, children, variant = 'default' }) => {
  const variants = {
    default: 'bg-accent text-accent-foreground border-accent/50',
    destructive: 'bg-destructive/10 text-destructive border-destructive/50',
    success: 'bg-green-100 text-green-900 border-green-500/50 dark:bg-green-900/20 dark:text-green-400',
    warning: 'bg-yellow-100 text-yellow-900 border-yellow-500/50 dark:bg-yellow-900/20 dark:text-yellow-400',
  };

  return (
    <div
      className={cn(
        'rounded-lg border p-4',
        variants[variant],
        className
      )}
      role="alert"
    >
      {children}
    </div>
  );
};

export default Alert;
