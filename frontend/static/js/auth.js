// frontend/static/js/auth.js - Authentication and User Management

class AuthManager {
    constructor() {
        this.currentUser = null;
        this.loginForm = null;
        this.initializeAuth();
    }

    initializeAuth() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.setupEventListeners());
        } else {
            this.setupEventListeners();
        }
    }

    setupEventListeners() {
        // Setup login form
        this.loginForm = document.getElementById('loginForm');
        if (this.loginForm) {
            this.loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        }

        // Setup remember me functionality
        const rememberMeCheckbox = document.getElementById('rememberMe');
        if (rememberMeCheckbox) {
            // Load saved username if remember me was checked
            const savedUsername = localStorage.getItem('remembered_username');
            if (savedUsername) {
                document.getElementById('username').value = savedUsername;
                rememberMeCheckbox.checked = true;
            }
        }

        // Auto-focus on username field
        const usernameField = document.getElementById('username');
        if (usernameField && document.getElementById('login-section').style.display !== 'none') {
            usernameField.focus();
        }

        // Check if user is already authenticated
        this.checkExistingAuth();
    }

    async checkExistingAuth() {
        if (!window.apiClient.token) {
            return;
        }

        try {
            showGlobalLoading('Checking authentication...');
            const user = await window.apiClient.getCurrentUser();
            this.setCurrentUser(user);
            this.showDashboard();
        } catch (error) {
            console.log('Authentication check failed:', error);
            this.clearAuth();
        } finally {
            hideGlobalLoading();
        }
    }

    async handleLogin(event) {
        event.preventDefault();
        
        const formData = new FormData(this.loginForm);
        const credentials = {
            username: formData.get('username').trim(),
            password: formData.get('password')
        };

        // Validation
        if (!credentials.username || !credentials.password) {
            showToast('Please enter both username and password', 'error');
            return;
        }

        // Show loading state
        this.setLoginLoading(true);

        try {
            const response = await window.apiClient.login(credentials);
            
            // Handle remember me
            const rememberMe = document.getElementById('rememberMe').checked;
            if (rememberMe) {
                localStorage.setItem('remembered_username', credentials.username);
            } else {
                localStorage.removeItem('remembered_username');
            }

            // Set user data
            this.setCurrentUser(response.user_info);
            
            // Show success message and redirect to dashboard
            showToast(`Welcome back, ${response.user_info.full_name}!`, 'success');
            
            setTimeout(() => {
                this.showDashboard();
                this.loadDashboardData();
            }, 500);

        } catch (error) {
            const errorMessage = window.apiHelpers.handleApiError(error, 'Login failed. Please check your credentials.');
            showToast(errorMessage, 'error');
            
            // Clear password field
            document.getElementById('password').value = '';
            document.getElementById('password').focus();
        } finally {
            this.setLoginLoading(false);
        }
    }

    setLoginLoading(loading) {
        const loginBtn = document.getElementById('loginBtn');
        const btnText = loginBtn.querySelector('.btn-text');
        const btnLoader = loginBtn.querySelector('.btn-loader');

        if (loading) {
            loginBtn.disabled = true;
            btnText.style.display = 'none';
            btnLoader.style.display = 'block';
        } else {
            loginBtn.disabled = false;
            btnText.style.display = 'block';
            btnLoader.style.display = 'none';
        }
    }

    setCurrentUser(user) {
        this.currentUser = user;
        
        // Update UI with user info
        if (user) {
            document.getElementById('officerName').textContent = user.full_name;
            document.getElementById('officerRole').textContent = user.role;
            document.getElementById('officerBadge').textContent = user.badge_number;
        }
    }

    showDashboard() {
        // Hide all sections
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('telegram-view').style.display = 'none';
        document.getElementById('webpage-view').style.display = 'none';
        
        // Show dashboard
        document.getElementById('dashboard-section').style.display = 'block';
    }

    async loadDashboardData() {
        try {
            // Load summary statistics for dashboard cards
            const [telegramStats, webpageStats] = await Promise.allSettled([
                window.apiClient.getTelegramStats(),
                window.apiClient.getWebpageStats()
            ]);

            // Update dashboard stats
            if (telegramStats.status === 'fulfilled') {
                const stats = telegramStats.value;
                document.getElementById('dashTelegramCount').textContent = stats.total_flagged || 0;
                document.getElementById('telegramBadge').textContent = stats.total_flagged || 0;
            }

            if (webpageStats.status === 'fulfilled') {
                const stats = webpageStats.value;
                document.getElementById('dashWebpageCount').textContent = stats.total_flagged || 0;
                document.getElementById('webpageBadge').textContent = stats.total_flagged || 0;
            }

            // Calculate combined high risk and today counts
            let totalHighRisk = 0;
            let totalToday = 0;

            if (telegramStats.status === 'fulfilled') {
                totalHighRisk += telegramStats.value.high_risk || 0;
                totalToday += telegramStats.value.found_today || 0;
            }

            if (webpageStats.status === 'fulfilled') {
                totalHighRisk += webpageStats.value.high_risk || 0;
                totalToday += webpageStats.value.found_today || 0;
            }

            document.getElementById('dashHighRiskCount').textContent = totalHighRisk;
            document.getElementById('dashTodayCount').textContent = totalToday;

            // Load recent activity
            this.loadRecentActivity();

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            showToast('Some dashboard data could not be loaded', 'warning');
        }
    }

    async loadRecentActivity() {
        const activityContainer = document.getElementById('recentActivity');
        
        try {
            // Get recent data from both sources
            const [telegramData, webpageData] = await Promise.allSettled([
                window.apiClient.getTelegramChannels({ limit: 5 }),
                window.apiClient.getWebpages({ limit: 5 })
            ]);

            const recentItems = [];

            // Combine recent items
            if (telegramData.status === 'fulfilled') {
                telegramData.value.channels.slice(0, 3).forEach(channel => {
                    recentItems.push({
                        type: 'telegram',
                        title: `@${channel.channel_username}`,
                        subtitle: channel.channel_title,
                        risk: channel.avg_prob,
                        time: channel.first_seen,
                        icon: '📱'
                    });
                });
            }

            if (webpageData.status === 'fulfilled') {
                webpageData.value.pages.slice(0, 3).forEach(page => {
                    recentItems.push({
                        type: 'webpage',
                        title: window.apiHelpers.extractDomain(page.url),
                        subtitle: window.apiHelpers.truncateText(page.text_snippet, 50),
                        risk: page.score,
                        time: page.scraped_at,
                        icon: '🌐'
                    });
                });
            }

            // Sort by time (most recent first)
            recentItems.sort((a, b) => new Date(b.time) - new Date(a.time));

            // Display recent items
            if (recentItems.length === 0) {
                activityContainer.innerHTML = `
                    <div class="activity-item">
                        <div style="text-align: center; color: var(--text-medium);">
                            No recent activity to display
                        </div>
                    </div>
                `;
            } else {
                activityContainer.innerHTML = recentItems.slice(0, 5).map(item => `
                    <div class="activity-item">
                        <div style="display: flex; align-items: center; gap: 15px;">
                            <span style="font-size: 1.5em;">${item.icon}</span>
                            <div style="flex: 1;">
                                <div style="font-weight: 600; color: var(--text-dark);">
                                    ${item.title}
                                </div>
                                <div style="font-size: 0.9em; color: var(--text-medium); margin-top: 2px;">
                                    ${item.subtitle}
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <span class="risk-badge ${window.apiHelpers.getRiskClass(item.risk)}" style="font-size: 0.8em; padding: 4px 8px;">
                                    ${window.apiHelpers.getRiskLevel(item.risk)}
                                </span>
                                <div style="font-size: 0.8em; color: var(--text-light); margin-top: 5px;">
                                    ${window.apiHelpers.formatRelativeTime(item.time)}
                                </div>
                            </div>
                        </div>
                    </div>
                `).join('');
            }

        } catch (error) {
            console.error('Error loading recent activity:', error);
            activityContainer.innerHTML = `
                <div class="activity-item">
                    <div style="text-align: center; color: var(--text-medium);">
                        Unable to load recent activity
                    </div>
                </div>
            `;
        }
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            this.performLogout();
        }
    }

    async performLogout() {
        try {
            showGlobalLoading('Logging out...');
            await window.apiClient.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            this.clearAuth();
            this.showLoginScreen();
            showToast('You have been logged out successfully', 'info');
            hideGlobalLoading();
        }
    }

    clearAuth() {
        this.currentUser = null;
        window.apiClient.setToken(null);
        
        // Clear form data
        if (this.loginForm) {
            this.loginForm.reset();
        }
    }

    showLoginScreen() {
        // Hide all sections
        document.getElementById('dashboard-section').style.display = 'none';
        document.getElementById('telegram-view').style.display = 'none';
        document.getElementById('webpage-view').style.display = 'none';
        
        // Show login
        document.getElementById('login-section').style.display = 'block';
        
        // Focus on username field
        setTimeout(() => {
            const usernameField = document.getElementById('username');
            if (usernameField) {
                usernameField.focus();
            }
        }, 100);
    }

    // Public method to check if user is authenticated
    isAuthenticated() {
        return this.currentUser !== null && window.apiClient.token !== null;
    }

    // Public method to get current user
    getCurrentUser() {
        return this.currentUser;
    }

    // Public method to refresh user data
    async refreshUserData() {
        if (!this.isAuthenticated()) return null;
        
        try {
            const user = await window.apiClient.getCurrentUser();
            this.setCurrentUser(user);
            return user;
        } catch (error) {
            console.error('Error refreshing user data:', error);
            this.clearAuth();
            this.showLoginScreen();
            return null;
        }
    }
}

// Initialize auth manager
window.authManager = new AuthManager();

// Global authentication functions
window.login = (credentials) => window.authManager.handleLogin(credentials);
window.logout = () => window.authManager.logout();
window.isAuthenticated = () => window.authManager.isAuthenticated();
window.getCurrentUser = () => window.authManager.getCurrentUser();

// Auto-logout on token expiration
window.addEventListener('storage', (event) => {
    if (event.key === 'auth_token' && !event.newValue) {
        // Token was removed from storage (possibly by another tab)
        window.authManager.clearAuth();
        window.authManager.showLoginScreen();
        showToast('Session expired. Please log in again.', 'warning');
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (event) => {
    // Escape key to logout (when authenticated)
    if (event.key === 'Escape' && window.authManager.isAuthenticated()) {
        if (event.ctrlKey || event.metaKey) {
            event.preventDefault();
            window.authManager.logout();
        }
    }
    
    // Enter key to submit login form (when on login screen)
    if (event.key === 'Enter' && document.getElementById('login-section').style.display !== 'none') {
        const activeElement = document.activeElement;
        if (activeElement.tagName === 'INPUT' && activeElement.form === window.authManager.loginForm) {
            event.preventDefault();
            window.authManager.loginForm.dispatchEvent(new Event('submit'));
        }
    }
});