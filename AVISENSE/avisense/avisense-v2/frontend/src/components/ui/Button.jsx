import React from 'react';
import { Loader2 } from 'lucide-react';

export function Button({
    children,
    variant = 'primary',
    className = '',
    isLoading = false,
    disabled,
    ...props
}) {
    const baseStyles = "relative overflow-hidden transition-all duration-300 active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed";

    const variants = {
        primary: "btn-primary shadow-glow hover:shadow-glow-lg",
        secondary: "btn-secondary backdrop-blur-md",
        outline: "btn-outline backdrop-blur-sm",
        ghost: "btn-ghost hover:bg-white/5",
        danger: "bg-red-500/10 text-red-500 border border-red-500/20 hover:bg-red-500/20 hover:border-red-500/40"
    };

    return (
        <button
            className={`btn ${baseStyles} ${variants[variant]} ${className}`}
            disabled={disabled || isLoading}
            {...props}
        >
            {isLoading && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
            {children}

            {/* Shine effect for primary buttons */}
            {variant === 'primary' && !disabled && !isLoading && (
                <div className="absolute inset-0 -translate-x-full group-hover:animate-[shimmer_2s_infinite] bg-gradient-to-r from-transparent via-white/20 to-transparent" />
            )}
        </button>
    );
}
