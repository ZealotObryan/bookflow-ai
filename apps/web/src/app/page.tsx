import Link from "next/link";
import { ArrowUpRight, CalendarDays, Check, MessageCircle, ShieldCheck, Sparkles, Users, Zap } from "lucide-react";

const features = [
  { icon: CalendarDays, title: "A calendar that stays clear", copy: "See your day at a glance, coordinate your team and keep every appointment in the right place." },
  { icon: MessageCircle, title: "Conversations that convert", copy: "Give customers a familiar way to ask questions, find a time and manage their appointments." },
  { icon: Sparkles, title: "An assistant for the busy work", copy: "Bring everyday business tasks into one calm workspace, with AI designed to work within your rules." },
];
const steps = [
  ["01", "Set up your business", "Add your services, working hours, team and resources."],
  ["02", "Let customers book", "Manage appointments from one clear calendar and booking list."],
  ["03", "Stay on top of every detail", "Keep customer records, payments and follow-ups together."],
];
export default function HomePage() {
  return <main className="marketing-shell">
    <header className="marketing-nav">
      <Link className="brand-lockup" href="/"><span className="brand-symbol"><CalendarDays size={18}/></span><span>bookflow<span className="brand-period">.</span></span><span className="brand-ai">AI</span></Link>
      <nav className="marketing-links"><a href="#features">Features</a><a href="#how-it-works">How it works</a></nav>
      <div className="marketing-actions"><Link className="nav-login" href="/login">Log in</Link><Link className="button button-dark button-small" href="/dashboard">Explore workspace <ArrowUpRight size={15}/></Link></div>
    </header>
    <section className="marketing-hero">
      <div className="hero-copy-block">
        <div className="eyebrow-pill"><span className="live-dot"/> THE BUSINESS WORKSPACE FOR SERVICE TEAMS</div>
        <h1>Make every<br/><em>appointment</em><br/>feel effortless.</h1>
        <p className="marketing-lede">Less time coordinating. More time doing the work you love. BookFlow brings your calendar, customers and daily operations into one beautifully simple place.</p>
        <div className="hero-cta-row"><Link className="button button-primary" href="/dashboard">Explore the workspace <ArrowUpRight size={17}/></Link><a className="text-link" href="#features">See what’s inside <span>↓</span></a></div>
        <div className="hero-trust"><span><ShieldCheck size={15}/> Built around your business rules</span><span><Check size={15}/> Designed for growing teams</span></div>
      </div>
      <div className="hero-visual">
        <div className="visual-orbit orbit-one"/><div className="visual-orbit orbit-two"/>
        <div className="preview-window">
          <div className="preview-top"><div className="preview-brand"><span className="mini-mark">b.</span> BookFlow <span className="preview-tag">WORKSPACE</span></div><div className="preview-avatar">OS</div></div>
          <div className="preview-body">
            <div className="preview-greeting"><div><span className="muted-label">MONDAY, 9 NOVEMBER</span><h3>Good morning, there <span>✳</span></h3><p>Here’s what’s happening today.</p></div><div className="preview-date">Today <span>⌄</span></div></div>
            <div className="preview-stats"><div><span>Appointments</span><strong>18</strong><small className="positive">↑ 12% this week</small></div><div><span>Revenue</span><strong>MK 486k</strong><small className="positive">↑ 8.4% this week</small></div><div><span>New customers</span><strong>24</strong><small>Across 7 days</small></div></div>
            <div className="preview-lower"><div className="preview-calendar"><div className="preview-panel-title">Today’s schedule <span>View calendar ↗</span></div><div className="schedule-row"><span className="schedule-time">09:00</span><span className="schedule-color green"/><div><b>Hair consultation</b><small>Thoko · Amina Banda</small></div><span className="schedule-status">Confirmed</span></div><div className="schedule-row"><span className="schedule-time">10:30</span><span className="schedule-color peach"/><div><b>Skin treatment</b><small>Memory · Ruth</small></div><span className="schedule-status">Confirmed</span></div><div className="schedule-row"><span className="schedule-time">12:00</span><span className="schedule-color blue"/><div><b>Follow-up session</b><small>James · Chisomo</small></div><span className="schedule-status pending">Pending</span></div></div>
            <div className="preview-assistant"><div className="assistant-icon"><Sparkles size={16}/></div><span className="muted-label">BOOKFLOW ASSISTANT</span><h4>Your day, at a glance.</h4><p>You have 3 appointments to confirm and 2 payment follow-ups.</p><div className="assistant-action">Review follow-ups <ArrowUpRight size={13}/></div></div></div>
          </div>
        </div>
        <div className="floating-note"><span className="floating-icon"><MessageCircle size={16}/></span><div><b>New booking received</b><small>Appointment request · Just now</small></div><span className="note-dot"/></div>
        <div className="floating-stamp"><Sparkles size={14}/> MADE FOR YOUR FLOW</div>
      </div>
    </section>
    <section className="value-strip"><span>ONE CONNECTED WORKSPACE</span><div><CalendarDays size={17}/> Calendar</div><div><Users size={17}/> Customers</div><div><MessageCircle size={17}/> Conversations</div><div><Zap size={17}/> Automations</div></section>
    <section className="feature-section" id="features"><div className="section-intro"><span className="section-overline">THE BOOKFLOW DIFFERENCE</span><h2>Everything in sync.<br/><em>Nothing slipping through.</em></h2><p>All the moving parts of a service business, brought together in a workspace that feels natural from day one.</p></div><div className="feature-grid">{features.map((feature,index)=>{const Icon=feature.icon;return <article className="feature-card" key={feature.title}><div className="feature-icon"><Icon size={20}/></div><span className="feature-index">0{index+1}</span><h3>{feature.title}</h3><p>{feature.copy}</p><a href="/dashboard">Explore workspace <ArrowUpRight size={14}/></a></article>;})}</div></section>
    <section className="how-section" id="how-it-works"><div className="how-heading"><span className="section-overline">A CLEARER WAY TO WORK</span><h2>Simple to start.<br/><em>Ready to grow.</em></h2></div><div className="steps-grid">{steps.map(([number,title,copy])=><article className="step-card" key={number}><span>{number}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section>
    <section className="closing-cta"><div><span className="section-overline">YOUR BUSINESS, IN FLOW</span><h2>Make room for<br/><em>what matters.</em></h2></div><Link className="button button-light" href="/dashboard">Take a look inside <ArrowUpRight size={17}/></Link></section>
    <footer className="marketing-footer"><Link className="brand-lockup" href="/"><span className="brand-symbol"><CalendarDays size={17}/></span><span>bookflow<span className="brand-period">.</span></span><span className="brand-ai">AI</span></Link><span>Appointments, without the back-and-forth.</span><span>© {new Date().getFullYear()} BookFlow AI</span></footer>
  </main>;
}
