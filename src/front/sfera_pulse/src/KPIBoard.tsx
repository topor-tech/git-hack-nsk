import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import Navbar from './components/Navbar';
import ProjectRepositorySelector from './components/ProjectRepositorySelector';
import Tooltip from './components/Tooltip';
import { kpiBoardService, type KPIBoardStats, type DeveloperKPI } from './api/kpi';
import './KPIBoard.css';

interface KPIBoardProps {
  onLogout: () => void;
}

export default function KPIBoard({ onLogout }: KPIBoardProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedProject, setSelectedProject] = useState(searchParams.get('project') || '');
  const [selectedRepository, setSelectedRepository] = useState(searchParams.get('repository') || '');
  const [limit, setLimit] = useState(parseInt(searchParams.get('limit') || '500'));
  const [selectedDeveloper, setSelectedDeveloper] = useState(searchParams.get('developer') || '');
  const [kpiData, setKpiData] = useState<KPIBoardStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Update URL parameters when selections change
  useEffect(() => {
    const params = new URLSearchParams();
    if (selectedProject) params.set('project', selectedProject);
    if (selectedRepository) params.set('repository', selectedRepository);
    if (limit !== 500) params.set('limit', limit.toString());
    if (selectedDeveloper) params.set('developer', selectedDeveloper);
    setSearchParams(params);
  }, [selectedProject, selectedRepository, limit, selectedDeveloper, setSearchParams]);

  // Fetch KPI data when project and repository are selected
  useEffect(() => {
    if (selectedProject && selectedRepository) {
      fetchKPIData();
    }
  }, [selectedProject, selectedRepository, limit]);

  const fetchKPIData = async () => {
    if (!selectedProject || !selectedRepository) return;

    setLoading(true);
    setError('');

    try {
      console.log('Fetching KPI data for:', { selectedProject, selectedRepository, limit });
      const data = await kpiBoardService.getKPIBoard(selectedProject, selectedRepository, {
        limit: limit,
      });
      console.log('KPI data received:', data);
      setKpiData(data);
    } catch (err) {
      console.error('KPI fetch error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch KPI data';
      setError(errorMessage);
      setKpiData(null);
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (project: string) => {
    setSelectedProject(project);
    setSelectedRepository('');
    setSelectedDeveloper('');
    setKpiData(null);
  };

  const handleRepositoryChange = (repository: string) => {
    setSelectedRepository(repository);
    setSelectedDeveloper('');
    setKpiData(null);
  };

  const handleLimitChange = (newLimit: number) => {
    setLimit(newLimit);
  };

  const handleDeveloperChange = (developer: string) => {
    setSelectedDeveloper(developer);
    // Update URL parameters immediately
    const params = new URLSearchParams();
    if (selectedProject) params.set('project', selectedProject);
    if (selectedRepository) params.set('repository', selectedRepository);
    if (limit !== 500) params.set('limit', limit.toString());
    if (developer) params.set('developer', developer);
    setSearchParams(params);
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  // Filter developers based on selection
  const filteredDevelopers = selectedDeveloper 
    ? kpiData?.developer_kpis.filter(dev => dev.developer === selectedDeveloper) || []
    : kpiData?.developer_kpis || [];

  return (
    <div className="kpi-board">
      <Navbar onLogout={onLogout} />
      
      <div className="kpi-board-content">
        <div className="kpi-board-header">
          <h1>KPI Board - Developer Performance Analytics</h1>
          <Tooltip
            content={
              <div>
                <h4>Test Tooltip</h4>
                <p>This is a test tooltip to verify functionality.</p>
              </div>
            }
            position="top"
          >
            <p>Comprehensive developer performance metrics and team analytics</p>
          </Tooltip>
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
          className="kpi-board-selector"
        />

        {/* Developer Filter */}
        {kpiData && kpiData.developer_kpis.length > 0 && (
          <div className="developer-filter">
            <label htmlFor="developer-select">Filter by Developer:</label>
            <select
              id="developer-select"
              value={selectedDeveloper}
              onChange={(e) => handleDeveloperChange(e.target.value)}
              disabled={loading}
            >
              <option value="">All Developers</option>
              {kpiData.developer_kpis.map((dev) => (
                <option key={dev.developer} value={dev.developer}>
                  {dev.developer}
                </option>
              ))}
            </select>
          </div>
        )}

        {error && (
          <div className="error-message">
            <h3>Error</h3>
            <p>{error}</p>
            <button onClick={fetchKPIData} className="retry-btn">
              Retry
            </button>
          </div>
        )}

        {loading && (
          <div className="loading-container">
            <div className="loading-spinner"></div>
            <p>Loading KPI data...</p>
          </div>
        )}

        {kpiData && !loading && (
          <div className="kpi-board-widgets">
            {/* Overview Stats */}
            <div className="widget overview-stats">
              <h3>Overview</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <div className="stat-value">{kpiData.total_developers}</div>
                  <div className="stat-label">Total Developers</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{kpiData.analysis_period.start}</div>
                  <div className="stat-label">Analysis Start</div>
                </div>
                <div className="stat-item">
                  <div className="stat-value">{kpiData.analysis_period.end}</div>
                  <div className="stat-label">Analysis End</div>
                </div>
              </div>
            </div>

            {/* Team Averages */}
            <div className="widget team-averages">
              <h3>Team Averages</h3>
              <div className="averages-grid">
                <Tooltip
                  content={
                    <div className="metric-tooltip">
                      <div className="metric-category">THROUGHPUT METRICS</div>
                      <p className="metric-description">Measures developer productivity and code output volume.</p>
                      <div className="calculation-steps">
                        <h5>Calculation Steps:</h5>
                        <ol>
                          <li>Count total commits by developer in analysis period</li>
                          <li>Sum lines added and removed across all commits</li>
                          <li>Count total files modified</li>
                          <li>Calculate throughput score: commits ÷ analysis period days</li>
                          <li>Calculate productivity score: (lines_added + lines_removed) ÷ commits</li>
                        </ol>
                      </div>
                      <div className="formula">Throughput Score = Commits ÷ Analysis Period Days</div>
                      <div className="overall-weight">Weight: 25% of Overall Score</div>
                    </div>
                  }
                  position="top"
                  maxWidth="400px"
                >
                  <div className="average-item">
                    <div className="average-value">{kpiData.team_averages.average_throughput.toFixed(2)}</div>
                    <div className="average-label">Avg Throughput</div>
                  </div>
                </Tooltip>
                <Tooltip
                  content={
                    <div className="metric-tooltip">
                      <div className="metric-category">CYCLE TIME METRICS</div>
                      <p className="metric-description">Measures development velocity and time between commits.</p>
                      <div className="calculation-steps">
                        <h5>Calculation Steps:</h5>
                        <ol>
                          <li>Sort commits by creation time for each developer</li>
                          <li>Calculate time intervals between consecutive commits</li>
                          <li>Find average, fastest, and slowest intervals</li>
                          <li>Calculate cycle time score: 100 ÷ (average_interval + 1)</li>
                        </ol>
                      </div>
                      <div className="formula">Cycle Time Score = 100 ÷ (Average Interval + 1)</div>
                      <div className="overall-weight">Weight: 20% of Overall Score</div>
                    </div>
                  }
                  position="top"
                  maxWidth="400px"
                >
                  <div className="average-item">
                    <div className="average-value">{kpiData.team_averages.average_cycle_time.toFixed(2)}</div>
                    <div className="average-label">Avg Cycle Time</div>
                  </div>
                </Tooltip>
                <Tooltip
                  content={
                    <div className="metric-tooltip">
                      <div className="metric-category">QUALITY METRICS</div>
                      <p className="metric-description">Measures commit size patterns and code consistency.</p>
                      <div className="calculation-steps">
                        <h5>Calculation Steps:</h5>
                        <ol>
                          <li>Count large commits (&gt;500 total lines changed)</li>
                          <li>Count small commits (≤50 total lines changed)</li>
                          <li>Calculate average commit size</li>
                          <li>Calculate quality score: % of medium-sized commits (50-500 lines)</li>
                          <li>Calculate consistency score: max(0, 100 - variance/100)</li>
                        </ol>
                      </div>
                      <div className="formula">Quality Score = % of Medium-Sized Commits</div>
                      <div className="overall-weight">Weight: 25% of Overall Score</div>
                    </div>
                  }
                  position="top"
                  maxWidth="400px"
                >
                  <div className="average-item">
                    <div className="average-value">{kpiData.team_averages.average_quality.toFixed(2)}</div>
                    <div className="average-label">Avg Quality</div>
                  </div>
                </Tooltip>
                <Tooltip
                  content={
                    <div className="metric-tooltip">
                      <div className="metric-category">ACTIVITY PATTERN METRICS</div>
                      <p className="metric-description">Measures work schedule patterns and timing analysis.</p>
                      <div className="calculation-steps">
                        <h5>Calculation Steps:</h5>
                        <ol>
                          <li>Analyze commits by day of week and hour</li>
                          <li>Count weekend commits (Saturday/Sunday)</li>
                          <li>Count work hours commits (9 AM - 5 PM)</li>
                          <li>Calculate work hours ratio and weekend ratio</li>
                          <li>Calculate activity score: (work_hours_ratio × 80) + (weekend_ratio × 20)</li>
                        </ol>
                      </div>
                      <div className="formula">Activity Score = (Work Hours Ratio × 80) + (Weekend Ratio × 20)</div>
                      <div className="overall-weight">Weight: 15% of Overall Score</div>
                    </div>
                  }
                  position="top"
                  maxWidth="400px"
                >
                  <div className="average-item">
                    <div className="average-value">{kpiData.team_averages.average_activity.toFixed(2)}</div>
                    <div className="average-label">Avg Activity</div>
                  </div>
                </Tooltip>
                <Tooltip
                  content={
                    <div className="metric-tooltip">
                      <div className="metric-category">OVERALL SCORING</div>
                      <p className="metric-description">Weighted average of all KPI metrics.</p>
                      <div className="calculation-steps">
                        <h5>Weight Distribution:</h5>
                        <ol>
                          <li>Throughput: 25% weight</li>
                          <li>Cycle Time: 20% weight</li>
                          <li>Work in Progress: 15% weight</li>
                          <li>Quality: 25% weight</li>
                          <li>Activity: 15% weight</li>
                        </ol>
                      </div>
                      <div className="formula">Overall = (Throughput×0.25) + (Cycle×0.20) + (WIP×0.15) + (Quality×0.25) + (Activity×0.15)</div>
                      <div className="overall-weight">Final Weighted Score</div>
                    </div>
                  }
                  position="top"
                  maxWidth="400px"
                >
                  <div className="average-item">
                    <div className="average-value">{kpiData.team_averages.average_overall.toFixed(2)}</div>
                    <div className="average-label">Avg Overall Score</div>
                  </div>
                </Tooltip>
              </div>
            </div>

            {/* Top Performers */}
            <div className="widget top-performers">
              <h3>Top Performers</h3>
              <div className="performers-grid">
                <div className="performer-item">
                  <div className="performer-category">Throughput</div>
                  <div className="performer-name">{kpiData.top_performers.throughput}</div>
                </div>
                <div className="performer-item">
                  <div className="performer-category">Cycle Time</div>
                  <div className="performer-name">{kpiData.top_performers.cycle_time}</div>
                </div>
                <div className="performer-item">
                  <div className="performer-category">Quality</div>
                  <div className="performer-name">{kpiData.top_performers.quality}</div>
                </div>
                <div className="performer-item">
                  <div className="performer-category">Activity</div>
                  <div className="performer-name">{kpiData.top_performers.activity}</div>
                </div>
                <div className="performer-item">
                  <div className="performer-category">Overall</div>
                  <div className="performer-name">{kpiData.top_performers.overall}</div>
                </div>
              </div>
            </div>

            {/* Developer KPI Cards */}
            <div className="widget developer-kpis">
              <h3>Developer Performance</h3>
              <div className="kpi-cards">
                {filteredDevelopers.map((developer) => (
                  <DeveloperKPICard key={developer.developer} developer={developer} />
                ))}
              </div>
            </div>
          </div>
        )}

        {!selectedProject && !loading && (
          <div className="empty-state">
            <h3>Select a Project and Repository</h3>
            <p>Choose a project and repository from the dropdowns above to view KPI analytics.</p>
          </div>
        )}
      </div>
    </div>
  );
}

interface DeveloperKPICardProps {
  developer: DeveloperKPI;
}

function DeveloperKPICard({ developer }: DeveloperKPICardProps) {
  return (
    <div className="kpi-card">
      <div className="kpi-card-header">
        <h4>{developer.developer}</h4>
        <Tooltip
          content={
            <div className="metric-tooltip">
              <div className="metric-category">OVERALL SCORING</div>
              <p className="metric-description">Weighted average of all KPI metrics.</p>
              <div className="calculation-steps">
                <h5>Weight Distribution:</h5>
                <ol>
                  <li>Throughput: 25% weight</li>
                  <li>Cycle Time: 20% weight</li>
                  <li>Work in Progress: 15% weight</li>
                  <li>Quality: 25% weight</li>
                  <li>Activity: 15% weight</li>
                </ol>
              </div>
              <div className="formula">Overall = (Throughput×0.25) + (Cycle×0.20) + (WIP×0.15) + (Quality×0.25) + (Activity×0.15)</div>
              <div className="overall-weight">Final Weighted Score</div>
            </div>
          }
          position="top"
          maxWidth="400px"
        >
          <div className="overall-score">
            <span className="score-label">Overall Score</span>
            <span className="score-value">{developer.overall_score.toFixed(2)}</span>
          </div>
        </Tooltip>
      </div>

      <div className="kpi-metrics">
        {/* Throughput Metrics */}
        <div className="metric-section">
          <Tooltip
            content={
              <div className="metric-tooltip">
                <div className="metric-category">THROUGHPUT METRICS</div>
                <p className="metric-description">Measures developer productivity and code output volume.</p>
                <div className="calculation-steps">
                  <h5>Calculation Steps:</h5>
                  <ol>
                    <li>Count total commits by developer in analysis period</li>
                    <li>Sum lines added and removed across all commits</li>
                    <li>Count total files modified</li>
                    <li>Calculate throughput score: commits ÷ analysis period days</li>
                    <li>Calculate productivity score: (lines_added + lines_removed) ÷ commits</li>
                  </ol>
                </div>
                <div className="formula">Throughput Score = Commits ÷ Analysis Period Days</div>
                <div className="overall-weight">Weight: 25% of Overall Score</div>
              </div>
            }
            position="top"
            maxWidth="400px"
          >
            <h5>Throughput</h5>
          </Tooltip>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">Commits</span>
              <span className="metric-value">{developer.throughput.commits_completed}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Lines Added</span>
              <span className="metric-value">{developer.throughput.lines_added.toLocaleString()}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Files Changed</span>
              <span className="metric-value">{developer.throughput.files_changed}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Score</span>
              <span className="metric-value">{developer.throughput.throughput_score.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Cycle Time Metrics */}
        <div className="metric-section">
          <Tooltip
            content={
              <div className="metric-tooltip">
                <div className="metric-category">CYCLE TIME METRICS</div>
                <p className="metric-description">Measures development velocity and time between commits.</p>
                <div className="calculation-steps">
                  <h5>Calculation Steps:</h5>
                  <ol>
                    <li>Sort commits by creation time for each developer</li>
                    <li>Calculate time intervals between consecutive commits</li>
                    <li>Find average, fastest, and slowest intervals</li>
                    <li>Calculate cycle time score: 100 ÷ (average_interval + 1)</li>
                  </ol>
                </div>
                <div className="formula">Cycle Time Score = 100 ÷ (Average Interval + 1)</div>
                <div className="overall-weight">Weight: 20% of Overall Score</div>
              </div>
            }
            position="top"
            maxWidth="400px"
          >
            <h5>Cycle Time</h5>
          </Tooltip>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">Avg Interval (h)</span>
              <span className="metric-value">{developer.cycle_time.average_commit_interval_hours.toFixed(2)}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Fastest (h)</span>
              <span className="metric-value">{developer.cycle_time.fastest_commit_interval_hours.toFixed(2)}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Slowest (h)</span>
              <span className="metric-value">{developer.cycle_time.slowest_commit_interval_hours.toFixed(2)}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Score</span>
              <span className="metric-value">{developer.cycle_time.cycle_time_score.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Quality Metrics */}
        <div className="metric-section">
          <Tooltip
            content={
              <div className="metric-tooltip">
                <div className="metric-category">QUALITY METRICS</div>
                <p className="metric-description">Measures commit size patterns and code consistency.</p>
                <div className="calculation-steps">
                  <h5>Calculation Steps:</h5>
                  <ol>
                    <li>Count large commits ({'>'}500 total lines changed)</li>
                    <li>Count small commits (≤50 total lines changed)</li>
                    <li>Calculate average commit size</li>
                    <li>Calculate quality score: % of medium-sized commits (50-500 lines)</li>
                    <li>Calculate consistency score: max(0, 100 - variance/100)</li>
                  </ol>
                </div>
                <div className="formula">Quality Score = % of Medium-Sized Commits</div>
                <div className="overall-weight">Weight: 25% of Overall Score</div>
              </div>
            }
            position="top"
            maxWidth="400px"
          >
            <h5>Quality</h5>
          </Tooltip>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">Large Commits</span>
              <span className="metric-value">{developer.quality.large_commits_count}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Small Commits</span>
              <span className="metric-value">{developer.quality.small_commits_count}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Avg Size</span>
              <span className="metric-value">{developer.quality.average_commit_size.toFixed(1)}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Score</span>
              <span className="metric-value">{developer.quality.quality_score.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Activity Patterns */}
        <div className="metric-section">
          <Tooltip
            content={
              <div className="metric-tooltip">
                <div className="metric-category">ACTIVITY PATTERN METRICS</div>
                <p className="metric-description">Measures work schedule patterns and timing analysis.</p>
                <div className="calculation-steps">
                  <h5>Calculation Steps:</h5>
                  <ol>
                    <li>Analyze commits by day of week and hour</li>
                    <li>Count weekend commits (Saturday/Sunday)</li>
                    <li>Count work hours commits (9 AM - 5 PM)</li>
                    <li>Calculate work hours ratio and weekend ratio</li>
                    <li>Calculate activity score: (work_hours_ratio × 80) + (weekend_ratio × 20)</li>
                  </ol>
                </div>
                <div className="formula">Activity Score = (Work Hours Ratio × 80) + (Weekend Ratio × 20)</div>
                <div className="overall-weight">Weight: 15% of Overall Score</div>
              </div>
            }
            position="top"
            maxWidth="400px"
          >
            <h5>Activity Patterns</h5>
          </Tooltip>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">Most Active Day</span>
              <span className="metric-value">{developer.activity_patterns.most_active_day}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Most Active Hour</span>
              <span className="metric-value">{developer.activity_patterns.most_active_hour}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Work Hours Commits</span>
              <span className="metric-value">{developer.activity_patterns.work_hours_commits}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Score</span>
              <span className="metric-value">{developer.activity_patterns.activity_score.toFixed(2)}</span>
            </div>
          </div>
        </div>

        {/* Work in Progress */}
        <div className="metric-section">
          <Tooltip
            content={
              <div className="metric-tooltip">
                <div className="metric-category">WORK IN PROGRESS METRICS</div>
                <p className="metric-description">Measures concurrent work tracking and focus scoring.</p>
                <div className="calculation-steps">
                  <h5>Calculation Steps:</h5>
                  <ol>
                    <li>Count total commits by developer (proxy for concurrent work)</li>
                    <li>Calculate concurrent work score: 0-5 commits = linear increase, 5-20 = moderate, &gt;20 = decreasing</li>
                    <li>Calculate focus score: max(0, 100 - active_commits × 2)</li>
                  </ol>
                </div>
                <div className="formula">Focus Score = max(0, 100 - Active Commits × 2)</div>
                <div className="overall-weight">Weight: 15% of Overall Score</div>
              </div>
            }
            position="top"
            maxWidth="400px"
          >
            <h5>Work in Progress</h5>
          </Tooltip>
          <div className="metric-grid">
            <div className="metric-item">
              <span className="metric-label">Active Commits</span>
              <span className="metric-value">{developer.work_in_progress.active_commits_count}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Concurrent Score</span>
              <span className="metric-value">{developer.work_in_progress.concurrent_work_score.toFixed(2)}</span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Focus Score</span>
              <span className="metric-value">{developer.work_in_progress.focus_score.toFixed(2)}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
