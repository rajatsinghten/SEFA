// Handle authentication errors and token expiration

// Check session status periodically
function checkAuthStatus() {
    fetch('/auth/status')
        .then(response => {
            if (!response.ok) {
                // If status is 401, redirect to login
                if (response.status === 401) {
                    showAuthError("Your session has expired. Please log in again.");
                    setTimeout(() => {
                        window.location.href = '/login';
                    }, 2000);
                }
                return;
            }
            return response.json();
        })
        .then(data => {
            if (data && !data.authenticated) {
                showAuthError(data.message || "Authentication required");
                setTimeout(() => {
                    window.location.href = '/login';
                }, 2000);
            }
        })
        .catch(error => {
            console.error("Auth status check failed:", error);
        });
}

// Display authentication error message
function showAuthError(message) {
    // Check if error notification already exists
    let errorNotification = document.getElementById('auth-error-notification');
    
    if (!errorNotification) {
        // Create error notification element
        errorNotification = document.createElement('div');
        errorNotification.id = 'auth-error-notification';
        errorNotification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
            border-radius: 4px;
            padding: 12px 20px;
            z-index: 9999;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        `;
        document.body.appendChild(errorNotification);
    }
    
    // Update message
    errorNotification.innerText = message;
}

// Check authentication status every minute
setInterval(checkAuthStatus, 60000);

// Handle API response errors
function handleApiResponse(response) {
    if (!response.ok) {
        // Handle 401 unauthorized errors
        if (response.status === 401) {
            window.location.href = '/refresh-auth';
            throw new Error('Authentication required');
        }
        // Handle other errors
        throw new Error(`Request failed with status ${response.status}`);
    }
    return response.json();
}

// Wrap fetch calls with error handling
function fetchWithAuth(url, options = {}) {
    return fetch(url, options)
        .then(handleApiResponse)
        .catch(error => {
            console.error('API request failed:', error);
            throw error;
        });
}
