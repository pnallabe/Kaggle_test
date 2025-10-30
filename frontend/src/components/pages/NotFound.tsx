import { FC } from 'react';
import { Link } from 'react-router-dom';
import Button from '@components/ui/Button';

const NotFound: FC = () => {
  return (
    <div className="flex items-center justify-center min-h-screen bg-background">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-foreground mb-4">404</h1>
        <p className="text-xl text-muted-foreground mb-8">Page not found</p>
        <Link to="/">
          <Button>Go back to Dashboard</Button>
        </Link>
      </div>
    </div>
  );
};

export default NotFound;
