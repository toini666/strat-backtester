import { useEffect, useState } from 'react';
import { CheckCircle, AlertCircle, X, Info } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'info';

export interface ToastMessage {
    id: string;
    type: ToastType;
    message: string;
    duration?: number;
}

interface ToastProps {
    toast: ToastMessage;
    onDismiss: (id: string) => void;
}

function ToastItem({ toast, onDismiss }: ToastProps) {
    const [isExiting, setIsExiting] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            handleDismiss();
        }, toast.duration || 3000);

        return () => clearTimeout(timer);
    }, [toast]);

    const handleDismiss = () => {
        setIsExiting(true);
        setTimeout(() => {
            onDismiss(toast.id);
        }, 300); // Wait for exit animation
    };

    const getStyles = () => {
        switch (toast.type) {
            case 'success':
                return 'bg-green-900/40 border-green-500/50 text-green-200';
            case 'error':
                return 'bg-red-900/40 border-red-500/50 text-red-200';
            default:
                return 'bg-blue-900/40 border-blue-500/50 text-blue-200';
        }
    };

    const getIcon = () => {
        switch (toast.type) {
            case 'success': return <CheckCircle className="w-5 h-5 text-green-400" />;
            case 'error': return <AlertCircle className="w-5 h-5 text-red-400" />;
            default: return <Info className="w-5 h-5 text-blue-400" />;
        }
    };

    return (
        <div
            className={`flex items-center gap-3 px-4 py-3 rounded-lg border shadow-lg backdrop-blur-md transition-all duration-300 mb-2 ${getStyles()} ${isExiting ? 'opacity-0 translate-x-full' : 'animate-in slide-in-from-right'}`}
            role="alert"
        >
            {getIcon()}
            <p className="text-sm font-medium">{toast.message}</p>
            <button
                onClick={handleDismiss}
                className="ml-auto p-1 rounded hover:bg-white/10 transition-colors"
            >
                <X className="w-4 h-4 opacity-70" />
            </button>
        </div>
    );
}

interface ToastContainerProps {
    toasts: ToastMessage[];
    onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end max-w-sm w-full pointer-events-none">
            <div className="pointer-events-auto w-full">
                {toasts.map(toast => (
                    <ToastItem key={toast.id} toast={toast} onDismiss={onDismiss} />
                ))}
            </div>
        </div>
    );
}

// Hook for managing toasts
export function useToast() {
    const [toasts, setToasts] = useState<ToastMessage[]>([]);

    const addToast = (message: string, type: ToastType = 'info', duration = 3000) => {
        const id = Math.random().toString(36).substr(2, 9);
        setToasts(prev => [...prev, { id, message, type, duration }]);
        return id;
    };

    const removeToast = (id: string) => {
        setToasts(prev => prev.filter(t => t.id !== id));
    };

    return { toasts, addToast, removeToast };
}
