import React from 'react';

export function Input({
    label,
    error,
    icon: Icon,
    className = '',
    ...props
}) {
    return (
        <div className="space-y-1.5">
            {label && (
                <label className="label text-dark-muted text-sm font-medium ml-1">
                    {label}
                </label>
            )}

            <div className="relative group">
                {Icon && (
                    <div className="absolute left-3 top-1/2 -translate-y-1/2 text-dark-muted group-focus-within:text-primary-400 transition-colors">
                        <Icon className="w-5 h-5" />
                    </div>
                )}

                <input
                    className={`
            input bg-dark-surface/50 border-dark-border text-white placeholder-dark-muted
            focus:border-primary-500 focus:ring-1 focus:ring-primary-500
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-all duration-200
            ${Icon ? 'pl-10' : ''}
            ${error ? 'border-red-500 focus:border-red-500 focus:ring-red-500' : ''}
            ${className}
          `}
                    {...props}
                />
            </div>

            {error && (
                <p className="text-sm text-red-400 ml-1 animate-fade-in">
                    {error}
                </p>
            )}
        </div>
    );
}
