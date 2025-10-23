import { useState, useEffect } from 'react';
import { commitsService, type SimpleCommit } from './api/commits';
import './Home.css';

interface HomeProps {
  onLogout: () => void;
}

export default function Home({ onLogout }: HomeProps) {
  const [commits, setCommits] = useState<SimpleCommit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [limit, setLimit] = useState(10);

  const projectKey = 'team16';
  const repoName = 'base_repo';

  useEffect(() => {
    fetchCommits();
  }, [limit]);

  const fetchCommits = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await commitsService.getLastCommits(projectKey, repoName, limit);
      setCommits(response.commits || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch commits');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleString();
    } catch {
      return dateString;
    }
  };

  const formatMessage = (message: string) => {
    // Split by newlines and format each line
    return message.split('\n').map((line, index) => {
      // Handle bullet points and other formatting
      if (line.trim().startsWith('*')) {
        return (
          <div key={index} className="commit-bullet-point">
            {line}
          </div>
        );
      }
      // Handle empty lines
      if (line.trim() === '') {
        return <br key={index} />;
      }
      // Regular lines
      return (
        <div key={index} className="commit-line">
          {line}
        </div>
      );
    });
  };

  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLimit(parseInt(e.target.value));
  };

  return (
    <div className="home">
      <div className="home-header">
        <h1>Sfera Pulse Dashboard</h1>
        <div className="header-controls">
          <div className="limit-selector">
            <label htmlFor="limit">Show commits:</label>
            <select
              id="limit"
              value={limit}
              onChange={handleLimitChange}
              disabled={loading}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
            </select>
          </div>
          <button onClick={onLogout} className="logout-btn">
            Logout
          </button>
        </div>
      </div>

      <div className="project-info">
        <h2>Project: {projectKey} / {repoName}</h2>
      </div>

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Loading commits...</p>
        </div>
      )}

      {error && (
        <div className="error-message">
          <h3>Error</h3>
          <p>{error}</p>
          <button onClick={fetchCommits} className="retry-btn">
            Try Again
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="commits-section">
          <h3>Recent Commits ({commits.length})</h3>
          {commits.length === 0 ? (
            <div className="no-commits">
              <p>No commits found for this repository.</p>
            </div>
          ) : (
            <div className="commits-list">
              {commits.map((commit, index) => (
                <div key={index} className="commit-item">
                  <div className="commit-header">
                    <div className="commit-title">
                      {formatMessage(commit.message)}
                    </div>
                    <span className="commit-author">by {commit.author}</span>
                  </div>
                  <div className="commit-meta">
                    <span className="commit-date">
                      {formatDate(commit.created_at)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
