import { useState, useEffect } from 'react';
import { projectsService, type Project } from '../api/projects';
import { repositoriesService, type Repository } from '../api/repositories';
import './ProjectRepositorySelector.css';

export interface ProjectRepositorySelectorProps {
  selectedProject: string;
  selectedRepository: string;
  limit: number;
  loading?: boolean;
  onProjectChange: (project: string) => void;
  onRepositoryChange: (repository: string) => void;
  onLimitChange: (limit: number) => void;
  onError?: (error: string) => void;
  showCommitsLimit?: boolean;
  className?: string;
}

export default function ProjectRepositorySelector({
  selectedProject,
  selectedRepository,
  limit,
  loading = false,
  onProjectChange,
  onRepositoryChange,
  onLimitChange,
  onError,
  showCommitsLimit = true,
  className = ''
}: ProjectRepositorySelectorProps) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(true);
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [repositoriesLoading, setRepositoriesLoading] = useState(false);

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchRepositories();
    }
  }, [selectedProject]);

  const fetchProjects = async () => {
    setProjectsLoading(true);
    try {
      const response = await projectsService.getProjects(30, 'name', 'asc');
      setProjects(response.data || []);
      // Set the first project as default only if no project is selected
      if (response.data && response.data.length > 0 && !selectedProject) {
        const firstProject = response.data[0].full_name;
        onProjectChange(firstProject);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch projects';
      onError?.(errorMessage);
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
      // Only auto-select the first repository if no repository is currently selected
      // This prevents conflicts with parent component's repository reset logic
      if (response.data && response.data.length > 0 && !selectedRepository) {
        const firstRepository = response.data[0].name;
        onRepositoryChange(firstRepository);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch repositories';
      onError?.(errorMessage);
    } finally {
      setRepositoriesLoading(false);
    }
  };

  const handleProjectChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProject = e.target.value;
    onProjectChange(newProject);
    onRepositoryChange(''); // Reset repository selection when project changes
  };

  const handleRepositoryChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newRepository = e.target.value;
    onRepositoryChange(newRepository);
  };

  const handleLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLimit = parseInt(e.target.value);
    onLimitChange(newLimit);
  };

  return (
    <div className={`project-info ${className}`}>
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

          {showCommitsLimit && (
            <div className="commits-selector">
              <label htmlFor="commits-limit">Show commits:</label>
              <select
                id="commits-limit"
                value={limit}
                onChange={handleLimitChange}
                disabled={loading}
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
                <option value={200}>200</option>
                <option value={500}>500</option>
                <option value={1000}>1000</option>
              </select>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
