export default function DebugPanel({ thinkChain, workerResults, visible }) {
  if (!visible) return null;
  return (
    <div className="w-80 border-l border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-4 overflow-y-auto text-xs">
      <h3 className="font-semibold text-gray-700 dark:text-gray-300 mb-3">Debug Trace</h3>
      {thinkChain.length > 0 && (
        <div className="mb-4">
          <h4 className="font-medium text-blue-600 dark:text-blue-400 mb-2">Supervisor Thinking</h4>
          {thinkChain.map((tc, i) => (
            <div key={i} className="mb-2 p-2 bg-white dark:bg-gray-800 rounded">
              <div className="text-gray-500">Round {tc.iteration}</div>
              <div className="text-gray-700 dark:text-gray-300 mt-1">{tc.think}</div>
              <div className="mt-1">
                <span className="bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded text-xs">
                  {tc.decision}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
      {workerResults.length > 0 && (
        <div>
          <h4 className="font-medium text-green-600 dark:text-green-400 mb-2">Worker Results</h4>
          {workerResults.map((w, i) => (
            <div key={i} className="mb-2 p-2 bg-white dark:bg-gray-800 rounded">
              <span className={w.status === 'success' ? 'text-green-600' : 'text-red-500'}>
                {w.status === 'success' ? 'OK' : 'ERR'}
              </span>
              {' '}
              <span className="font-medium">{w.worker}</span>
              <span className="text-gray-400 ml-1">({w.elapsed_ms}ms)</span>
            </div>
          ))}
        </div>
      )}
      {thinkChain.length === 0 && workerResults.length === 0 && (
        <div className="text-gray-400 italic">No debug data yet.</div>
      )}
    </div>
  );
}
