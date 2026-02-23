import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Simple CSS for demo purposes
const style = document.createElement('style');
style.textContent = `
  * {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
  }
  
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
      'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
      sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    background-color: #f3f4f6;
  }

  .min-h-screen {
    min-height: 100vh;
  }

  .flex {
    display: flex;
  }

  .items-center {
    align-items: center;
  }

  .justify-center {
    justify-content: center;
  }

  .p-4 {
    padding: 1rem;
  }

  .p-6 {
    padding: 1.5rem;
  }

  .p-3 {
    padding: 0.75rem;
  }

  .p-2 {
    padding: 0.5rem;
  }

  .pt-4 {
    padding-top: 1rem;
  }

  .mb-2 {
    margin-bottom: 0.5rem;
  }

  .mb-3 {
    margin-bottom: 0.75rem;
  }

  .mb-4 {
    margin-bottom: 1rem;
  }

  .mb-6 {
    margin-bottom: 1.5rem;
  }

  .ml-2 {
    margin-left: 0.5rem;
  }

  .ml-3 {
    margin-left: 0.75rem;
  }

  .mr-2 {
    margin-right: 0.5rem;
  }

  .mr-3 {
    margin-right: 0.75rem;
  }

  .gap-2 {
    gap: 0.5rem;
  }

  .gap-3 {
    gap: 0.75rem;
  }

  .bg-white {
    background-color: #ffffff;
  }

  .bg-gray-50 {
    background-color: #f9fafb;
  }

  .bg-gray-100 {
    background-color: #f3f4f6;
  }

  .bg-gray-200 {
    background-color: #e5e7eb;
  }

  .bg-red-100 {
    background-color: #fee2e2;
  }

  .bg-green-100 {
    background-color: #dcfce7;
  }

  .bg-blue-50 {
    background-color: #eff6ff;
  }

  .bg-blue-100 {
    background-color: #dbeafe;
  }

  .bg-yellow-50 {
    background-color: #fefce8;
  }

  .rounded {
    border-radius: 0.25rem;
  }

  .rounded-lg {
    border-radius: 0.5rem;
  }

  .rounded-full {
    border-radius: 9999px;
  }

  .shadow-xl {
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }

  .border {
    border-width: 1px;
  }

  .border-b-2 {
    border-bottom-width: 2px;
  }

  .border-gray-300 {
    border-color: #d1d5db;
  }

  .border-red-400 {
    border-color: #f87171;
  }

  .border-green-400 {
    border-color: #4ade80;
  }

  .border-blue-500 {
    border-color: #3b82f6;
  }

  .text-2xl {
    font-size: 1.5rem;
  }

  .text-lg {
    font-size: 1.125rem;
  }

  .text-sm {
    font-size: 0.875rem;
  }

  .text-xs {
    font-size: 0.75rem;
  }

  .font-bold {
    font-weight: 700;
  }

  .font-medium {
    font-weight: 500;
  }

  .text-gray-500 {
    color: #6b7280;
  }

  .text-gray-600 {
    color: #4b5563;
  }

  .text-gray-700 {
    color: #374151;
  }

  .text-gray-800 {
    color: #1f2937;
  }

  .text-gray-900 {
    color: #111827;
  }

  .text-red-700 {
    color: #b91c1c;
  }

  .text-green-700 {
    color: #15803d;
  }

  .text-blue-900 {
    color: #1e3a8a;
  }

  .text-white {
    color: #ffffff;
  }

  .uppercase {
    text-transform: uppercase;
  }

  .capitalize {
    text-transform: capitalize;
  }

  .w-8 {
    width: 2rem;
  }

  .w-12 {
    width: 3rem;
  }

  .w-24 {
    width: 6rem;
  }

  .w-32 {
    width: 8rem;
  }

  .h-6 {
    height: 1.5rem;
  }

  .h-8 {
    height: 2rem;
  }

  .h-48 {
    height: 12rem;
  }

  .max-w-2xl {
    max-width: 42rem;
  }

  .max-h-\\[90vh\\] {
    max-height: 90vh;
  }

  .grid {
    display: grid;
  }

  .grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .flex-wrap {
    flex-wrap: wrap;
  }

  .overflow-y-auto {
    overflow-y: auto;
  }

  .cursor-pointer {
    cursor: pointer;
  }

  .transition-colors {
    transition-property: color, background-color, border-color;
    transition-duration: 150ms;
  }

  .transition-transform {
    transition-property: transform;
    transition-duration: 150ms;
  }

  .translate-x-6 {
    transform: translateX(1.5rem);
  }

  .absolute {
    position: absolute;
  }

  .relative {
    position: relative;
  }

  .top-1 {
    top: 0.25rem;
  }

  .left-1 {
    left: 0.25rem;
  }

  .inline-block {
    display: inline-block;
  }

  .animate-spin {
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .hover\\:bg-gray-50:hover {
    background-color: #f9fafb;
  }

  .hover\\:bg-gray-200:hover {
    background-color: #e5e7eb;
  }

  .hover\\:bg-gray-300:hover {
    background-color: #d1d5db;
  }

  .hover\\:bg-blue-700:hover {
    background-color: #1d4ed8;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }

  .disabled\\:opacity-50:disabled {
    opacity: 0.5;
  }

  .focus\\:ring-2:focus {
    --tw-ring-offset-shadow: var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);
    --tw-ring-shadow: var(--tw-ring-inset) 0 0 0 calc(2px + var(--tw-ring-offset-width)) var(--tw-ring-color);
    box-shadow: var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow, 0 0 #0000);
  }

  .focus\\:ring-blue-500:focus {
    --tw-ring-color: #3b82f6;
  }

  .focus\\:border-transparent:focus {
    border-color: transparent;
  }
`;

document.head.appendChild(style);

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
