import React, { useEffect } from 'react';
import { X, AlertTriangle, CheckCircle, Info } from 'lucide-react';

interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
    footer?: React.ReactNode;
    width?: string;
}

export function Modal({ isOpen, onClose, title, children, footer, width = 'max-w-md' }: ModalProps) {
    useEffect(() => {
        const handleEsc = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        if (isOpen) window.addEventListener('keydown', handleEsc);
        return () => window.removeEventListener('keydown', handleEsc);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div
                className={`bg-gray-900 border border-gray-700 shadow-2xl rounded-xl w-full ${width} transform transition-all animate-in zoom-in-95 duration-200`}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-center justify-between p-4 border-b border-gray-800">
                    <h3 className="text-lg font-semibold text-gray-200">{title}</h3>
                    <button
                        onClick={onClose}
                        className="p-1 rounded-lg text-gray-500 hover:bg-gray-800 hover:text-gray-300 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-6">
                    {children}
                </div>

                {footer && (
                    <div className="flex items-center justify-end gap-3 p-4 bg-gray-900/50 border-t border-gray-800 rounded-b-xl">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
}

interface ConfirmModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => void;
    title: string;
    message: string;
    confirmText?: string;
    cancelText?: string;
    variant?: 'danger' | 'warning' | 'info';
    loading?: boolean;
}

export function ConfirmModal({
    isOpen,
    onClose,
    onConfirm,
    title,
    message,
    confirmText = 'Confirm',
    cancelText = 'Cancel',
    variant = 'danger',
    loading = false
}: ConfirmModalProps) {
    const getVariantStyles = () => {
        switch (variant) {
            case 'danger': return 'bg-red-600 hover:bg-red-700 text-white';
            case 'warning': return 'bg-amber-600 hover:bg-amber-700 text-white';
            default: return 'bg-blue-600 hover:bg-blue-700 text-white';
        }
    };

    const getIcon = () => {
        switch (variant) {
            case 'danger': return <AlertTriangle className="w-12 h-12 text-red-500 mb-4 mx-auto" />;
            case 'warning': return <AlertTriangle className="w-12 h-12 text-amber-500 mb-4 mx-auto" />;
            default: return <Info className="w-12 h-12 text-blue-500 mb-4 mx-auto" />;
        }
    };

    return (
        <Modal
            isOpen={isOpen}
            onClose={loading ? () => { } : onClose}
            title={title}
            footer={
                <>
                    <button
                        onClick={onClose}
                        disabled={loading}
                        className="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg transition-colors"
                    >
                        {cancelText}
                    </button>
                    <button
                        onClick={onConfirm}
                        disabled={loading}
                        className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${getVariantStyles()} ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {loading && (
                            <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                        )}
                        {confirmText}
                    </button>
                </>
            }
        >
            <div className="text-center">
                {getIcon()}
                <p className="text-gray-300">{message}</p>
            </div>
        </Modal>
    );
}
