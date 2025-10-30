import { FC, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAppSelector, useAppDispatch } from '@hooks/index';
import { fetchProjects, createProject, setCurrentProject } from '@store/slices/projectSlice';
import { Card, CardHeader, CardTitle, CardContent, Skeleton, Modal, Input } from '@components/ui';
import Button from '@components/ui/Button';
import { TrendingUp, Database, Zap } from 'lucide-react';

interface CreateProjectForm {
  name: string;
  description: string;
}

const Dashboard: FC = () => {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const { projects, loading } = useAppSelector((state: any) => state.projects);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [formData, setFormData] = useState<CreateProjectForm>({
    name: '',
    description: '',
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (projects.length === 0) {
      dispatch(fetchProjects() as any);
    }
  }, [dispatch, projects.length]);

  const handleCreateProject = async () => {
    if (!formData.name.trim()) {
      alert('Project name is required');
      return;
    }

    setIsSubmitting(true);
    try {
      await dispatch(
        createProject({
          name: formData.name,
          description: formData.description,
          data_sources: [],
        }) as any
      );
      
      // Refresh projects list after creation
      await dispatch(fetchProjects() as any);
      
      setFormData({ name: '', description: '' });
      setIsModalOpen(false);
    } catch (error) {
      console.error('Failed to create project:', error);
      alert('Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleOpenProject = (project: any) => {
    dispatch(setCurrentProject(project));
    navigate('/query');
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="pt-6">
                <Skeleton className="h-12 w-full mb-2" />
                <Skeleton className="h-4 w-1/2" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Welcome back! Here's your analytics overview.</p>
        </div>
        <Button onClick={() => setIsModalOpen(true)}>+ New Project</Button>
      </div>

      {/* Create Project Modal */}
      <Modal
        isOpen={isModalOpen}
        title="Create New Project"
        description="Enter project details to get started"
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleCreateProject}
        submitLabel="Create"
        isSubmitting={isSubmitting}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Project Name *
            </label>
            <Input
              type="text"
              placeholder="Enter project name"
              value={formData.name}
              onChange={(e: any) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              disabled={isSubmitting}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground mb-2">
              Description
            </label>
            <textarea
              placeholder="Enter project description"
              value={formData.description}
              onChange={(e: any) =>
                setFormData((prev) => ({ ...prev, description: e.target.value }))
              }
              disabled={isSubmitting}
              className="w-full px-3 py-2 border border-input rounded-md text-foreground bg-background placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
              rows={4}
            />
          </div>
        </div>
      </Modal>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active Projects</p>
                <p className="text-2xl font-bold text-foreground">{projects.length}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-primary opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Data Sources</p>
                <p className="text-2xl font-bold text-foreground">
                  {new Set(projects.flatMap((p: any) => p.data_sources)).size}
                </p>
              </div>
              <Database className="h-8 w-8 text-primary opacity-20" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Last Updated</p>
                <p className="text-sm font-bold text-foreground">Today</p>
              </div>
              <Zap className="h-8 w-8 text-primary opacity-20" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Projects List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Projects</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {projects.map((project: any) => (
              <div
                key={project.id}
                className="flex items-start justify-between p-4 rounded-lg border border-border hover:bg-muted/50 transition-colors"
              >
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground">{project.name}</h3>
                  <p className="text-sm text-muted-foreground">{project.description}</p>
                  <div className="mt-2 flex gap-2">
                    {project.data_sources.map((source: any) => (
                      <span
                        key={source}
                        className="text-xs px-2 py-1 bg-muted text-muted-foreground rounded"
                      >
                        {source}
                      </span>
                    ))}
                  </div>
                </div>
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => handleOpenProject(project)}
                >
                  Explore
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
