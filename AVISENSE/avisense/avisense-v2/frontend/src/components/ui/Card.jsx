import React from 'react';

export function Card({ children, className = '', hover = false, ...props }) {
    return (
        <div
            className={`
        glass-card p-6 
        ${hover ? 'hover:-translate-y-1 hover:shadow-glow-sm cursor-pointer' : ''} 
        ${className}
      `}
            {...props}
        >
            {children}
        </div>
    );
}

export function CardHeader({ children, className = '' }) {
    return <div className={`mb-4 ${className}`}>{children}</div>;
}

export function CardTitle({ children, className = '' }) {
    return <h3 className={`text-xl font-semibold text-white ${className}`}>{children}</h3>;
}

export function CardContent({ children, className = '' }) {
    return <div className={className}>{children}</div>;
}
