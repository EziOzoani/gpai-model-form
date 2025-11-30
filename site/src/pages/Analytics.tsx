import React, { useState, useEffect } from 'react';
import {
  Chart as ChartJS,
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  RadialLinearScale,
  Tooltip,
  Legend,
  Title
} from 'chart.js';
import { Pie, Bar, Doughnut, Line, Radar } from 'react-chartjs-2';

// Register ChartJS components
ChartJS.register(
  ArcElement,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  RadialLinearScale,
  Tooltip,
  Legend,
  Title
);

interface Metric {
  value: number;
  label: string;
  icon?: string;
  percentage?: number;
  unit?: string;
}

interface ChartData {
  type: string;
  data: any[];
  title: string;
  [key: string]: any;
}

const Analytics: React.FC = () => {
  const [metrics, setMetrics] = useState<Record<string, Metric>>({});
  const [charts, setCharts] = useState<Record<string, ChartData>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      // Fetch metrics
      const metricsRes = await fetch('http://localhost:5001/api/analysis/metrics');
      const metricsData = await metricsRes.json();
      setMetrics(metricsData);

      // Fetch chart data
      const chartNames = [
        'provider_pie',
        'regional_distribution',
        'size_distribution',
        'timeline',
        'provider_comparison_radar',
        'section_completeness'
      ];

      const chartPromises = chartNames.map(name =>
        fetch(`http://localhost:5001/api/analysis/visualizations/${name}`)
          .then(res => res.json())
          .then(data => ({ name, data }))
      );

      const chartsData = await Promise.all(chartPromises);
      const chartsMap: Record<string, ChartData> = {};
      
      chartsData.forEach(({ name, data }) => {
        chartsMap[name] = data;
      });
      
      setCharts(chartsMap);
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load analytics');
      setLoading(false);
    }
  };

  const renderChart = (chartKey: string, chartData: ChartData) => {
    const commonOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom' as const,
        },
        title: {
          display: true,
          text: chartData.title,
          font: {
            size: 16
          }
        }
      }
    };

    switch (chartData.type) {
      case 'pie':
        return (
          <Pie
            data={{
              labels: chartData.data.map(d => d.name),
              datasets: [{
                data: chartData.data.map(d => d.value),
                backgroundColor: chartData.data.map(d => d.color),
                borderWidth: 1
              }]
            }}
            options={commonOptions}
          />
        );

      case 'bar':
        return (
          <Bar
            data={{
              labels: chartData.data.map(d => d.region),
              datasets: [{
                label: 'Model Count',
                data: chartData.data.map(d => d.count),
                backgroundColor: chartData.color || '#3498DB'
              }]
            }}
            options={{
              ...commonOptions,
              scales: {
                y: {
                  beginAtZero: true
                }
              }
            }}
          />
        );

      case 'donut':
        return (
          <Doughnut
            data={{
              labels: chartData.data.map(d => d.name),
              datasets: [{
                data: chartData.data.map(d => d.value),
                backgroundColor: chartData.data.map(d => d.color),
                borderWidth: 1
              }]
            }}
            options={commonOptions}
          />
        );

      case 'line':
        return (
          <Line
            data={{
              labels: chartData.data.map(d => d.date),
              datasets: [{
                label: 'Models Released',
                data: chartData.data.map(d => d.value),
                borderColor: '#3498DB',
                backgroundColor: 'rgba(52, 152, 219, 0.1)',
                tension: 0.4
              }]
            }}
            options={{
              ...commonOptions,
              scales: {
                y: {
                  beginAtZero: true
                }
              }
            }}
          />
        );

      case 'radar':
        return (
          <Radar
            data={{
              labels: chartData.axes,
              datasets: chartData.data.map((provider: any, idx: number) => ({
                label: provider.provider,
                data: provider.metrics.map((m: any) => m.value),
                borderColor: ['#3498DB', '#E74C3C', '#2ECC71'][idx % 3],
                backgroundColor: ['rgba(52, 152, 219, 0.2)', 'rgba(231, 76, 60, 0.2)', 'rgba(46, 204, 113, 0.2)'][idx % 3],
              }))
            }}
            options={{
              ...commonOptions,
              scales: {
                r: {
                  beginAtZero: true,
                  max: 100
                }
              }
            }}
          />
        );

      case 'grouped-bar':
        return (
          <Bar
            data={{
              labels: chartData.data.map(d => d.section),
              datasets: chartData.series.map((series: any) => ({
                label: series.name,
                data: chartData.data.map(d => d[series.key]),
                backgroundColor: series.color
              }))
            }}
            options={{
              ...commonOptions,
              scales: {
                y: {
                  beginAtZero: true
                }
              }
            }}
          />
        );

      default:
        return <div>Unsupported chart type: {chartData.type}</div>;
    }
  };

  if (loading) return <div className="flex items-center justify-center h-64">Loading analytics...</div>;
  if (error) return <div className="text-red-500 text-center">{error}</div>;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100">GPAI Model Analytics</h1>
      
      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {Object.entries(metrics).map(([key, metric]) => (
          <div key={key} className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600 dark:text-gray-400">{metric.label}</p>
                <p className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                  {metric.value}
                  {metric.unit && <span className="text-lg">{metric.unit}</span>}
                </p>
                {metric.percentage && (
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {metric.percentage}% of total
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Provider Distribution */}
        {charts.provider_pie && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div style={{ height: '300px' }}>
              {renderChart('provider_pie', charts.provider_pie)}
            </div>
          </div>
        )}

        {/* Regional Distribution */}
        {charts.regional_distribution && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div style={{ height: '300px' }}>
              {renderChart('regional_distribution', charts.regional_distribution)}
            </div>
          </div>
        )}

        {/* Size Distribution */}
        {charts.size_distribution && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div style={{ height: '300px' }}>
              {renderChart('size_distribution', charts.size_distribution)}
            </div>
          </div>
        )}

        {/* Provider Comparison Radar */}
        {charts.provider_comparison_radar && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div style={{ height: '300px' }}>
              {renderChart('provider_comparison_radar', charts.provider_comparison_radar)}
            </div>
          </div>
        )}
      </div>

      {/* Full Width Charts */}
      <div className="space-y-6">
        {/* Timeline */}
        {charts.timeline && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div style={{ height: '300px' }}>
              {renderChart('timeline', charts.timeline)}
            </div>
          </div>
        )}

        {/* Section Completeness */}
        {charts.section_completeness && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div style={{ height: '400px' }}>
              {renderChart('section_completeness', charts.section_completeness)}
            </div>
          </div>
        )}
      </div>

      {/* Export Button */}
      <div className="flex justify-end">
        <button
          onClick={() => window.open('http://localhost:5001/api/analysis/export?format=csv', '_blank')}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Export as CSV
        </button>
      </div>
    </div>
  );
};

export default Analytics;