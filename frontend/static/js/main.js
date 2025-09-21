// frontend/static/js/main.js - Main Application Logic and UI Management

class CyberPatrolApp {
    constructor() {
        this.currentPage = 'dashboard';
        this.pagination = {
            telegram: { page: 0, limit: 50 },
            webpage: { page: 0, limit: 50 }
        };
        this.filters = {
            telegram: {},
            webpage: {}
        };
        
        this.initializeApp();
    }

    initializeApp() {
        // Wait for DOM and auth to be ready
        document.addEventListener('DOMContentLoaded', () => {
            this.setupEventListeners();
            this.initializeUI();
        });
    }

    setupEventListeners() {
        // Navigation event listeners are set up in the HTML onclick attributes
        // Filter change listeners
        const telegramRiskFilter = document.getElementById('telegramRiskFilter');
        if (telegramRiskFilter) {
            telegramRiskFilter.addEventListener('change', () => this.filterTelegramChannels());
        }

        const webpageRiskFilter = document.getElementById('webpageRiskFilter');
        if (webpageRiskFilter) {
            webpageRiskFilter.addEventListener('change', () => this.filterWebpages());
        }

        // Keyboard shortcuts
        document.addEventListener('keydown', (event) => {
            if (event.key === 'F5' || (event.ctrlKey && event.key === 'r')) {
                event.preventDefault();
                this.refreshCurrentView();
            }
        });
    }

    initializeUI() {
        // Set initial state
        this.currentPage = 'login';
    }

    // Navigation methods
    showDashboard() {
        this.hideAllSections();
        document.getElementById('dashboard-section').style.display = 'block';
        this.currentPage = 'dashboard';
        
        // Refresh dashboard data
        if (window.authManager && window.authManager.isAuthenticated()) {
            window.authManager.loadDashboardData();
        }
    }

    viewTelegramChannels() {
        this.hideAllSections();
        document.getElementById('telegram-view').style.display = 'block';
        this.currentPage = 'telegram';
        this.loadTelegramData();
    }

    viewWebpages() {
        this.hideAllSections();
        document.getElementById('webpage-view').style.display = 'block';
        this.currentPage = 'webpage';
        this.loadWebpageData();
    }

    hideAllSections() {
        const sections = ['login-section', 'dashboard-section', 'telegram-view', 'webpage-view'];
        sections.forEach(section => {
            document.getElementById(section).style.display = 'none';
        });
    }

    // Telegram data management
    async loadTelegramData(direction = null) {
        const container = document.getElementById('telegramData');
        const pagination = document.getElementById('telegramPagination');
        
        // Handle pagination
        if (direction === 'next') {
            this.pagination.telegram.page++;
        } else if (direction === 'prev') {
            this.pagination.telegram.page = Math.max(0, this.pagination.telegram.page - 1);
        } else if (direction !== 'refresh') {
            this.pagination.telegram.page = 0;
        }

        // Show loading
        window.apiHelpers.showLoading('telegramData');

        try {
            const params = {
                limit: this.pagination.telegram.limit,
                offset: this.pagination.telegram.page * this.pagination.telegram.limit,
                ...this.filters.telegram
            };

            const response = await window.apiClient.getTelegramChannels(params);
            
            // Update statistics
            this.updateTelegramStats(response.stats);
            
            // Update results info
            const resultsInfo = document.getElementById('telegramResultsInfo');
            if (resultsInfo) {
                const start = params.offset + 1;
                const end = Math.min(params.offset + response.channels.length, response.total_count);
                resultsInfo.textContent = `Showing ${start}-${end} of ${response.total_count} channels`;
            }

            // Render channels
            this.renderTelegramChannels(response.channels);
            
            // Update pagination
            this.updateTelegramPagination(response.total_count);

        } catch (error) {
            console.error('Error loading telegram data:', error);
            const errorMessage = window.apiHelpers.handleApiError(error, 'Failed to load Telegram channels');
            window.apiHelpers.showError('telegramData', errorMessage);
        }
    }

    updateTelegramStats(stats) {
        document.getElementById('telegramTotal').textContent = stats.total_flagged || 0;
        document.getElementById('telegramHigh').textContent = stats.high_risk || 0;
        document.getElementById('telegramMedium').textContent = stats.medium_risk || 0;
        document.getElementById('telegramToday').textContent = stats.found_today || 0;
    }

    renderTelegramChannels(channels) {
        const container = document.getElementById('telegramData');
        
        if (channels.length === 0) {
            window.apiHelpers.showEmpty('telegramData', 'No channels found matching your criteria');
            return;
        }

        container.innerHTML = channels.map(channel => `
            <div class="data-item" data-channel-id="${channel.id}">
                <div class="item-header">
                    <div class="item-title">@${channel.channel_username}</div>
                    <span class="risk-badge ${window.apiHelpers.getRiskClass(channel.avg_prob)}">
                        ${window.apiHelpers.getRiskLevel(channel.avg_prob)} Risk
                    </span>
                </div>
                <div class="item-details">
                    <div class="detail-group">
                        <span class="detail-label">Channel Title</span>
                        <span class="detail-value">${channel.channel_title || 'Unknown'}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Average Risk Score</span>
                        <span class="detail-value">${window.apiHelpers.formatRiskScore(channel.avg_prob)}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">90th Percentile</span>
                        <span class="detail-value">${window.apiHelpers.formatRiskScore(channel.pct90_prob)}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Messages Analyzed</span>
                        <span class="detail-value">${channel.sample_size}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">First Detected</span>
                        <span class="detail-value">${window.apiHelpers.formatDate(channel.first_seen)}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Time Ago</span>
                        <span class="detail-value">${window.apiHelpers.formatRelativeTime(channel.first_seen)}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateTelegramPagination(totalCount) {
        const pagination = document.getElementById('telegramPagination');
        const pageInfo = document.getElementById('telegramPageInfo');
        const prevBtn = document.getElementById('telegramPrevBtn');
        const nextBtn = document.getElementById('telegramNextBtn');

        if (totalCount <= this.pagination.telegram.limit) {
            pagination.style.display = 'none';
            return;
        }

        pagination.style.display = 'flex';
        
        const currentPage = this.pagination.telegram.page + 1;
        const totalPages = Math.ceil(totalCount / this.pagination.telegram.limit);
        
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        prevBtn.disabled = this.pagination.telegram.page === 0;
        nextBtn.disabled = this.pagination.telegram.page >= totalPages - 1;
    }

    filterTelegramChannels() {
        const riskFilter = document.getElementById('telegramRiskFilter').value;
        
        this.filters.telegram = {};
        if (riskFilter) {
            this.filters.telegram.risk_level = riskFilter;
        }
        
        this.loadTelegramData();
    }

    // Webpage data management
    async loadWebpageData(direction = null) {
        const container = document.getElementById('webpageData');
        
        // Handle pagination
        if (direction === 'next') {
            this.pagination.webpage.page++;
        } else if (direction === 'prev') {
            this.pagination.webpage.page = Math.max(0, this.pagination.webpage.page - 1);
        } else if (direction !== 'refresh') {
            this.pagination.webpage.page = 0;
        }

        // Show loading
        window.apiHelpers.showLoading('webpageData');

        try {
            const params = {
                limit: this.pagination.webpage.limit,
                offset: this.pagination.webpage.page * this.pagination.webpage.limit,
                ...this.filters.webpage
            };

            const response = await window.apiClient.getWebpages(params);
            
            // Update statistics
            this.updateWebpageStats(response.stats);
            
            // Update results info
            const resultsInfo = document.getElementById('webpageResultsInfo');
            if (resultsInfo) {
                const start = params.offset + 1;
                const end = Math.min(params.offset + response.pages.length, response.total_count);
                resultsInfo.textContent = `Showing ${start}-${end} of ${response.total_count} pages`;
            }

            // Render pages
            this.renderWebpages(response.pages);
            
            // Update pagination
            this.updateWebpagePagination(response.total_count);

        } catch (error) {
            console.error('Error loading webpage data:', error);
            const errorMessage = window.apiHelpers.handleApiError(error, 'Failed to load webpages');
            window.apiHelpers.showError('webpageData', errorMessage);
        }
    }

    updateWebpageStats(stats) {
        document.getElementById('webpageTotal').textContent = stats.total_flagged || 0;
        document.getElementById('webpageHigh').textContent = stats.high_risk || 0;
        document.getElementById('webpageMedium').textContent = stats.medium_risk || 0;
        document.getElementById('webpageToday').textContent = stats.found_today || 0;
    }

    renderWebpages(pages) {
        const container = document.getElementById('webpageData');
        
        if (pages.length === 0) {
            window.apiHelpers.showEmpty('webpageData', 'No webpages found matching your criteria');
            return;
        }

        container.innerHTML = pages.map(page => `
            <div class="data-item" data-page-id="${page.id}">
                <div class="item-header">
                    <div class="item-title">${window.apiHelpers.truncateText(page.url, 60)}</div>
                    <span class="risk-badge ${window.apiHelpers.getRiskClass(page.score)}">
                        ${window.apiHelpers.getRiskLevel(page.score)} Risk
                    </span>
                </div>
                <div class="item-details">
                    <div class="detail-group">
                        <span class="detail-label">Domain</span>
                        <span class="detail-value">${window.apiHelpers.extractDomain(page.url)}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Classification</span>
                        <span class="detail-value">${page.label.toUpperCase()}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Risk Score</span>
                        <span class="detail-value">${window.apiHelpers.formatRiskScore(page.score)}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Scraped At</span>
                        <span class="detail-value">${window.apiHelpers.formatDate(page.scraped_at)}</span>
                    </div>
                    <div class="detail-group">
                        <span class="detail-label">Time Ago</span>
                        <span class="detail-value">${window.apiHelpers.formatRelativeTime(page.scraped_at)}</span>
                    </div>
                    <div class="detail-group" style="grid-column: 1 / -1;">
                        <span class="detail-label">Content Preview</span>
                        <span class="detail-value snippet">${window.apiHelpers.truncateText(page.text_snippet, 200)}</span>
                    </div>
                    <div class="detail-group" style="grid-column: 1 / -1;">
                        <span class="detail-label">Full URL</span>
                        <span class="detail-value" style="word-break: break-all; font-family: monospace; font-size: 0.9em;">
                            <a href="${page.url}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-purple); text-decoration: none;">
                                ${page.url} ↗
                            </a>
                        </span>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateWebpagePagination(totalCount) {
        const pagination = document.getElementById('webpagePagination');
        const pageInfo = document.getElementById('webpagePageInfo');
        const prevBtn = document.getElementById('webpagePrevBtn');
        const nextBtn = document.getElementById('webpageNextBtn');

        if (totalCount <= this.pagination.webpage.limit) {
            pagination.style.display = 'none';
            return;
        }

        pagination.style.display = 'flex';
        
        const currentPage = this.pagination.webpage.page + 1;
        const totalPages = Math.ceil(totalCount / this.pagination.webpage.limit);
        
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        prevBtn.disabled = this.pagination.webpage.page === 0;
        nextBtn.disabled = this.pagination.webpage.page >= totalPages - 1;
    }

    filterWebpages() {
        const riskFilter = document.getElementById('webpageRiskFilter').value;
        
        this.filters.webpage = {};
        if (riskFilter) {
            this.filters.webpage.risk_level = riskFilter;
        }
        
        this.loadWebpageData();
    }

    // Utility methods
    refreshCurrentView() {
        switch (this.currentPage) {
            case 'dashboard':
                if (window.authManager && window.authManager.isAuthenticated()) {
                    window.authManager.loadDashboardData();
                }
                break;
            case 'telegram':
                this.loadTelegramData('refresh');
                break;
            case 'webpage':
                this.loadWebpageData('refresh');
                break;
        }
        
        showToast('Data refreshed', 'success');
    }

    refreshDashboard() {
        if (window.authManager && window.authManager.isAuthenticated()) {
            window.authManager.loadDashboardData();
            showToast('Dashboard data refreshed', 'success');
        }
    }
}

// Toast notification system
function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-header">
            <span class="toast-title">${getToastTitle(type)}</span>
            <button class="toast-close" onclick="this.parentElement.parentElement.remove()">&times;</button>
        </div>
        <div class="toast-message">${message}</div>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            if (toast.parentElement) {
                toast.remove();
            }
        }, duration);
    }
}

function getToastTitle(type) {
    switch (type) {
        case 'success': return 'Success';
        case 'error': return 'Error';
        case 'warning': return 'Warning';
        case 'info': return 'Info';
        default: return 'Notification';
    }
}

// Global loading overlay
function showGlobalLoading(message = 'Loading...') {
    const overlay = document.getElementById('loading-overlay');
    const messageElement = overlay.querySelector('p');
    messageElement.textContent = message;
    overlay.style.display = 'flex';
}

function hideGlobalLoading() {
    document.getElementById('loading-overlay').style.display = 'none';
}

// Initialize the app
window.cyberPatrolApp = new CyberPatrolApp();

// Global navigation functions (called from HTML)
window.showDashboard = () => window.cyberPatrolApp.showDashboard();
window.viewTelegramChannels = () => window.cyberPatrolApp.viewTelegramChannels();
window.viewWebpages = () => window.cyberPatrolApp.viewWebpages();
window.loadTelegramData = (direction) => window.cyberPatrolApp.loadTelegramData(direction);
window.loadWebpageData = (direction) => window.cyberPatrolApp.loadWebpageData(direction);
window.filterTelegramChannels = () => window.cyberPatrolApp.filterTelegramChannels();
window.filterWebpages = () => window.cyberPatrolApp.filterWebpages();
window.refreshDashboard = () => window.cyberPatrolApp.refreshDashboard();

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { CyberPatrolApp, showToast, showGlobalLoading, hideGlobalLoading };
}