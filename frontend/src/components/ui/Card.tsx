import { FC, ReactNode } from 'react';
import { cn } from '@utils/cn';

interface CardProps {
  className?: string;
  children: ReactNode;
}

export const Card: FC<CardProps> = ({ className, children }) => (
  <div className={cn('rounded-lg border border-border bg-card text-card-foreground shadow-sm', className)}>
    {children}
  </div>
);

export const CardHeader: FC<CardProps> = ({ className, children }) => (
  <div className={cn('flex flex-col space-y-1.5 p-6 border-b border-border', className)}>
    {children}
  </div>
);

export const CardTitle: FC<{ className?: string; children: ReactNode }> = ({
  className,
  children,
}) => (
  <h2 className={cn('text-2xl font-semibold leading-none tracking-tight', className)}>
    {children}
  </h2>
);

export const CardDescription: FC<{ className?: string; children: ReactNode }> = ({
  className,
  children,
}) => <p className={cn('text-sm text-muted-foreground', className)}>{children}</p>;

export const CardContent: FC<CardProps> = ({ className, children }) => (
  <div className={cn('p-6 pt-0', className)}>{children}</div>
);

export const CardFooter: FC<CardProps> = ({ className, children }) => (
  <div className={cn('flex items-center p-6 pt-0', className)}>{children}</div>
);
