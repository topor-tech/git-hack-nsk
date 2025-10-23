import { useState, useEffect } from 'react';
import { commitsService, type SimpleCommit } from './api/commits';
import { projectsService, type Project } from './api/projects';
import { repositoriesService, type Repository } from './api/repositories';
import './Home.css';

interface HomeProps {
  onLogout: () => void;
}

export default function Home({ onLogout }: HomeProps) {
  const [commits, setCommits] = useState<SimpleCommit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [limit, setLimit] = useState(10);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selectedRepository, setSelectedRepository] = useState<string>('');
  const [repositoriesLoading, setRepositoriesLoading] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchRepositories();
    }
  }, [selectedProject]);

  useEffect(() => {
    if (selectedProject && selectedRepository) {
      fetchCommits();
    }
  }, [limit, selectedProject, selectedRepository]);

  const fetchProjects = async () => {
    setProjectsLoading(true);
    try {
      const response = await projectsService.getProjects(30, 'name', 'asc');
      setProjects(response.data || []);
      // Set the first project as default
      if (response.data && response.data.length > 0) {
        setSelectedProject(response.data[0].full_name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch projects');
    } finally {
      setProjectsLoading(false);
    }
  };

  const fetchRepositories = async () => {
    if (!selectedProject) return;

    setRepositoriesLoading(true);
    try {
      const response = await repositoriesService.getRepositories(selectedProject, 30, 'name', 'asc');
      setRepositories(response.data || []);
      // Set the first repository as default
      if (response.data && response.data.length > 0) {
        setSelectedRepository(response.data[0].name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch repositories');
    } finally {
      setRepositoriesLoading(false);
    }
  };

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

  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLimit(parseInt(e.target.value));
  };

  const handleProjectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedProject(e.target.value);
    setSelectedRepository(''); // Reset repository selection when project changes
  };

  const handleRepositoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedRepository(e.target.value);
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
        <h2>Project & Repository Selection</h2>
        {projectsLoading ? (
          <div className="selectors-container">
            <div className="project-selector">
              <div className="skeleton-label"></div>
              <div className="skeleton-select"></div>
            </div>
          </div>
        ) : (
          <div className="selectors-container">
            <div className="project-selector">
              <label htmlFor="project-select">Select Project: </label>
              <select
                id="project-select"
                value={selectedProject}
                onChange={handleProjectChange}
                disabled={loading}
              >
                {projects.map((project) => (
                  <option key={project.id} value={project.full_name}>
                    {project.full_name}
                  </option>
                ))}
              </select>
            </div>

            {selectedProject && (
              <div className="repository-selector">
                {repositoriesLoading ? (
                  <div className="repository-selector">
                    <div className="skeleton-label"></div>
                    <div className="skeleton-select"></div>
                  </div>
                ) : (
                  <div>
                    <label htmlFor="repository-select">Select Repository: </label>
                    <select
                      id="repository-select"
                      value={selectedRepository}
                      onChange={handleRepositoryChange}
                      disabled={loading}
                    >
                      {repositories.map((repository) => (
                        <option key={repository.id} value={repository.name}>
                          {repository.name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
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
  );
}
