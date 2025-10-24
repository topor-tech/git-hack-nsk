import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProjectRepositorySelector from './components/ProjectRepositorySelector';
import { dashboardService, type DashboardStats } from './api/dashboard';
import './Dashboard.css';

interface DashboardProps {
  onLogout: () => void;
}

export default function Dashboard({ onLogout }: DashboardProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedProject, setSelectedProject] = useState(searchParams.get('project') || '');
  const [selectedRepository, setSelectedRepository] = useState(searchParams.get('repository') || '');
  const [limit, setLimit] = useState(parseInt(searchParams.get('limit') || '500'));
  const [dashboardData, setDashboardData] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Update URL parameters when selections change
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedProject) params.set('project', selectedProject);
    if (selectedRepository) params.set('repository', selectedRepository);
    if (limit !== 500) params.set('limit', limit.toString());
    setSearchParams(params);
  }, [selectedProject, selectedRepository, limit, setSearchParams]);

  // Fetch dashboard data when project and repository are selected
  useEffect(() => {
    if (selectedProject && selectedRepository) {
      fetchDashboardData();
    }
  }, [selectedProject, selectedRepository, limit]);

  const fetchDashboardData = async () => {
    if (!selectedProject || !selectedRepository) return;

    setLoading(true);
    setError('');

    try {
      const data = await dashboardService.getDashboard(selectedProject, selectedRepository, {
        limit: limit,
      });
      setDashboardData(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch dashboard data';
      setError(errorMessage);
      setDashboardData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (project: string) => {
    setSelectedProject(project);
    setSelectedRepository('');
    setDashboardData(null);
  };

  const handleRepositoryChange = (repository: string) => {
    setSelectedRepository(repository);
    setDashboardData(null);
  };

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  return (
    <div className="dashboard">
      <Navbar onLogout={onLogout} />
      
      <div className="dashboard-content">
        <div className="dashboard-header">
          <h1>Repository Analytics Dashboard</h1>
          <p>Comprehensive insights into repository activity and commit patterns</p>
        </div>

        <ProjectRepositorySelector
          selectedProject={selectedProject}
          selectedRepository={selectedRepository}
          limit={limit}
          loading={loading}
          onProjectChange={handleProjectChange}
          onRepositoryChange={handleRepositoryChange}
          onLimitChange={handleLimitChange}
          onError={handleError}
          showCommitsLimit={true}
          className="dashboard-selector"
        />

        {error && (
          <div className="error-message">
            <h3>Error</h3>
            <p>{error}</p>
            <button onClick={fetchDashboardData} className="retry-btn">
              Retry
            </button>
          </div>
        )}

        {loading && (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading dashboard data...</p>
          </div>
        )}

        {dashboardData && !loading && (
          <div className="dashboard-widgets">
            {/* Overview Stats */}
            <div className="widget overview-stats">
              <h3>Overview</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-value">{dashboardData.total_commits}</div>
                  <div className="stat-label">Total Commits</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{dashboardData.analysis_period.start}</div>
                  <div className="stat-label">Analysis Start</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{dashboardData.analysis_period.end}</div>
                  <div className="stat-label">Analysis End</div>
                </div>
              </div>
            </div>

            {/* Top Authors */}
            <div className="widget top-authors">
              <h3>Top Contributors</h3>
              <div className="authors-list">
                {dashboardData.top_authors.map((author, index) => (
                  <div key={author.author} className="author-item">
                    <div className="author-rank">#{index + 1}</div>
                    <div className="author-info">
                      <div className="author-name">{author.author}</div>
                      <div className="author-stats">
                        {author.commit_count} commits ({author.percentage}%)
                      </div>
                    </div>
                    <div className="author-bar">
                      <div 
                        className="author-progress" 
                        style={{ width: `${author.percentage}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Commit Patterns */}
            <div className="widget commit-patterns">
              <h3>Commit Message Patterns</h3>
              <div className="patterns-list">
                {dashboardData.commit_patterns.map((pattern) => (
                  <div key={pattern.pattern} className="pattern-item">
                    <div className="pattern-info">
                      <div className="pattern-name">{pattern.pattern}</div>
                      <div className="pattern-stats">
                        {pattern.count} commits ({pattern.percentage}%)
                      </div>
                    </div>
                    <div className="pattern-bar">
                      <div 
                        className="pattern-progress" 
                        style={{ width: `${pattern.percentage}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Daily Activity */}
            <div className="widget daily-activity">
              <h3>Daily Activity</h3>
              <div className="activity-chart">
                {Object.entries(dashboardData.daily_activity).map(([day, count]) => {
                  const maxCount = Math.max(...Object.values(dashboardData.daily_activity));
                  const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
                  
                  return (
                    <div key={day} className="activity-bar">
                      <div className="bar-container">
                        <div 
                          className="bar-fill" 
                          style={{ height: `${percentage}%` }}
                        ></div>
                      </div>
                      <div className="bar-label">{day.slice(0, 3)}</div>
                      <div className="bar-value">{count}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Hourly Activity */}
            <div className="widget hourly-activity">
              <h3>Hourly Activity</h3>
              <div className="hourly-chart">
                {Object.entries(dashboardData.hourly_activity)
                  .sort(([a], [b]) => a.localeCompare(b))
                  .map(([hour, count]) => {
                    const maxCount = Math.max(...Object.values(dashboardData.hourly_activity));
                    const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
                    
                    return (
                      <div key={hour} className="hourly-bar">
                        <div className="bar-container">
                          <div 
                            className="bar-fill" 
                            style={{ height: `${percentage}%` }}
                          ></div>
                        </div>
                        <div className="bar-label">{hour}</div>
                        <div className="bar-value">{count}</div>
                      </div>
                    );
                  })}
              </div>
            </div>
          </div>
        )}

        {!selectedProject && !loading && (
          <div className="empty-state">
            <h3>Select a Project and Repository</h3>
            <p>Choose a project and repository from the dropdowns above to view analytics.</p>
          </div>
        )}
      </div>
    </div>
  );
}
