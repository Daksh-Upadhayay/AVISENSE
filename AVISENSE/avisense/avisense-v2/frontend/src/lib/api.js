import { supabase } from './supabase';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
console.log('API URL configured as:', API_URL);

export const api = {
    async post(endpoint, body) {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        if (!token) {
            throw new Error('No active session');
        }

        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            body: JSON.stringify(body),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'API request failed');
        }

        return response.json();
    },

    async get(endpoint) {
        const { data: { session } } = await supabase.auth.getSession();
        const token = session?.access_token;

        if (!token) {
            throw new Error('No active session');
        }

        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'API request failed');
        }

        return response.json();
    }
};
