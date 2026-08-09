import './Skeleton.css';

/**
 * Generic Skeleton Loader Component
 * 
 * PROPS:
 * - variant: 'text' | 'rect' | 'circle' | 'avatar' (default: 'text')
 * - width: string (e.g., '100%', '50px')
 * - height: string (e.g., '1rem', '200px')
 * - className: string (additional classes)
 * - style: object (additional inline styles)
 */
export default function Skeleton({ variant = 'text', width, height, className = '', style = {} }) {
    const computedStyle = {
        width,
        height,
        ...style
    };

    return (
        <span
            className={`skeleton ${variant} ${className}`}
            style={computedStyle}
            aria-hidden="true"
        />
    );
}
