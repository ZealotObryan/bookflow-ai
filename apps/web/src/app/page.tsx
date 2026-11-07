const pillars = [
  {
    number: "01",
    title: "Bookings that make sense",
    description:
      "Manage appointments, multiple services and overlapping schedules without double-booking staff or resources.",
  },
  {
    number: "02",
    title: "WhatsApp-first conversations",
    description:
      "Give customers a familiar way to ask questions, check availability and manage their appointments.",
  },
  {
    number: "03",
    title: "One clear business view",
    description:
      "Bring services, employees, customers, payments and calendar activity into one workspace.",
  },
];

export default function HomePage() {
  return (
    <main className="page-shell">
      <nav className="topbar" aria-label="Main navigation">
        <a className="brand" href="/" aria-label="BookFlow AI home">
          <span className="brand-mark">B</span>
          <span>bookflow<span className="brand-accent">.</span></span>
          <span className="brand-ai">AI</span>
        </a>
        <span className="topbar-note">The smarter way to manage appointments</span>
      </nav>

      <section className="hero">
        <div className="eyebrow"><span className="status-dot" /> PRODUCT FOUNDATION</div>
        <h1>More time for your business.<br /><span>Less time managing it.</span></h1>
        <p className="hero-copy">
          BookFlow AI brings appointments, customers and everyday operations
          together—with WhatsApp at the centre of the experience.
        </p>
        <div className="hero-actions">
          <span className="primary-action">Building the foundation</span>
          <span className="secondary-action">Designed for service businesses</span>
        </div>
        <div className="hero-footnote">
          <span>BUILT FOR AFRICA</span><span className="footnote-divider" />
          <span>READY TO GROW</span><span className="footnote-divider" />
          <span>AI-ASSISTED</span>
        </div>
      </section>

      <section className="pillars" aria-labelledby="pillars-heading">
        <div className="section-heading">
          <div>
            <p className="section-kicker">THE BOOKFLOW APPROACH</p>
            <h2 id="pillars-heading">Everything working in sync.</h2>
          </div>
          <p className="section-intro">
            A connected experience for business owners and the people they serve.
          </p>
        </div>
        <div className="pillar-grid">
          {pillars.map((pillar) => (
            <article className="pillar-card" key={pillar.number}>
              <span className="pillar-number">{pillar.number}</span>
              <h3>{pillar.title}</h3>
              <p>{pillar.description}</p>
            </article>
          ))}
        </div>
      </section>

      <footer className="footer">
        <span>© {new Date().getFullYear()} BookFlow AI</span>
        <span>Appointments, without the back-and-forth.</span>
      </footer>
    </main>
  );
}
