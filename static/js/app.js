// Urban Issue Reporter - Main JavaScript

// Global variables
let currentMap = null;
let currentMarker = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('🏙️ Urban Issue Reporter initialized');
    
    // Initialize tooltips and interactive elements
    initializeInteractiveElements();
    
    // Auto-hide flash messages
    setTimeout(hideFlashMessages, 5000);
});

// Initialize interactive elements
function initializeInteractiveElements() {
    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            document.querySelector(this.getAttribute('href')).scrollIntoView({
                behavior: 'smooth'
            });
        });
    });
    
    // Add loading states to buttons
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<div class="loading"></div> Processing...';
                submitBtn.disabled = true;
                
                // Re-enable after 5 seconds (fallback)
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 5000);
            }
        });
    });
}

// Hide flash messages
function hideFlashMessages() {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(msg => {
        msg.style.opacity = '0';
        msg.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (msg.parentNode) {
                msg.parentNode.removeChild(msg);
            }
        }, 500);
    });
}

// Show loading spinner
function showLoading(element) {
    if (element) {
        element.innerHTML = '<div class="loading"></div> Loading...';
        element.disabled = true;
    }
}

// Hide loading spinner
function hideLoading(element, originalText) {
    if (element) {
        element.innerHTML = originalText;
        element.disabled = false;
    }
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Validate coordinates
function validateCoordinates(lat, lng) {
    const latitude = parseFloat(lat);
    const longitude = parseFloat(lng);
    
    return !isNaN(latitude) && !isNaN(longitude) && 
           latitude >= -90 && latitude <= 90 && 
           longitude >= -180 && longitude <= 180;
}

// Show notification
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `flash-message flash-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
    `;
    
    // Add to flash messages container or create one
    let container = document.querySelector('.flash-messages');
    if (!container) {
        container = document.createElement('div');
        container.className = 'flash-messages';
        document.body.appendChild(container);
    }
    
    container.appendChild(notification);
    
    // Auto-hide after 4 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 500);
    }, 4000);
}

// Handle AJAX errors
function handleAjaxError(error, defaultMessage = 'An error occurred') {
    console.error('AJAX Error:', error);
    showNotification(defaultMessage, 'error');
}

// Utility function to get CSRF token (if needed in future)
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('search');
    if (searchInput) {
        let searchTimeout;
        
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                // Auto-submit search after 1 second of no typing
                if (this.value.length >= 3 || this.value.length === 0) {
                    this.form.submit();
                }
            }, 1000);
        });
    }
}

// Filter change handler
function onFilterChange() {
    const form = document.querySelector('.filter-grid').closest('form');
    if (form) {
        form.submit();
    }
}

// Copy coordinates to clipboard
function copyCoordinates(lat, lng) {
    const text = `${lat}, ${lng}`;
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Coordinates copied to clipboard!', 'success');
    }).catch(() => {
        showNotification('Unable to copy coordinates', 'error');
    });
}

// Share issue
function shareIssue(issueId, title) {
    const url = window.location.origin + `/issue/${issueId}`;
    
    if (navigator.share) {
        navigator.share({
            title: title,
            text: 'Check out this urban issue report',
            url: url
        });
    } else {
        // Fallback: copy to clipboard
        navigator.clipboard.writeText(url).then(() => {
            showNotification('Issue link copied to clipboard!', 'success');
        }).catch(() => {
            showNotification('Unable to share issue', 'error');
        });
    }
}

// Print issue report
function printIssue() {
    window.print();
}

// Export data (future enhancement)
function exportData(format = 'csv') {
    showNotification('Export functionality coming soon!', 'info');
}

// Initialize charts (if needed in future)
function initializeCharts() {
    // Placeholder for future chart implementations
    console.log('Charts initialization placeholder');
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Ctrl/Cmd + / for search focus
    if ((e.ctrlKey || e.metaKey) && e.key === '/') {
        e.preventDefault();
        const searchInput = document.getElementById('search');
        if (searchInput) {
            searchInput.focus();
        }
    }
    
    // Escape to close modals
    if (e.key === 'Escape') {
        const modal = document.querySelector('#statusModal');
        if (modal && modal.style.display === 'flex') {
            modal.style.display = 'none';
        }
    }
});

// Console welcome message
console.log('%c🏙️ Urban Issue Reporter', 'color: #667eea; font-size: 20px; font-weight: bold;');
console.log('%cSystem Status: ✅ Operational', 'color: #27ae60; font-weight: bold;');
