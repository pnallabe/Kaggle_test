import React, { FC } from 'react';
import { Bell, User, Moon, Sun } from 'lucide-react';
import Button from '@components/ui/Button';
import Logo from '@components/ui/Logo';
import { cn } from '@utils/cn';

const Navbar: FC = () => {
  const [isDark, setIsDark] = React.useState(false);

  const toggleDarkMode = () => {
    setIsDark(!isDark);
    document.documentElement.classList.toggle('dark');
  };

  return (
    <nav className="border-b border-border bg-card px-6 py-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Logo size="sm" variant="gradient" />
          <div>
            <h2 className="text-xl font-bold gradient-text">Suchana.ai</h2>
            <p className="text-xs text-muted-foreground">AI-Powered Analytics</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="relative p-2 text-muted-foreground hover:text-foreground transition-colors">
            <Bell className="h-5 w-5" />
            <span className="absolute top-1 right-1 h-2 w-2 bg-destructive rounded-full" />
          </button>

          <button
            onClick={toggleDarkMode}
            className="p-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            {isDark ? (
              <Sun className="h-5 w-5" />
            ) : (
              <Moon className="h-5 w-5" />
            )}
          </button>

          <button className="flex items-center gap-2 px-3 py-2 rounded-md hover:bg-muted transition-colors">
            <User className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm text-foreground">Profile</span>
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
