import { useState } from 'react';
import { useAppSelector } from '@hooks/index';

export default function APITest() {
  const auth = useAppSelector((state) => state.auth);
  const [testResult, setTestResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const testCreateProject = async () => {
    if (!auth.token) {
      setTestResult('❌ No auth token found');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch('http://localhost:8080/api/v1/projects', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${auth.token}`,
        },
        body: JSON.stringify({
          name: `Test Project ${new Date().getTime()}`,
          description: 'API Test',
          data_sources: [],
        }),
      });

      const data = await response.json();
      
      if (response.ok) {
        setTestResult(`✅ Success!\n${JSON.stringify(data, null, 2)}`);
      } else {
        setTestResult(`❌ Error: ${response.status}\n${JSON.stringify(data, null, 2)}`);
      }
    } catch (error: any) {
      setTestResult(`❌ Exception: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 bg-slate-900 text-white rounded-lg max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">🧪 API Test</h2>
      
      <div className="mb-4">
        <p className="text-sm text-slate-400 mb-2">Auth Token Status:</p>
        <p className="text-xs font-mono bg-slate-800 p-3 rounded break-all">
          {auth.token ? `✅ Token exists (${auth.token.substring(0, 50)}...)` : '❌ No token'}
        </p>
      </div>

      <button
        onClick={testCreateProject}
        disabled={loading || !auth.token}
        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded mb-4"
      >
        {loading ? 'Testing...' : 'Test Create Project'}
      </button>

      <div className="bg-slate-800 p-4 rounded">
        <p className="text-sm text-slate-400 mb-2">Result:</p>
        <pre className="text-xs whitespace-pre-wrap break-all max-h-96 overflow-y-auto">
          {testResult || 'Click button to test...'}
        </pre>
      </div>
    </div>
  );
}
