"""Professional reporting system for 3D printing analysis and results."""

import json
import base64
from io import BytesIO
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
from pathlib import Path
import uuid

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import trimesh
from jinja2 import Template
import pdfkit
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart

class ReportType(Enum):
    """Types of reports that can be generated."""
    PRINT_ANALYSIS = "print_analysis"
    QUALITY_ASSESSMENT = "quality_assessment"
    SIMULATION_RESULTS = "simulation_results"
    MATERIAL_COMPARISON = "material_comparison"
    COST_ANALYSIS = "cost_analysis"
    BATCH_SUMMARY = "batch_summary"
    FAILURE_ANALYSIS = "failure_analysis"
    OPTIMIZATION_RECOMMENDATIONS = "optimization_recommendations"

class ReportFormat(Enum):
    """Supported report output formats."""
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    EXCEL = "xlsx"

@dataclass
class ReportMetadata:
    """Report metadata and configuration."""
    id: str
    title: str
    subtitle: str
    report_type: ReportType
    format: ReportFormat
    author: str
    organization: str
    generated_at: datetime
    version: str = "1.0"
    template: str = "default"
    include_charts: bool = True
    include_3d_views: bool = True
    include_raw_data: bool = False
    page_orientation: str = "portrait"  # portrait, landscape
    logo_path: Optional[str] = None

@dataclass
class ReportSection:
    """Individual report section."""
    id: str
    title: str
    content: str
    data: Dict[str, Any]
    charts: List[Dict] = None
    images: List[str] = None
    order: int = 0
    page_break: bool = False

    def __post_init__(self):
        if self.charts is None:
            self.charts = []
        if self.images is None:
            self.images = []

@dataclass
class PrintJob:
    """Print job data for reporting."""
    id: str
    name: str
    file_path: str
    material: str
    printer: str
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    quality_score: float
    success: bool
    print_time: float  # minutes
    material_used: float  # grams
    cost: float  # currency units
    settings: Dict[str, Any]
    defects: List[Dict] = None
    measurements: Dict[str, float] = None

    def __post_init__(self):
        if self.defects is None:
            self.defects = []
        if self.measurements is None:
            self.measurements = {}

class ChartGenerator:
    """Generate charts and visualizations for reports."""

    def __init__(self):
        self.figure_size = (10, 6)
        self.dpi = 300
        self.style = 'seaborn-v0_8'
        plt.style.use('seaborn-v0_8')

    def create_quality_trend_chart(self, jobs: List[PrintJob]) -> str:
        """Create quality trend chart over time."""

        if not jobs:
            return ""

        # Sort jobs by start time
        sorted_jobs = sorted(jobs, key=lambda x: x.start_time)

        dates = [job.start_time for job in sorted_jobs]
        quality_scores = [job.quality_score for job in sorted_jobs]

        fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)

        ax.plot(dates, quality_scores, marker='o', linewidth=2, markersize=6)
        ax.set_title('Print Quality Trend Over Time', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Quality Score', fontsize=12)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 1)

        # Add trend line
        if len(quality_scores) > 1:
            x_numeric = np.arange(len(dates))
            z = np.polyfit(x_numeric, quality_scores, 1)
            p = np.poly1d(z)
            ax.plot(dates, p(x_numeric), "--", alpha=0.7, color='red', label='Trend')
            ax.legend()

        plt.xticks(rotation=45)
        plt.tight_layout()

        # Save to base64 string
        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return image_base64

    def create_material_usage_chart(self, jobs: List[PrintJob]) -> str:
        """Create material usage breakdown chart."""

        if not jobs:
            return ""

        # Group by material
        material_usage = {}
        for job in jobs:
            material = job.material
            if material not in material_usage:
                material_usage[material] = 0
            material_usage[material] += job.material_used

        materials = list(material_usage.keys())
        usage = list(material_usage.values())

        fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)

        colors_list = plt.cm.Set3(np.linspace(0, 1, len(materials)))
        wedges, texts, autotexts = ax.pie(usage, labels=materials, autopct='%1.1f%%',
                                         colors=colors_list, startangle=90)

        ax.set_title('Material Usage Distribution', fontsize=16, fontweight='bold')

        # Enhance text appearance
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return image_base64

    def create_success_rate_chart(self, jobs: List[PrintJob]) -> str:
        """Create success rate chart."""

        if not jobs:
            return ""

        successful = sum(1 for job in jobs if job.success)
        failed = len(jobs) - successful

        fig, ax = plt.subplots(figsize=(8, 8), dpi=self.dpi)

        sizes = [successful, failed]
        labels = [f'Successful ({successful})', f'Failed ({failed})']
        colors = ['#2ecc71', '#e74c3c']

        wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                         colors=colors, startangle=90)

        ax.set_title('Print Success Rate', fontsize=16, fontweight='bold')

        # Calculate success rate
        success_rate = (successful / len(jobs)) * 100 if jobs else 0
        ax.text(0, -1.3, f'Overall Success Rate: {success_rate:.1f}%',
                ha='center', fontsize=14, fontweight='bold')

        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return image_base64

    def create_print_time_distribution(self, jobs: List[PrintJob]) -> str:
        """Create print time distribution histogram."""

        if not jobs:
            return ""

        print_times = [job.print_time / 60 for job in jobs]  # Convert to hours

        fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)

        n, bins, patches = ax.hist(print_times, bins=20, alpha=0.7, color='skyblue', edgecolor='black')

        ax.set_title('Print Time Distribution', fontsize=16, fontweight='bold')
        ax.set_xlabel('Print Time (hours)', fontsize=12)
        ax.set_ylabel('Number of Prints', fontsize=12)
        ax.grid(True, alpha=0.3)

        # Add statistics
        mean_time = np.mean(print_times)
        median_time = np.median(print_times)

        ax.axvline(mean_time, color='red', linestyle='--', linewidth=2, label=f'Mean: {mean_time:.1f}h')
        ax.axvline(median_time, color='green', linestyle='--', linewidth=2, label=f'Median: {median_time:.1f}h')
        ax.legend()

        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return image_base64

    def create_cost_analysis_chart(self, jobs: List[PrintJob]) -> str:
        """Create cost analysis chart."""

        if not jobs:
            return ""

        # Group by date for cost trends
        daily_costs = {}
        for job in jobs:
            date = job.start_time.date()
            if date not in daily_costs:
                daily_costs[date] = 0
            daily_costs[date] += job.cost

        dates = sorted(daily_costs.keys())
        costs = [daily_costs[date] for date in dates]

        fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)

        ax.bar(dates, costs, alpha=0.7, color='green', edgecolor='darkgreen')
        ax.set_title('Daily Print Costs', fontsize=16, fontweight='bold')
        ax.set_xlabel('Date', fontsize=12)
        ax.set_ylabel('Cost ($)', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        # Add total cost annotation
        total_cost = sum(costs)
        ax.text(0.02, 0.98, f'Total Cost: ${total_cost:.2f}',
                transform=ax.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
                fontsize=12, fontweight='bold')

        plt.xticks(rotation=45)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return image_base64

    def create_defect_analysis_chart(self, jobs: List[PrintJob]) -> str:
        """Create defect type analysis chart."""

        if not jobs:
            return ""

        # Count defect types
        defect_counts = {}
        for job in jobs:
            for defect in job.defects:
                defect_type = defect.get('type', 'Unknown')
                if defect_type not in defect_counts:
                    defect_counts[defect_type] = 0
                defect_counts[defect_type] += 1

        if not defect_counts:
            return ""

        defect_types = list(defect_counts.keys())
        counts = list(defect_counts.values())

        fig, ax = plt.subplots(figsize=self.figure_size, dpi=self.dpi)

        bars = ax.bar(defect_types, counts, alpha=0.7, color='coral', edgecolor='darkred')
        ax.set_title('Defect Type Distribution', fontsize=16, fontweight='bold')
        ax.set_xlabel('Defect Type', fontsize=12)
        ax.set_ylabel('Occurrence Count', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{int(height)}', ha='center', va='bottom', fontweight='bold')

        plt.xticks(rotation=45)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()

        return image_base64

class ReportGenerator:
    """Professional report generation system."""

    def __init__(self):
        self.chart_generator = ChartGenerator()
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load report templates."""

        html_template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ metadata.title }}</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 1200px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                }
                .header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .header h1 {
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 300;
                }
                .header .subtitle {
                    margin: 10px 0 0 0;
                    font-size: 1.2em;
                    opacity: 0.9;
                }
                .metadata {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin-bottom: 30px;
                }
                .metadata-item {
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .metadata-item strong {
                    color: #667eea;
                }
                .section {
                    background: white;
                    margin-bottom: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    overflow: hidden;
                }
                .section-header {
                    background: #667eea;
                    color: white;
                    padding: 20px;
                    font-size: 1.4em;
                    font-weight: 600;
                }
                .section-content {
                    padding: 30px;
                }
                .chart-container {
                    text-align: center;
                    margin: 20px 0;
                }
                .chart-container img {
                    max-width: 100%;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                }
                .data-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                .data-table th,
                .data-table td {
                    padding: 12px;
                    text-align: left;
                    border-bottom: 1px solid #ddd;
                }
                .data-table th {
                    background-color: #f8f9fa;
                    font-weight: 600;
                    color: #495057;
                }
                .data-table tr:hover {
                    background-color: #f8f9fa;
                }
                .summary-stats {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin: 30px 0;
                }
                .stat-card {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 10px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }
                .stat-value {
                    font-size: 2.5em;
                    font-weight: 300;
                    margin-bottom: 5px;
                }
                .stat-label {
                    font-size: 0.9em;
                    opacity: 0.9;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }
                .footer {
                    text-align: center;
                    padding: 30px;
                    color: #666;
                    border-top: 1px solid #eee;
                    margin-top: 40px;
                }
                @media print {
                    body { background-color: white; }
                    </div>
{{ ... }}
                    <div class="metadata-item">
                        <strong>Organization:</strong> {{ metadata.organization }}
                    </div>
                </div>
            {% endfor %}

            <div class="footer">
                <p>Generated by 3D Print CAD Professional | Version {{ metadata.version }}</p>
            </div>
        </body>
        </html>
        """

        return {
            "html": html_template
        }

    def generate_print_analysis_report(self, jobs: List[PrintJob],
                                     metadata: ReportMetadata) -> str:
        """Generate comprehensive print analysis report."""

        sections = []

        # Executive Summary
        total_jobs = len(jobs)
        successful_jobs = sum(1 for job in jobs if job.success)
        success_rate = (successful_jobs / total_jobs * 100) if total_jobs > 0 else 0
        avg_quality = np.mean([job.quality_score for job in jobs]) if jobs else 0
        total_time = sum(job.print_time for job in jobs) / 60  # hours
        total_cost = sum(job.cost for job in jobs)
        total_material = sum(job.material_used for job in jobs)

        summary_content = f"""
        <div class="summary-stats">
            <div class="stat-card">
                <div class="stat-value">{total_jobs}</div>
                <div class="stat-label">Total Prints</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{success_rate:.1f}%</div>
                <div class="stat-label">Success Rate</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{avg_quality:.2f}</div>
                <div class="stat-label">Avg Quality</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_time:.1f}h</div>
                <div class="stat-label">Total Time</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${total_cost:.2f}</div>
                <div class="stat-label">Total Cost</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{total_material:.1f}g</div>
                <div class="stat-label">Material Used</div>
            </div>
        </div>

        <h3>Key Insights</h3>
        <ul>
            <li>Processed {total_jobs} print jobs with {success_rate:.1f}% success rate</li>
            <li>Average print quality score: {avg_quality:.2f}/1.0</li>
            <li>Total printing time: {total_time:.1f} hours</li>
            <li>Total material consumption: {total_material:.1f} grams</li>
            <li>Total project cost: ${total_cost:.2f}</li>
        </ul>
        """

        sections.append(ReportSection(
            id="summary",
            title="Executive Summary",
            content=summary_content,
            data={},
            order=1
        ))

        # Quality Analysis
        quality_chart = self.chart_generator.create_quality_trend_chart(jobs)
        success_chart = self.chart_generator.create_success_rate_chart(jobs)

        quality_content = """
        <h3>Quality Metrics</h3>
        <p>Analysis of print quality trends and success rates over time.</p>
        """

        sections.append(ReportSection(
            id="quality",
            title="Quality Analysis",
            content=quality_content,
            data={},
            charts=[quality_chart, success_chart],
            order=2
        ))

        # Material and Cost Analysis
        material_chart = self.chart_generator.create_material_usage_chart(jobs)
        cost_chart = self.chart_generator.create_cost_analysis_chart(jobs)

        material_content = """
        <h3>Resource Utilization</h3>
        <p>Breakdown of material usage and cost distribution across all prints.</p>
        """

        sections.append(ReportSection(
            id="materials",
            title="Material & Cost Analysis",
            content=material_content,
            data={},
            charts=[material_chart, cost_chart],
            order=3
        ))

        # Performance Analysis
        time_chart = self.chart_generator.create_print_time_distribution(jobs)

        performance_content = f"""
        <h3>Performance Metrics</h3>
        <p>Analysis of print time distribution and performance characteristics.</p>

        <h4>Time Statistics</h4>
        <ul>
            <li>Average print time: {np.mean([job.print_time for job in jobs]) / 60:.1f} hours</li>
            <li>Shortest print: {min(job.print_time for job in jobs) / 60:.1f} hours</li>
            <li>Longest print: {max(job.print_time for job in jobs) / 60:.1f} hours</li>
            <li>Total machine time: {total_time:.1f} hours</li>
        </ul>
        """

        sections.append(ReportSection(
            id="performance",
            title="Performance Analysis",
            content=performance_content,
            data={},
            charts=[time_chart],
            order=4
        ))

        # Defect Analysis
        defect_chart = self.chart_generator.create_defect_analysis_chart(jobs)

        defect_summary = {}
        for job in jobs:
            for defect in job.defects:
                defect_type = defect.get('type', 'Unknown')
                if defect_type not in defect_summary:
                    defect_summary[defect_type] = {'count': 0, 'total_severity': 0}
                defect_summary[defect_type]['count'] += 1
                defect_summary[defect_type]['total_severity'] += defect.get('severity', 0)

        defect_content = """
        <h3>Defect Analysis</h3>
        <p>Comprehensive analysis of print defects and failure modes.</p>
        """

        if defect_summary:
            defect_content += "<h4>Defect Summary</h4><ul>"
            for defect_type, data in defect_summary.items():
                avg_severity = data['total_severity'] / data['count']
                defect_content += f"<li>{defect_type}: {data['count']} occurrences (avg severity: {avg_severity:.2f})</li>"
            defect_content += "</ul>"

        sections.append(ReportSection(
            id="defects",
            title="Defect Analysis",
            content=defect_content,
            data=defect_summary,
            charts=[defect_chart] if defect_chart else [],
            order=5
        ))

        # Detailed Job List
        jobs_table = self._create_jobs_table(jobs)

        sections.append(ReportSection(
            id="jobs",
            title="Detailed Job List",
            content=jobs_table,
            data={},
            order=6
        ))

        return self._render_html_report(metadata, sections)

    def generate_quality_assessment_report(self, analysis_results: Dict,
                                         metadata: ReportMetadata) -> str:
        """Generate quality assessment report."""

        sections = []

        # Quality Overview
        overview_content = """
        <h3>Quality Assessment Summary</h3>
        <p>Comprehensive quality analysis results and recommendations.</p>
        """

        sections.append(ReportSection(
            id="overview",
            title="Quality Overview",
            content=overview_content,
            data=analysis_results,
            order=1
        ))

        return self._render_html_report(metadata, sections)

    def generate_simulation_report(self, simulation_results: Dict,
                                 metadata: ReportMetadata) -> str:
        """Generate simulation results report."""

        sections = []

        # Simulation Summary
        summary_content = """
        <h3>Simulation Results Summary</h3>
        <p>Results from comprehensive 3D print simulation analysis.</p>
        """

        # Add simulation result details
        for sim_type, result in simulation_results.items():
            summary_content += f"""
            <h4>{sim_type.value.replace('_', ' ').title()}</h4>
            <ul>
                <li>Success Probability: {result.success_probability:.1%}</li>
                <li>Quality Score: {result.quality_score:.2f}</li>
                <li>Predicted Defects: {len(result.predicted_defects)}</li>
                <li>Simulation Time: {result.simulation_time:.2f} seconds</li>
            </ul>
            """

        sections.append(ReportSection(
            id="simulation",
            title="Simulation Results",
            content=summary_content,
            data=simulation_results,
            order=1
        ))

        return self._render_html_report(metadata, sections)

    def _create_jobs_table(self, jobs: List[PrintJob]) -> str:
        """Create HTML table of job details."""

        if not jobs:
            return "<p>No jobs to display.</p>"

        table_html = """
        <table class="data-table">
            <thead>
                <tr>
                    <th>Job Name</th>
                    <th>Material</th>
                    <th>Printer</th>
                    <th>Start Time</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Quality</th>
                    <th>Cost</th>
                </tr>
            </thead>
            <tbody>
        """

        for job in jobs:
            duration = f"{job.print_time/60:.1f}h"
            status_color = "green" if job.success else "red"
            status_text = "Success" if job.success else "Failed"

            table_html += f"""
                <tr>
                    <td>{job.name}</td>
                    <td>{job.material}</td>
                    <td>{job.printer}</td>
                    <td>{job.start_time.strftime('%Y-%m-%d %H:%M')}</td>
                    <td>{duration}</td>
                    <td style="color: {status_color}; font-weight: bold;">{status_text}</td>
                    <td>{job.quality_score:.2f}</td>
                    <td>${job.cost:.2f}</td>
                </tr>
            """

        table_html += """
            </tbody>
        </table>
        """

        return table_html

    def _render_html_report(self, metadata: ReportMetadata,
                           sections: List[ReportSection]) -> str:
        """Render HTML report from template."""

        # Sort sections by order
        sections.sort(key=lambda x: x.order)

        template = Template(self.templates["html"])
        return template.render(metadata=metadata, sections=sections)

    def export_to_pdf(self, html_content: str, output_path: str,
                     options: Dict = None) -> bool:
        """Export HTML report to PDF."""

        try:
            default_options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'enable-local-file-access': None
            }

            if options:
                default_options.update(options)

            pdfkit.from_string(html_content, output_path, options=default_options)
            return True

        except Exception as e:
            print(f"PDF export error: {e}")
            return False

    def export_to_json(self, data: Dict, output_path: str) -> bool:
        """Export report data to JSON."""

        try:
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            return True

        except Exception as e:
            print(f"JSON export error: {e}")
            return False

    def create_batch_report(self, jobs: List[PrintJob], title: str,
                          organization: str = "3D Print CAD") -> str:
        """Create a comprehensive batch report."""

        metadata = ReportMetadata(
            id=str(uuid.uuid4()),
            title=title,
            subtitle=f"Analysis of {len(jobs)} print jobs",
            report_type=ReportType.BATCH_SUMMARY,
            format=ReportFormat.HTML,
            author="System",
            organization=organization,
            generated_at=datetime.now()
        )

        return self.generate_print_analysis_report(jobs, metadata)