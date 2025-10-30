import { FC, useState, useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '@hooks';
import { submitJob, pollJobCompletion } from '@store/slices/jobSlice';
import { fetchDatasets } from '@store/slices/datasetSlice';
import { Card, CardHeader, CardTitle, CardContent, Button, Input, Textarea, Loader, Alert, Badge } from '@components/ui';
import { Send, Play } from 'lucide-react';

const QueryConsole: FC = () => {
  const dispatch = useAppDispatch();
  const { datasets } = useAppSelector((state) => state.datasets);
  const { jobs, currentJobId, polling } = useAppSelector((state) => state.jobs);
  const { currentProject } = useAppSelector((state) => state.projects);

  const [query, setQuery] = useState('');
  const [selectedDataset, setSelectedDataset] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (currentProject) {
      dispatch(fetchDatasets(currentProject.id) as any);
    }
  }, [currentProject, dispatch]);

  const handleSubmitQuery = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    if (!selectedDataset) {
      setError('Please select a dataset');
      return;
    }

    setError('');

    try {
      const result = await dispatch(
        submitJob({
          query,
          dataset_id: selectedDataset,
        }) as any
      );

      if (result.payload?.job_id) {
        // Start polling for results
        dispatch(pollJobCompletion(result.payload.job_id) as any);
      }
    } catch (err) {
      setError('Failed to submit query');
    }
  };

  const currentJob = currentJobId ? jobs[currentJobId] : null;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground">Query Console</h1>
        <p className="text-muted-foreground">Write natural language queries to analyze your data</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Query Input */}
        <div className="lg:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>New Query</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Dataset</label>
                <select
                  value={selectedDataset}
                  onChange={(e) => setSelectedDataset(e.target.value)}
                  className="w-full px-3 py-2 rounded-md border border-input bg-background text-foreground"
                >
                  <option value="">Select a dataset...</option>
                  {datasets.map((ds) => (
                    <option key={ds.id} value={ds.id}>
                      {ds.name} ({ds.row_count} rows)
                    </option>
                  ))}
                </select>
              </div>

              <Textarea
                label="Query"
                placeholder="E.g., Show me the revenue breakdown by product category for last quarter"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={6}
              />

              {error && <Alert variant="destructive">{error}</Alert>}

              <Button
                onClick={handleSubmitQuery}
                disabled={polling}
                className="w-full"
              >
                {polling ? (
                  <>
                    <Loader size="sm" className="mr-2" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Run Query
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Query Status</CardTitle>
            </CardHeader>
            <CardContent>
              {currentJob ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Job ID</p>
                    <p className="font-mono text-xs text-foreground">{currentJob.job_id}</p>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Status</p>
                    <Badge
                      variant={
                        currentJob.status === 'completed'
                          ? 'success'
                          : currentJob.status === 'failed'
                            ? 'destructive'
                            : 'default'
                      }
                    >
                      {currentJob.status.toUpperCase()}
                    </Badge>
                  </div>

                  <div>
                    <p className="text-sm text-muted-foreground mb-2">Progress</p>
                    <div className="w-full bg-muted rounded-full h-2">
                      <div
                        className="bg-primary h-2 rounded-full transition-all"
                        style={{ width: `${currentJob.progress || 0}%` }}
                      />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{currentJob.progress || 0}%</p>
                  </div>

                  {currentJob.results && (
                    <div className="pt-4 border-t border-border">
                      <p className="text-sm font-medium text-foreground mb-2">Insights</p>
                      <ul className="space-y-2 text-sm text-foreground">
                        {currentJob.results.insights.slice(0, 3).map((insight, i) => (
                          <li key={i} className="flex gap-2">
                            <span className="text-primary">•</span>
                            <span>{insight}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">Submit a query to see results</p>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default QueryConsole;
