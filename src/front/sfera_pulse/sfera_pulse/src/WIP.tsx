import { useState, useEffect } from 'react';
import { wipService, type WIPBranch } from './api/wip';
import ProjectRepositorySelector from './components/ProjectRepositorySelector';
import Navbar from './components/Navbar';
import './WIP.css';

interface WIPProps {
  onLogout: () => void;
}

export default function WIP({ onLogout }: WIPProps) {
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [selectedRepository, setSelectedRepository] = useState<string>('');
  const [limit, setLimit] = useState<number>(20);
  const [branches, setBranches] = useState<WIPBranch[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // Fetch WIP branches when project and repository are selected
  useEffect(() => {
    if (selectedProject && selectedRepository) {
      fetchWIPBranches();
    }
  }, [selectedProject, selectedRepository, limit]);

  const fetchWIPBranches = async () => {
    if (!selectedProject || !selectedRepository) return;

    setLoading(true);
    setError('');
    try {
      const response = await wipService.getWIPBranches(
        selectedProject,
        selectedRepository,
        limit,
        'committed_at',
        'desc'
      );
      setBranches(response.branches || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch WIP branches';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (project: string) => {
    setSelectedProject(project);
    setSelectedRepository('');
    setBranches([]);
  };

  const handleRepositoryChange = (repository: string) => {
    setSelectedRepository(repository);
  };

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  // Calculate cycle time (time from now to branch creation)
  const calculateCycleTime = (lastCommitDatetime?: string): string => {
    if (!lastCommitDatetime) return 'N/A';

    const now = new Date();
    const commitDate = new Date(lastCommitDatetime);
    const diffInMs = now.getTime() - commitDate.getTime();

    const days = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
    const hours = Math.floor((diffInMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((diffInMs % (1000 * 60 * 60)) / (1000 * 60));

    if (days > 0) {
      return `${days}d ${hours}h`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  // Format date for display
  const formatDate = (dateString?: string): string => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div className="wip-container">
      <Navbar onLogout={onLogout} />

      <div className="wip-content">
        <h1>Work In Progress / Active Branches</h1>

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
        />

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {loading && (
          <div className="loading-message">
            Loading WIP branches...
          </div>
        )}

        {!loading && !error && branches.length > 0 && (
          <div className="wip-table-container">
            <h2>WIP Branches ({branches.length})</h2>
            <div className="table-wrapper">
              <table className="wip-table">
                <thead>
                  <tr>
                    <th>Branch Name</th>
                    <th>Last Commit Message</th>
                    <th>Author</th>
                    <th>Last Commit Date</th>
                    <th>Cycle Time</th>
                  </tr>
                </thead>
                <tbody>
                  {branches.map((branch, index) => (
                    <tr key={`${branch.name}-${index}`}>
                      <td className="branch-name">
                        {branch.name}
                      </td>
                      <td className="commit-message">
                        {branch.last_commit_message || 'N/A'}
                      </td>
                      <td className="author">
                        {branch.last_commit_author || 'N/A'}
                      </td>
                      <td className="commit-date">
                        {formatDate(branch.last_commit_datetime)}
                      </td>
                      <td className="cycle-time">
                        <span className={`cycle-time-badge ${getCycleTimeClass(branch.last_commit_datetime)}`}>
                          {calculateCycleTime(branch.last_commit_datetime)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {!loading && !error && branches.length === 0 && selectedProject && selectedRepository && (
          <div className="no-data-message">
            No WIP branches found for the selected repository.
          </div>
        )}
      </div>
    </div>
  );
}

// Helper function to determine cycle time styling based on age
const getCycleTimeClass = (lastCommitDatetime?: string): string => {
  if (!lastCommitDatetime) return 'cycle-time-unknown';

  const now = new Date();
  const commitDate = new Date(lastCommitDatetime);
  const diffInMs = now.getTime() - commitDate.getTime();
  const days = Math.floor(diffInMs / (1000 * 60 * 60 * 24));

  if (days > 30) return 'cycle-time-old';
  if (days > 7) return 'cycle-time-medium';
  return 'cycle-time-recent';
};
