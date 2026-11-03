import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'destructive' | 'plum';
  pill?: boolean;
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'primary',
  pill = false,
  size = 'md',
  loading = false,
  className = '',
  disabled,
  ...props
}) => {
  const baseClasses = "inline-flex items-center justify-center font-head font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-cf-plum/50 disabled:opacity-50 disabled:cursor-not-allowed";

  const sizeClasses = {
    sm: "text-xs px-3 py-1.5 min-h-[36px]",
    md: "text-sm px-4 py-2.5 min-h-[44px]",
    lg: "text-base px-6 py-3 min-h-[48px]",
  }[size];

  const variantClasses = {
    primary: "bg-cf-violet-600 hover:bg-cf-violet-700 text-white shadow-xs",
    secondary: "bg-white hover:bg-cf-bg-2 text-cf-violet-600 border border-cf-border hover:border-cf-thistle",
    ghost: "bg-transparent hover:bg-cf-lavender/40 text-cf-violet-600 hover:text-cf-violet-700",
    destructive: "bg-cf-danger hover:bg-red-700 text-white shadow-xs",
    plum: "bg-cf-plum hover:bg-cf-steel text-cf-violet-900 shadow-xs",
  }[variant];

  const radiusClass = pill ? "rounded-full" : "rounded-cf-md";

  return (
    <button
      className={`${baseClasses} ${sizeClasses} ${variantClasses} ${radiusClass} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
      ) : null}
      {children}
    </button>
  );
};
