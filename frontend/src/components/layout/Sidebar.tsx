import { FC } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { BarChart3, Database, Settings, LogOut } from 'lucide-react';
import { cn } from '@utils/cn';
import { Project } from '@types/index';

interface SidebarProps {
  projects: Project[];
}

const Sidebar: FC<SidebarProps> = ({ projects }) => {
  const location = useLocation();

  const isActive = (path: string) => location.pathname === path;

  const navItems = [
    { path: '/', label: 'Dashboard', icon: BarChart3 },
    { path: '/query', label: 'Query Console', icon: BarChart3 },
    { path: '/datasets', label: 'Datasets', icon: Database },
  ];

  return (
    <aside className="w-64 border-r border-border bg-card p-4">
      <div className="mb-8">
        <h1 className="text-xl font-bold text-foreground">AI Data Analyst</h1>
        <p className="text-xs text-muted-foreground">Enterprise Analytics Platform</p>
      </div>

      {/* Navigation */}
      <nav className="space-y-2 mb-8">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 px-4 py-2 rounded-md transition-colors',
                isActive(item.path)
                  ? 'bg-primary text-primary-foreground'
                  : 'text-foreground hover:bg-muted'
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="text-sm font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Projects */}
      <div className="mb-8">
        <h2 className="mb-3 px-4 text-xs font-semibold text-muted-foreground uppercase">
          Projects
        </h2>
        <div className="space-y-1">
          {projects.map((project) => (
            <Link
              key={project.id}
              to={`/?project=${project.id}`}
              className="block px-4 py-2 text-sm rounded-md text-foreground hover:bg-muted transition-colors truncate"
              title={project.name}
            >
              {project.name}
            </Link>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div className="absolute bottom-4 left-4 right-4 space-y-2">
        <Link
          to="/settings"
          className="flex items-center gap-2 px-4 py-2 text-sm rounded-md text-foreground hover:bg-muted transition-colors"
        >
          <Settings className="h-4 w-4" />
          <span>Settings</span>
        </Link>
        <button className="w-full flex items-center gap-2 px-4 py-2 text-sm rounded-md text-foreground hover:bg-muted transition-colors">
          <LogOut className="h-4 w-4" />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;
