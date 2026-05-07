import Link from 'next/link';

const agents = [
  {
    slug: 'coding-standards-enforcer',
    name: 'Coding Standards Enforcer',
    description:
      'Detect coding-standard violations and generate AI-powered fixes for Python, C++, Java, JS/TS, Go, and Rust.',
  },
];

export default function AgentsIndex() {
  return (
    <div className="page">
      <div className="card">
        <div className="header-section">
          <h1>Agents</h1>
          <p className="subtitle">Pick an agent to launch.</p>
        </div>
        <ul className="agent-list">
          {agents.map((a) => (
            <li key={a.slug} className="agent-card">
              <Link href={`/${a.slug}`}>
                <h2>{a.name}</h2>
                <p>{a.description}</p>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
