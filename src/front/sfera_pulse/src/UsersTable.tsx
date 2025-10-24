import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProjectRepositorySelector from './components/ProjectRepositorySelector';
import { usersService, type UserSuggestion } from './api/users';
import './UsersTable.css';

interface UsersTableProps {
  onLogout: () => void;
}

export default function UsersTable({ onLogout }: UsersTableProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  
  // State for project and repository selection
  const [selectedProject, setSelectedProject] = useState(
    searchParams.get('project') || ''
  );
  const [selectedRepository, setSelectedRepository] = useState(
    searchParams.get('repository') || ''
  );
  const [limit, setLimit] = useState(5000);
  
  // State for users data
  const [users, setUsers] = useState<UserSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [totalUsers, setTotalUsers] = useState<number>(0);
  
  // State for search/filtering
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Update URL parameters when selections change
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedProject) params.set('project', selectedProject);
    if (selectedRepository) params.set('repository', selectedRepository);
    setSearchParams(params);
  }, [selectedProject, selectedRepository, setSearchParams]);

  // Fetch users when project, repository, or search query changes
  useEffect(() => {
    if (selectedProject && selectedRepository) {
      fetchUsers();
    } else {
      setUsers([]);
      setTotalUsers(0);
    }
  }, [selectedProject, selectedRepository, limit, searchQuery]);

  const fetchUsers = async () => {
    if (!selectedProject || !selectedRepository) return;

    setLoading(true);
    setError('');
    
    try {
      const response = await usersService.getUserSuggestions(
        selectedProject,
        selectedRepository,
        {
          q: searchQuery.trim() || undefined,
          skipSelf: false,
          limit: limit
        }
      );
      
      setUsers(response.data || []);
      setTotalUsers(response.page?.total || 0);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch users';
      setError(errorMessage);
      setUsers([]);
      setTotalUsers(0);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (project: string) => {
    setSelectedProject(project);
    setSelectedRepository(''); // Reset repository when project changes
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

  const formatUserName = (user: UserSuggestion): string => {
    if (user.full_name) return user.full_name;
    if (user.first_name && user.last_name) {
      return `${user.first_name} ${user.last_name}`;
    }
    if (user.login) return user.login;
    if (user.email) return user.email;
    return 'Unknown User';
  };



  return (
    <div className="kpi-board">
      <Navbar onLogout={onLogout} />
      
      <div className="kpi-board-content">
        <div className="kpi-board-header">
          <h1>KPI Board - User Directory</h1>
          <p>Browse and manage users in your project repositories</p>
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
          showCommitsLimit={false}
          className="kpi-selector"
        />

        {error && (
          <div className="error-message">
            <h3>Error</h3>
            <p>{error}</p>
            <button onClick={fetchUsers} className="retry-btn">
              Retry
            </button>
          </div>
        )}

        {selectedProject && selectedRepository && (
          <div className="users-section">
            <div className="users-header">
              <h2>Users in Repository</h2>
              {totalUsers > 0 && (
                <div className="users-stats">
                  <span className="total-count">Total: {totalUsers}</span>
                  <span className="showing-count">
                    Showing: {users.length} of {totalUsers}
                    {searchQuery && ` (searching for "${searchQuery}")`}
                  </span>
                </div>
              )}
            </div>

            {users.length > 0 && (
              <div className="filter-section">
                <div className="filter-input-container">
                  <input
                    type="text"
                    placeholder="Search users by name, login, email, or principal..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="filter-input"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="clear-filter-btn"
                      title="Clear search"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            )}

            {loading ? (
              <div className="loading-container">
                <div className="loading-spinner"></div>
                <p>Loading users...</p>
              </div>
            ) : users.length > 0 ? (
              <div className="users-table-container">
                <table className="users-table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Login</th>
                      <th>Email</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user, index) => (
                      <tr key={index} className="user-row">
                        <td className="user-name-cell">
                          <div className="user-name">{formatUserName(user)}</div>
                        </td>
                        <td className="user-login-cell">
                          <div className="user-login">{user.login ? `@${user.login}` : '-'}</div>
                        </td>
                        <td className="user-email-cell">
                          <div className="user-email">{user.email || '-'}</div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : searchQuery ? (
              <div className="no-users">
                <p>No users found matching "{searchQuery}".</p>
                <button 
                  onClick={() => setSearchQuery('')} 
                  className="clear-filter-link"
                >
                  Clear search
                </button>
              </div>
            ) : (
              <div className="no-users">
                <p>No users found in this repository.</p>
              </div>
            )}
          </div>
        )}

        {!selectedProject && (
          <div className="selection-prompt">
            <p>Please select a project and repository to view users.</p>
          </div>
        )}
      </div>
    </div>
  );
}
