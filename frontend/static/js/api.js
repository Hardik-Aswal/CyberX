// frontend/static/js/api.js - API Communication Layer

class ApiClient {
    constructor() {
        this.baseUrl = window.location.origin;
        this.token = localStorage.getItem('auth_token');
    }

    // Set authentication token
    setToken(token) {
        this.token = token;
        if (token) {
            localStorage.setItem('auth_token', token);
        } else {
            localStorage.removeItem('auth_token');
        }
    }

    // Get authentication headers
    getHeaders(includeAuth = true) {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (includeAuth && this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    // Generic request method
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const config = {
            method: 'GET',
            headers: this.getHeaders(options.auth !== false),
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            
            // Handle authentication errors
            if (response.status === 401) {
                this.setToken(null);
                window.location.reload();
                throw new Error('Authentication failed');
            }

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }

            return await response.text();
        } catch (error) {
            console.error(`API Error (${endpoint}):`, error);
            throw error;
        }
    }

    // Authentication endpoints
    async login(credentials) {
        const response = await this.request('/api/auth/login', {
            method: 'POST',
            body: credentials,
            auth: false
        });
        
        if (response.access_token) {
            this.setToken(response.access_token);
        }
        
        return response;
    }

    async logout() {
        try {
            await this.request('/api/auth/logout', {
                method: 'POST'
            });
        } finally {
            this.setToken(null);
        }
    }

    async getCurrentUser() {
        return await this.request('/api/auth/me');
    }

    // Telegram endpoints
    async getTelegramChannels(params = {}) {
        const queryParams = new URLSearchParams();
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                queryParams.append(key, value);
            }
        });

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/api/telegram/channels?${queryString}` : '/api/telegram/channels';
        
        return await this.request(endpoint);
    }

    async getTelegramStats() {
        return await this.request('/api/telegram/stats');
    }

    async getTelegramChannel(channelId) {
        return await this.request(`/api/telegram/channels/${channelId}`);
    }

    // Webpage endpoints
    async getWebpages(params = {}) {
        const queryParams = new URLSearchParams();
        
        Object.entries(params).forEach(([key, value]) => {
            if (value !== undefined && value !== null && value !== '') {
                queryParams.append(key, value);
            }
        });

        const queryString = queryParams.toString();
        const endpoint = queryString ? `/api/webpages/pages?${queryString}` : '/api/webpages/pages';
        
        return await this.request(endpoint);
    }

    async getWebpageStats() {
        return await this.request('/api/webpages/stats');
    }

    async getWebpage(pageId) {
        return await this.request(`/api/webpages/pages/${pageId}`);
    }

    // Classification endpoints
    async classifyChat(text) {
        return await this.request('/chat/predict', {
            method: 'POST',
            body: { text },
            auth: false // These endpoints might not require auth
        });
    }

    async classifyText(text, url = null) {
        const body = { text };
        if (url) body.url = url;
        
        return await this.request('/text/predict', {
            method: 'POST',
            body,
            auth: false
        });
    }

    // Health check
    async healthCheck() {
        return await this.request('/health', { auth: false });
    }
}

// Global API client instance
window.apiClient = new ApiClient();

// Helper functions for common API operations
window.apiHelpers = {
    // Show loading state
    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <p>Loading...</p>
                </div>
            `;
        }
    },

    // Show error state
    showError(elementId, message = 'An error occurred while loading data') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="error-container">
                    <div class="error-icon">⚠️</div>
                    <h3>Error</h3>
                    <p>${message}</p>
                </div>
            `;
        }
    },

    // Show empty state
    showEmpty(elementId, message = 'No data available') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div class="empty-container">
                    <div class="empty-icon">📭</div>
                    <h3>No Data</h3>
                    <p>${message}</p>
                </div>
            `;
        }
    },

    // Format date for display
    formatDate(dateString) {
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-IN', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return 'Invalid Date';
        }
    },

    // Format relative time (e.g., "2 days ago")
    formatRelativeTime(dateString) {
        try {
            const date = new Date(dateString);
            const now = new Date();
            const diffTime = Math.abs(now - date);
            const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
            const diffHours = Math.floor(diffTime / (1000 * 60 * 60));
            const diffMinutes = Math.floor(diffTime / (1000 * 60));

            if (diffDays > 0) {
                return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
            } else if (diffHours > 0) {
                return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
            } else if (diffMinutes > 0) {
                return `${diffMinutes} minute${diffMinutes > 1 ? 's' : ''} ago`;
            } else {
                return 'Just now';
            }
        } catch (error) {
            return 'Unknown';
        }
    },

    // Format risk score as percentage
    formatRiskScore(score) {
        return `${(score * 100).toFixed(1)}%`;
    },

    // Get risk level from score
    getRiskLevel(score) {
        if (score >= 0.8) return 'HIGH';
        if (score >= 0.6) return 'MEDIUM';
        return 'LOW';
    },

    // Get risk level class for styling
    getRiskClass(score) {
        if (score >= 0.8) return 'risk-high';
        if (score >= 0.6) return 'risk-medium';
        return 'risk-low';
    },

    // Truncate text for display
    truncateText(text, maxLength = 100) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    },

    // Extract domain from URL
    extractDomain(url) {
        try {
            return new URL(url).hostname;
        } catch (error) {
            return 'unknown';
        }
    },

    // Debounce function for search/filter inputs
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Handle API errors gracefully
    handleApiError(error, fallbackMessage = 'An unexpected error occurred') {
        console.error('API Error:', error);
        
        let message = fallbackMessage;
        
        if (error.message) {
            if (error.message.includes('fetch')) {
                message = 'Network error. Please check your connection.';
            } else if (error.message.includes('401')) {
                message = 'Authentication required. Please log in again.';
            } else if (error.message.includes('403')) {
                message = 'Access denied. You do not have permission to access this resource.';
            } else if (error.message.includes('404')) {
                message = 'Requested resource not found.';
            } else if (error.message.includes('500')) {
                message = 'Server error. Please try again later.';
            } else {
                message = error.message;
            }
        }
        
        return message;
    }
};

// Initialize API client when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Check if user is already authenticated
    if (window.apiClient.token) {
        // Verify token is still valid
        window.apiClient.getCurrentUser()
            .then(user => {
                console.log('User authenticated:', user);
            })
            .catch(error => {
                console.log('Token invalid, clearing auth');
                window.apiClient.setToken(null);
            });
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { ApiClient, apiHelpers: window.apiHelpers };
}