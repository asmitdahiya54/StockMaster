const API = {

    async request(endpoint, options = {}) {

        const token = localStorage.getItem("stockmaster_token");

        const headers = {
            "Content-Type": "application/json",
            ...(options.headers || {})
        };

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers
        });

        let result;

        try {
            result = await response.json();
        } catch {
            result = {};
        }

        if (!response.ok) {
            throw new Error(result.message || `Request failed: ${response.status}`);
        }

        return result;
    },

    get(endpoint) {
        return this.request(endpoint);
    },

    post(endpoint, data) {
        return this.request(endpoint, {
            method: "POST",
            body: JSON.stringify(data)
        });
    },

    put(endpoint, data) {
        return this.request(endpoint, {
            method: "PUT",
            body: JSON.stringify(data)
        });
    },

    delete(endpoint) {
        return this.request(endpoint, {
            method: "DELETE"
        });
    }
};
