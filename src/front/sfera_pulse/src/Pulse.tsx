import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { commitsService, type SimpleCommit } from './api/commits';
import ProjectRepositorySelector from './components/ProjectRepositorySelector';
import Navbar from './components/Navbar';
import './Pulse.css';

interface PulseProps {
  onLogout: () => void;
}

export default function Pulse({ onLogout }: PulseProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [commits, setCommits] = useState<SimpleCommit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [limit, setLimit] = useState(parseInt(searchParams.get('limit') || '10'));
  const [selectedProject, setSelectedProject] = useState<string>(searchParams.get('project') || '');
  const [selectedRepository, setSelectedRepository] = useState<string>(searchParams.get('repository') || '');


  // Handle URL parameter changes
  useEffect(() => {
    const urlLimit = searchParams.get('limit');
    const urlProject = searchParams.get('project');
    const urlRepository = searchParams.get('repository');

    if (urlLimit && parseInt(urlLimit) !== limit) {
      setLimit(parseInt(urlLimit));
    }
    if (urlProject && urlProject !== selectedProject) {
      setSelectedProject(urlProject);
    }
    if (urlRepository && urlRepository !== selectedRepository) {
      setSelectedRepository(urlRepository);
    }
  }, [searchParams]);


  useEffect(() => {
    if (selectedProject && selectedRepository) {
      fetchCommits();
    }
  }, [limit, selectedProject, selectedRepository]);

  // Update URL parameters when state changes
  useEffect(() => {
    updateUrlParams({
      limit,
      project: selectedProject,
      repository: selectedRepository
    });
  }, [limit, selectedProject, selectedRepository]);


  const fetchCommits = async () => {
    if (!selectedProject || !selectedRepository) return;

    setLoading(true);
    setError('');

    try {
      const response = await commitsService.getLastCommits(selectedProject, selectedRepository, limit);
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

  const updateUrlParams = (updates: { limit?: number; project?: string; repository?: string }) => {
    const newParams = new URLSearchParams(searchParams);

    if (updates.limit !== undefined) {
      newParams.set('limit', updates.limit.toString());
    }
    if (updates.project !== undefined) {
      if (updates.project) {
        newParams.set('project', updates.project);
      } else {
        newParams.delete('project');
      }
    }
    if (updates.repository !== undefined) {
      if (updates.repository) {
        newParams.set('repository', updates.repository);
      } else {
        newParams.delete('repository');
      }
    }

    setSearchParams(newParams);
  };

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit);
  };

  const handleProjectChange = (newProject: string) => {
    setSelectedProject(newProject);
    setSelectedRepository(''); // Reset repository selection when project changes
  };

  const handleRepositoryChange = (newRepository: string) => {
    setSelectedRepository(newRepository);
  };

  return (
    <div>
    <Navbar onLogout={onLogout} />
    <div className="home">

      <ProjectRepositorySelector
        selectedProject={selectedProject}
        selectedRepository={selectedRepository}
        limit={limit}
        loading={loading}
        onProjectChange={handleProjectChange}
        onRepositoryChange={handleRepositoryChange}
        onLimitChange={handleLimitChange}
        onError={setError}
        showCommitsLimit={true}
      />

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

      {!loading && !error && selectedProject && selectedRepository && commits.length > 0 && (
        <>
          <h3>Commit Timeline by User ({commits.length} commits)</h3>
          {(() => {
            // Group commits by author
            const commitsByUser = commits.reduce((acc, commit) => {
              if (!acc[commit.author]) {
                acc[commit.author] = [];
              }
              acc[commit.author].push(commit);
              return acc;
            }, {} as Record<string, typeof commits>);

            // Calculate date range from all commits
            const allDates = commits.map(commit => new Date(commit.created_at));
            const minDate = new Date(Math.min(...allDates.map(date => date.getTime())));
            const maxDate = new Date(Math.max(...allDates.map(date => date.getTime())));
            const totalTimeRange = maxDate.getTime() - minDate.getTime();

            const users = Object.keys(commitsByUser);
            const colors = ['#00d4ff', '#0099cc', '#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#feca57', '#ff9ff3'];

            return (
              <div className="users-timeline">
                {users.map((user, userIndex) => {
                  const userCommits = commitsByUser[user];
                  const userColor = colors[userIndex % colors.length];

                  return (
                    <div key={user} className="user-timeline-row">
                      <div className="user-info">
                        <div className="user-avatar" style={{ backgroundColor: userColor }}>
                          {user.charAt(0).toUpperCase()}
                        </div>
                        <div className="user-details">
                          <div className="user-name">{user}</div>
                          <div className="user-stats">{userCommits.length} commits</div>
                        </div>
                      </div>
                      <div className="user-timeline-container">
                        <div className="timeline-line"></div>
                        {userCommits.map((commit, commitIndex) => {
                          const commitDate = new Date(commit.created_at);
                          // Calculate position based on actual date range
                          const timeFromStart = commitDate.getTime() - minDate.getTime();
                          const position = totalTimeRange > 0 ? (timeFromStart / totalTimeRange) * 100 : 50;

                          return (
                            <div
                              key={`${user}-${commitIndex}`}
                              className="timeline-impulse"
                              style={{
                                left: `${Math.max(0, Math.min(100, position))}%`,
                                '--user-color': userColor
                              } as React.CSSProperties}
                              title={`${commit.author} - ${formatDate(commit.created_at)}`}
                            >
                              <div className="impulse-dot" style={{ backgroundColor: userColor }}></div>
                              <div className="impulse-info">
                                <div className="impulse-author">{commit.author}</div>
                                <div className="impulse-date">{formatDate(commit.created_at)}</div>
                                <div className="impulse-message">{commit.message.split('\n')[0]}</div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })()}
          <div className="timeline-legend">
            <div className="legend-item">
              <span className="legend-label">
                {(() => {
                  const allDates = commits.map(commit => new Date(commit.created_at));
                  const minDate = new Date(Math.min(...allDates.map(date => date.getTime())));
                  return minDate.toLocaleDateString();
                })()}
              </span>
            </div>
            <div className="legend-item">
              <span className="legend-label">
                {(() => {
                  const allDates = commits.map(commit => new Date(commit.created_at));
                  const minDate = new Date(Math.min(...allDates.map(date => date.getTime())));
                  const maxDate = new Date(Math.max(...allDates.map(date => date.getTime())));
                  const midDate = new Date((minDate.getTime() + maxDate.getTime()) / 2);
                  return midDate.toLocaleDateString();
                })()}
              </span>
            </div>
            <div className="legend-item">
              <span className="legend-label">
                {(() => {
                  const allDates = commits.map(commit => new Date(commit.created_at));
                  const maxDate = new Date(Math.max(...allDates.map(date => date.getTime())));
                  return maxDate.toLocaleDateString();
                })()}
              </span>
            </div>
          </div>
        </>
      )}

      {!loading && !error && selectedProject && selectedRepository && (
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
    </div>
  );
}
