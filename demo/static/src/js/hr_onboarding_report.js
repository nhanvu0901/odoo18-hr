import {registry} from "@web/core/registry";
import {Component, onMounted, useRef, onWillUnmount} from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
const Chart = window.Chart;

class HROnboardingReportAction extends Component {
    static template = "custom_hr_module.HROnboardingReportTemplate";

    setup() {
        this.action = useService("action");
        this.onboardingChartRef = useRef("onboardingChart");
        this.offboardingChartRef = useRef("offboardingChart");

        this.onboardingChartInstance = null;
        this.offboardingChartInstance = null;

        onMounted(() => {
            setTimeout(() => {
                this.renderCharts();
            }, 100);
        });

        onWillUnmount(() => {
            if (this.onboardingChartInstance) {
                this.onboardingChartInstance.destroy();
            }
            if (this.offboardingChartInstance) {
                this.offboardingChartInstance.destroy();
            }
        });
    }

    get reportData() {
        return this.props.action.context.report_data || {};
    }

    get departments() {
        return this.props.action.context.departments || [];
    }

    // Add these missing getters for the dates
    get date_from() {
        return this.props.action.context.date_from || '';
    }

    get date_to() {
        return this.props.action.context.date_to || '';
    }

    get employeeData() {
        return this.reportData.employee_data || [];
    }

    get onboardingStats() {
        return this.reportData.onboarding_stats || {};
    }

    get offboardingStats() {
        return this.reportData.offboarding_stats || {};
    }

    renderCharts() {
        if (this.onboardingChartRef.el) {
            this.renderPieChart(
                this.onboardingChartRef.el,
                this.onboardingStats,
                'Onboarding',
                'onboarding'
            );
        } else {
            console.error("❌ Onboarding canvas not found!");
        }

        if (this.offboardingChartRef.el) {
            this.renderPieChart(
                this.offboardingChartRef.el,
                this.offboardingStats,
                'Offboarding',
                'offboarding'
            );
        } else {
            console.error("❌ Offboarding canvas not found!");
        }
    }

    renderPieChart(canvas, data, title, chartType) {
        try {
            const ctx = canvas.getContext('2d');

            if (chartType === 'onboarding' && this.onboardingChartInstance) {
                this.onboardingChartInstance.destroy();
            }
            if (chartType === 'offboarding' && this.offboardingChartInstance) {
                this.offboardingChartInstance.destroy();
            }

            const total = Object.values(data).reduce((sum, val) => sum + val, 0);

            if (total === 0) {
                const emptyChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['No Data'],
                        datasets: [{
                            data: [1],
                            backgroundColor: ['#E5E5E5'],
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: false
                            },
                            tooltip: {
                                enabled: false
                            }
                        }
                    }
                });

                if (chartType === 'onboarding') {
                    this.onboardingChartInstance = emptyChart;
                } else {
                    this.offboardingChartInstance = emptyChart;
                }

                console.log(`⚠️ No data for ${title}, showing empty chart`);
                return;
            }

            const labels = Object.keys(data);
            const values = Object.values(data);
            const colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                '#9966FF', '#FF9F40', '#FF9F7F', '#8FBC8F'
            ];

            const chartConfig = {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: values,
                        backgroundColor: colors.slice(0, labels.length),
                        borderColor: '#ffffff',
                        borderWidth: 2,
                        hoverOffset: 4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        title: {
                            display: true,
                            text: `${title} Statistics`,
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: 20
                        },
                        legend: {
                            position: 'right',
                            labels: {
                                usePointStyle: true,
                                pointStyle: 'circle',
                                padding: 15,
                                font: {
                                    size: 12
                                },
                                generateLabels: function (chart) {
                                    const data = chart.data;
                                    if (data.labels.length && data.datasets.length) {
                                        return data.labels.map((label, i) => {
                                            const value = data.datasets[0].data[i];
                                            const percentage = ((value / total) * 100).toFixed(1);
                                            return {
                                                text: `${label}: ${value} (${percentage}%)`,
                                                fillStyle: data.datasets[0].backgroundColor[i],
                                                hidden: false,
                                                index: i
                                            };
                                        });
                                    }
                                    return [];
                                }
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function (context) {
                                    const label = context.label || '';
                                    const value = context.parsed;
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    animation: {
                        animateRotate: true,
                        animateScale: true,
                        duration: 1000
                    }
                }
            };

            const chartInstance = new Chart(ctx, chartConfig);

            if (chartType === 'onboarding') {
                this.onboardingChartInstance = chartInstance;
            } else {
                this.offboardingChartInstance = chartInstance;
            }
        } catch (error) {
            console.error(`❌ Error rendering ${title} chart:`, error);
        }
    }

    openWizardForm() {
        this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'HR Onboarding/Offboarding Report',
            res_model: 'hr.onboarding.report',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {}
        });
    }
}

registry.category("actions").add("hr_onboarding_report_action", HROnboardingReportAction);