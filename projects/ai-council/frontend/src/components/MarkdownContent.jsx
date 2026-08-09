import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const REMARK_PLUGINS = [remarkGfm];

export function MarkdownRenderer({ children }) {
  const content = typeof children === 'string' ? children : String(children || '');

  return <ReactMarkdown remarkPlugins={REMARK_PLUGINS}>{content}</ReactMarkdown>;
}

export default function MarkdownContent({ children, className = '' }) {
  const content = typeof children === 'string' ? children : String(children || '');
  const classes = ['markdown-content', className].filter(Boolean).join(' ');

  return (
    <div className={classes}>
      <MarkdownRenderer>{content}</MarkdownRenderer>
    </div>
  );
}
