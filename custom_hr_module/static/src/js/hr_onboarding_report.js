import {registry} from "@web/core/registry";
import {Component, onMounted, useRef, onWillUnmount, useState} from "@odoo/owl";
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

        this.state = useState({
            currentReportType: 'onboarding',
            reportData: {},
            date_from: '',
            date_to: '',
            departments: [],
            isDataLoaded: false,
            isFromCache: false
        });

        onMounted(() => {
            this.initializeReportData();
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

    initializeReportData() {
        const contextData = this.props.action.context.report_data;

        if (contextData && Object.keys(contextData).length > 0) {
            this.updateStateFromContext();
            this.saveReportDataToLocalStorage();
        }
        else {
            console.log("📂 No context data, attempting to load from localStorage");
            this.loadReportDataFromLocalStorage();
        }
    }

    updateStateFromContext() {
        this.state.reportData = this.props.action.context.report_data || {};
        this.state.date_from = this.props.action.context.date_from || '';
        this.state.date_to = this.props.action.context.date_to || '';
        this.state.departments = this.props.action.context.departments || [];
        this.state.isDataLoaded = true;
        this.state.isFromCache = false;
    }

    saveReportDataToLocalStorage() {
        try {
            const reportData = {
                report_data: this.state.reportData,
                date_from: this.state.date_from,
                date_to: this.state.date_to,
                departments: this.state.departments,
                timestamp: Date.now()
            };

            localStorage.setItem('hr_onboarding_report_data', JSON.stringify(reportData));
        } catch (error) {
            console.error("❌ Error saving to localStorage:", error);
        }
    }

    loadReportDataFromLocalStorage() {
        try {
            const storedData = localStorage.getItem('hr_onboarding_report_data');

            if (storedData) {
                const parsedData = JSON.parse(storedData);
                console.log("📂 Found stored data:", parsedData);

                const dataAge = Date.now() - (parsedData.timestamp || 0);
                const maxAge = 86400000; // 24 hours in milliseconds

                if (dataAge < maxAge) {
                    this.state.reportData = parsedData.report_data || {};
                    this.state.date_from = parsedData.date_from || '';
                    this.state.date_to = parsedData.date_to || '';
                    this.state.departments = parsedData.departments || [];
                    this.state.isDataLoaded = true;
                    this.state.isFromCache = true;
                } else {
                    localStorage.removeItem('hr_onboarding_report_data');
                    this.state.isDataLoaded = false;
                }
            } else {
                this.state.isDataLoaded = false;
            }
        } catch (error) {
            localStorage.removeItem('hr_onboarding_report_data');
            this.state.isDataLoaded = false;
        }
    }

    get reportData() {
        return this.state.reportData;
    }

    get departments() {
        return this.state.departments;
    }

    get date_from() {
        return this.state.date_from;
    }

    get date_to() {
        return this.state.date_to;
    }

    get currentReportType() {
        return this.state.currentReportType;
    }

    get onboardingStats() {
        return this.reportData.onboarding_stats || {};
    }

    get offboardingStats() {
        return this.reportData.offboarding_stats || {};
    }

    get onboardingEmployees() {
        return this.reportData.onboarding_employees || [];
    }

    get offboardingEmployees() {
        return this.reportData.offboarding_employees || [];
    }

    get currentEmployeeData() {
        return this.currentReportType === 'onboarding' ? this.onboardingEmployees : this.offboardingEmployees;
    }

    get hasData() {
        const data = this.reportData;
        if (!data || Object.keys(data).length === 0) {
            return false;
        }

        const hasOnboardingData = data.onboarding_stats && Object.keys(data.onboarding_stats).length > 0;
        const hasOffboardingData = data.offboarding_stats && Object.keys(data.offboarding_stats).length > 0;
        const hasOnboardingEmployees = data.onboarding_employees && data.onboarding_employees.length > 0;
        const hasOffboardingEmployees = data.offboarding_employees && data.offboarding_employees.length > 0;

        return hasOnboardingData || hasOffboardingData || hasOnboardingEmployees || hasOffboardingEmployees;
    }

    get isFromCache() {
        return this.state.isFromCache;
    }

    switchReportType(event) {
        this.state.currentReportType = event.target.value;
    }

    renderCharts() {
        // Only render charts if we have data
        if (!this.hasData) {
            console.log("⚠️ No data available for charts");
            return;
        }

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
                'Departure',
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
                            text: `${title} Insight`,
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
            name: 'Employee Trend',
            res_model: 'hr.onboarding.report',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {}
        });
    }
}

registry.category("actions").add("hr_onboarding_report_action", HROnboardingReportAction);