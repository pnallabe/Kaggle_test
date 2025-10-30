import { FC, useEffect, useState } from 'react';
import { useAppDispatch, useAppSelector } from '@hooks';
import { fetchDatasets, uploadDataset } from '@store/slices/datasetSlice';
import { Card, CardHeader, CardTitle, CardContent, Button, DataTable, Loader, Alert } from '@components/ui';
import { Upload, FileUp, Trash2 } from 'lucide-react';

const DatasetManager: FC = () => {
  const dispatch = useAppDispatch();
  const { currentProject } = useAppSelector((state) => state.projects);
  const { datasets, loading, uploadProgress } = useAppSelector((state) => state.datasets);
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    if (currentProject) {
      dispatch(fetchDatasets(currentProject.id) as any);
    }
  }, [currentProject, dispatch]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0] && currentProject) {
      const file = e.dataTransfer.files[0];
      dispatch(
        uploadDataset({
          projectId: currentProject.id,
          file,
        }) as any
      );
    }
  };

  const columns = [
    {
      key: 'name' as const,
      label: 'Name',
      sortable: true,
      width: '30%',
    },
    {
      key: 'type' as const,
      label: 'Type',
      sortable: true,
      width: '15%',
    },
    {
      key: 'row_count' as const,
      label: 'Rows',
      sortable: true,
      width: '15%',
      render: (value: unknown) => (value as number).toLocaleString(),
    },
    {
      key: 'size_bytes' as const,
      label: 'Size',
      sortable: true,
      width: '15%',
      render: (value: unknown) => {
        const bytes = value as number;
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
      },
    },
    {
      key: 'created_at' as const,
      label: 'Created',
      sortable: true,
      width: '15%',
      render: (value: unknown) => {
        const date = new Date(value as string);
        return date.toLocaleDateString();
      },
    },
    {
      key: 'id' as const,
      label: 'Actions',
      width: '10%',
      render: () => (
        <button className="text-destructive hover:text-destructive/80 transition-colors">
          <Trash2 className="h-4 w-4" />
        </button>
      ),
    },
  ];

  if (!currentProject) {
    return (
      <div className="p-6">
        <Alert variant="destructive">
          Please select a project first
        </Alert>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Dataset Manager</h1>
        <p className="text-muted-foreground">Upload and manage your data sources</p>
      </div>

      {/* Upload Area */}
      <Card>
        <CardContent className="pt-6">
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
              dragActive ? 'border-primary bg-primary/5' : 'border-border'
            }`}
          >
            <FileUp className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <h3 className="font-semibold text-foreground mb-1">Drop your files here</h3>
            <p className="text-sm text-muted-foreground mb-4">or click to browse</p>
            <Button variant="outline">
              <Upload className="h-4 w-4 mr-2" />
              Choose Files
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {Object.entries(uploadProgress).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Uploading...</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {Object.entries(uploadProgress).map(([fileName, progress]) => (
              <div key={fileName}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-foreground">{fileName}</span>
                  <span className="text-muted-foreground">{progress}%</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <div
                    className="bg-primary h-2 rounded-full transition-all"
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Datasets List */}
      <Card>
        <CardHeader>
          <CardTitle>Your Datasets</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader />
            </div>
          ) : datasets.length === 0 ? (
            <p className="text-muted-foreground text-center py-8">No datasets yet. Upload one to get started!</p>
          ) : (
            <DataTable data={datasets} columns={columns} />
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default DatasetManager;
