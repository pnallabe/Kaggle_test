import { useCallback } from 'react';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
  duration?: number;
}

let toastId = 0;
const toastListeners: Array<(toast: Toast) => void> = [];
const toastStack: Toast[] = [];

export function useToast() {
  const addToast = useCallback((message: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', duration = 5000) => {
    const id = `toast-${++toastId}`;
    const toast: Toast = { id, message, type, duration };
    
    toastStack.push(toast);
    toastListeners.forEach(listener => listener(toast));

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, []);

  const removeToast = useCallback((id: string) => {
    const index = toastStack.findIndex(t => t.id === id);
    if (index !== -1) {
      toastStack.splice(index, 1);
      toastListeners.forEach(listener => listener({ id, message: '', type: 'info' }));
    }
  }, []);

  return { addToast, removeToast };
}

export function subscribeToToasts(listener: (toast: Toast) => void) {
  toastListeners.push(listener);
  return () => {
    const index = toastListeners.indexOf(listener);
    if (index !== -1) {
      toastListeners.splice(index, 1);
    }
  };
}

export function getToastStack() {
  return toastStack;
}
