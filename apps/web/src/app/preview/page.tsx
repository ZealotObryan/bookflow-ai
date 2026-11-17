"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft, ArrowRight, CalendarDays, CheckCircle2, ChevronLeft,
  ChevronRight, ClipboardList, CreditCard, LayoutDashboard, MessageCircle,
  Scissors, Sparkles, Users, Wallet, Clock3, TrendingUp, Menu, X
} from "lucide-react";

const sections = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "calendar", label: "Calendar & bookings", icon: CalendarDays },
  { id: "customers", label: "Customers", icon: Users },
  { id: "work", label: "Projects & work", icon: ClipboardList },
  { id: "payments", label: "Payments & reports", icon: Wallet },
  { id: "assistant", label: "AI assistant", icon: MessageCircle },
] as const;
type Section = typeof sections[number]["id"];

const bookings = [
  ["09:00", "Hair consultation", "Amina Banda", "Thoko M.", "Confirmed", "MK 25,000"],
  ["10:30", "Skin treatment", "Ruth Phiri", "Memory P.", "Confirmed", "MK 45,000"],
  ["12:00", "Follow-up session", "Chisomo Zulu", "James K.", "Awaiting", "MK 18,000"],
  ["14:00", "Manicure & pedicure", "Tadala Nkhoma", "Thoko M.", "Confirmed", "MK 35,000"],
];
const customers = [
  ["Amina Banda", "+265 991 234 567", "8", "MK 245,000"],
  ["Ruth Phiri", "+265 888 345 678", "5", "MK 186,000"],
  ["Chisomo Zulu", "+265 999 456 789", "3", "MK 92,000"],
];
const projects = [
  ["Chisomo & Peter wedding", "Event photography", "Editing", "28 Nov 2026"],
  ["Mwayi graduation portraits", "Photography", "Client review", "21 Nov 2026"],
  ["Corporate brand package", "Design project", "In progress", "04 Dec 2026"],
];

export default function ProductPreviewPage() {
  const [active, setActive] = useState<Section>("overview");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [tourStep, setTourStep] = useState(0);
  const [showTour, setShowTour] = useState(true);
  const activeItem = sections.find(s => s.id === active)!;
  const next = () => setActive(sections[(sections.findIndex(s => s.id === active) + 1) % sections.length].id);
  const previous = () => setActive(sections[(sections.findIndex(s => s.id === active) + sections.length - 1) % sections.length].id);

  return <main className="bf-preview">
    <style jsx global>{`
      .bf-preview{min-height:100vh;background:#f5f7f4;color:#17251d;font-family:inherit}
      .bf-preview *{box-sizing:border-box}
      .bf-preview a{color:inherit;text-decoration:none}
      .bf-preview-top{height:68px;padding:0 clamp(18px,4vw,56px);display:flex;align-items:center;justify-content:space-between;background:#fff;border-bottom:1px solid #e7ece7;gap:16px}
      .bf-preview-brand{display:flex;align-items:center;gap:10px;font-weight:800;font-size:19px;letter-spacing:-.5px}
      .bf-preview-mark{width:34px;height:34px;border-radius:11px;background:#174b35;color:#fff;display:grid;place-items:center}
      .bf-preview-pill{font-size:10px;letter-spacing:1.2px;font-weight:800;background:#e9f2eb;color:#236143;padding:6px 9px;border-radius:20px}
      .bf-preview-top-actions{display:flex;align-items:center;gap:12px}
      .bf-preview-link{font-size:13px;font-weight:650;color:#526258}
      .bf-preview-cta{background:#174b35;color:#fff!important;border-radius:9px;padding:11px 16px;font-size:13px;font-weight:750;display:inline-flex;align-items:center;gap:8px}
      .bf-preview-intro{max-width:1200px;margin:0 auto;padding:35px 24px 22px;display:flex;justify-content:space-between;align-items:end;gap:24px}
      .bf-preview-kicker{font-size:10px;font-weight:800;letter-spacing:1.7px;color:#548066}
      .bf-preview-intro h1{font-size:clamp(25px,4vw,38px);letter-spacing:-1.5px;margin:9px 0 7px;line-height:1.08}
      .bf-preview-intro p{font-size:14px;color:#66746b;margin:0;max-width:610px;line-height:1.6}
      .bf-preview-demo{max-width:1200px;margin:0 auto;padding:0 24px 44px}
      .bf-preview-frame{display:grid;grid-template-columns:225px minmax(0,1fr);min-height:590px;background:#fff;border:1px solid #e4eae4;border-radius:17px;overflow:hidden;box-shadow:0 18px 50px #183b2410}
      .bf-preview-side{background:#fbfcfa;border-right:1px solid #e8ede8;padding:22px 14px;display:flex;flex-direction:column}
      .bf-preview-side-label{font-size:9px;letter-spacing:1.4px;color:#8a978e;font-weight:800;padding:0 10px 13px}
      .bf-preview-nav{border:0;background:transparent;width:100%;display:flex;align-items:center;gap:11px;padding:11px 10px;border-radius:9px;text-align:left;color:#66736a;font-size:12px;font-weight:650;cursor:pointer;margin-bottom:3px}
      .bf-preview-nav.active{background:#eaf2ec;color:#174b35;font-weight:800}
      .bf-preview-side-note{margin-top:auto;background:#f0f5f0;border:1px solid #e3ebe3;padding:13px;border-radius:11px;font-size:11px;color:#66746b;line-height:1.5}
      .bf-preview-side-note b{display:block;color:#234d35;margin-bottom:4px}
      .bf-preview-main{padding:26px clamp(16px,3vw,32px);min-width:0}
      .bf-preview-main-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:22px}
      .bf-preview-main-head h2{font-size:21px;letter-spacing:-.6px;margin:0}
      .bf-preview-main-head p{font-size:12px;color:#839087;margin:5px 0 0}
      .bf-preview-date{border:1px solid #e4eae4;padding:9px 11px;border-radius:8px;font-size:11px;color:#526258}
      .bf-preview-stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-bottom:18px}
      .bf-preview-stat{border:1px solid #e9eee9;border-radius:11px;padding:15px;min-width:0}
      .bf-preview-stat span{font-size:10px;color:#78857c;display:block}
      .bf-preview-stat strong{font-size:23px;letter-spacing:-.7px;display:block;margin:7px 0 4px}
      .bf-preview-stat small{font-size:10px;color:#47805a}
      .bf-preview-panel{border:1px solid #e8ede8;border-radius:12px;padding:17px;margin-top:14px;min-width:0}
      .bf-preview-panel-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px}
      .bf-preview-panel-head b{font-size:13px}
      .bf-preview-panel-head span{font-size:10px;color:#7c897f}
      .bf-preview-row{display:grid;grid-template-columns:55px minmax(0,1fr) auto;gap:11px;align-items:center;padding:12px 0;border-top:1px solid #eff2ef}
      .bf-preview-time{font-size:11px;color:#718076;font-weight:700}
      .bf-preview-row strong{font-size:11px;display:block}
      .bf-preview-row small{font-size:10px;color:#849087;display:block;margin-top:3px}
      .bf-preview-status{font-size:9px;border-radius:20px;background:#eaf4ec;color:#36734a;padding:5px 8px;white-space:nowrap}
      .bf-preview-status.pending{background:#fff4e5;color:#a46b21}
      .bf-preview-table{width:100%;border-collapse:collapse;font-size:11px}
      .bf-preview-table th{text-align:left;color:#87938a;font-size:9px;letter-spacing:.7px;padding:10px 8px;border-bottom:1px solid #e9eee9}
      .bf-preview-table td{padding:13px 8px;border-bottom:1px solid #eff2ef;color:#59675e}
      .bf-preview-table td b{color:#26372c}
      .bf-preview-project{display:flex;justify-content:space-between;gap:12px;padding:13px 0;border-bottom:1px solid #edf1ed}
      .bf-preview-project b{font-size:12px;display:block}
      .bf-preview-project small{font-size:10px;color:#829087;display:block;margin-top:4px}
      .bf-preview-chat{max-width:520px;border:1px solid #e8ede8;border-radius:14px;padding:18px;background:#fbfcfa}
      .bf-preview-bubble{padding:13px 14px;border-radius:12px;background:#eaf2ec;color:#34523d;font-size:12px;line-height:1.6;margin:12px 0;max-width:90%}
      .bf-preview-bubble.user{background:#174b35;color:white;margin-left:auto}
      .bf-preview-tour{margin-top:18px;padding:14px 16px;border-radius:11px;background:#f0f5f0;display:flex;align-items:center;justify-content:space-between;gap:12px}
      .bf-preview-tour p{font-size:11px;color:#65736a;margin:3px 0 0}
      .bf-preview-tour b{font-size:12px}
      .bf-preview-tour-actions{display:flex;align-items:center;gap:8px}
      .bf-preview-iconbtn{border:1px solid #dfe7df;background:#fff;border-radius:8px;padding:8px;display:grid;place-items:center;cursor:pointer;color:#365640}
      .bf-preview-foot{max-width:1200px;margin:0 auto;padding:0 24px 34px;display:flex;align-items:center;justify-content:space-between;gap:16px;color:#7c897f;font-size:11px}
      .bf-preview-mobile-menu{display:none}
      @media(max-width:760px){.bf-preview-intro{align-items:start;flex-direction:column;padding-top:26px}.bf-preview-frame{grid-template-columns:1fr;min-height:0}.bf-preview-side{border-right:0;border-bottom:1px solid #e8ede8;padding:10px;display:flex;flex-direction:row;overflow:auto;gap:5px}.bf-preview-side-label,.bf-preview-side-note{display:none}.bf-preview-nav{width:auto;white-space:nowrap;padding:10px;font-size:10px}.bf-preview-main{padding:20px 14px}.bf-preview-stats{gap:7px}.bf-preview-stat{padding:11px}.bf-preview-stat strong{font-size:18px}.bf-preview-row{grid-template-columns:45px minmax(0,1fr);}.bf-preview-row .bf-preview-status{grid-column:2;justify-self:start}.bf-preview-top-actions .bf-preview-link{display:none}.bf-preview-foot{align-items:flex-start;flex-direction:column}.bf-preview-table{min-width:500px}.bf-preview-table-wrap{overflow:auto}.bf-preview-tour{align-items:flex-start;flex-direction:column}.bf-preview-demo{padding:0 12px 30px}}
    `}</style>

    <header className="bf-preview-top">
      <Link href="/" className="bf-preview-brand"><span className="bf-preview-mark"><CalendarDays size={18}/></span>BookFlow<span style={{color:"#6a9678"}}>.</span><span className="bf-preview-pill">AI</span></Link>
      <div className="bf-preview-top-actions"><span className="bf-preview-link">Interactive product preview</span><Link href="/register" className="bf-preview-cta">Create your workspace <ArrowRight size={14}/></Link></div>
    </header>

    <section className="bf-preview-intro">
      <div><span className="bf-preview-kicker">TAKE A LOOK INSIDE</span><h1>See how your business could flow.</h1><p>Explore a sample BookFlow workspace. Switch between the tools and see how appointments, customers, projects and everyday operations fit together.</p></div>
      <span className="bf-preview-pill">DEMO DATA · READ ONLY</span>
    </section>

    <section className="bf-preview-demo">
      <div className="bf-preview-frame">
        <aside className="bf-preview-side">
          <div className="bf-preview-side-label">SAMPLE WORKSPACE</div>
          {sections.map(item=>{const Icon=item.icon;return <button key={item.id} onClick={()=>setActive(item.id)} className={`bf-preview-nav ${active===item.id?"active":""}`}><Icon size={15}/>{item.label}</button>;})}
          <div className="bf-preview-side-note"><b><Sparkles size={12} style={{display:"inline",marginRight:5}}/>Built around your flow</b>Choose the tools that fit your business. This preview uses fictional sample records.</div>
        </aside>

        <div className="bf-preview-main">
          <div className="bf-preview-main-head"><div><h2>{activeItem.label}</h2><p>Willow & Sage Studio · Sample business</p></div><span className="bf-preview-date">Monday, 16 November 2026</span></div>

          {active==="overview"&&<><div className="bf-preview-stats"><div className="bf-preview-stat"><span>Appointments today</span><strong>18</strong><small>↑ 12% this week</small></div><div className="bf-preview-stat"><span>Scheduled value</span><strong>MK 486k</strong><small>Confirmed booking value</small></div><div className="bf-preview-stat"><span>New customers</span><strong>24</strong><small>Across the last 7 days</small></div></div><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b>Today&apos;s schedule</b><span>4 upcoming appointments</span></div>{bookings.slice(0,3).map(b=><div className="bf-preview-row" key={b[0]}><span className="bf-preview-time">{b[0]}</span><div><strong>{b[1]}</strong><small>{b[2]} · {b[3]}</small></div><span className={`bf-preview-status ${b[4]==="Awaiting"?"pending":""}`}>{b[4]}</span></div>)}</div><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b>Assistant overview</b><span><Sparkles size={12} style={{display:"inline"}}/> Example insight</span></div><p style={{fontSize:12,color:"#66746b",lineHeight:1.6,margin:0}}>You have 3 booking requests awaiting review and 2 payment follow-ups to check. Keep your day moving from one workspace.</p></div></>}

          {active==="calendar"&&<><div className="bf-preview-stats"><div className="bf-preview-stat"><span>Today&apos;s bookings</span><strong>18</strong><small>Across your team</small></div><div className="bf-preview-stat"><span>Awaiting review</span><strong>3</strong><small>Owner approval needed</small></div><div className="bf-preview-stat"><span>Available slots</span><strong>6</strong><small>Sample availability</small></div></div><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b>Appointment schedule</b><span>Sample day view</span></div>{bookings.map(b=><div className="bf-preview-row" key={b[0]}><span className="bf-preview-time">{b[0]}</span><div><strong>{b[1]}</strong><small>{b[2]} · {b[3]} · {b[5]}</small></div><span className={`bf-preview-status ${b[4]==="Awaiting"?"pending":""}`}>{b[4]}</span></div>)}</div><p style={{fontSize:11,color:"#819087"}}>In your live workspace, availability is checked against the service, team and resource rules configured for your business.</p></>}

          {active==="customers"&&<><div className="bf-preview-stats"><div className="bf-preview-stat"><span>Customer records</span><strong>248</strong><small>Sample total</small></div><div className="bf-preview-stat"><span>Returning customers</span><strong>68%</strong><small>Sample rate</small></div><div className="bf-preview-stat"><span>New this month</span><strong>24</strong><small>Sample total</small></div></div><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b>Recent customers</b><span>Fictional records</span></div><div className="bf-preview-table-wrap"><table className="bf-preview-table"><thead><tr><th>CUSTOMER</th><th>PHONE</th><th>VISITS</th><th>LIFETIME VALUE</th></tr></thead><tbody>{customers.map(c=><tr key={c[0]}><td><b>{c[0]}</b></td><td>{c[1]}</td><td>{c[2]}</td><td>{c[3]}</td></tr>)}</tbody></table></div></div><p style={{fontSize:11,color:"#819087"}}>Customer profiles help a business keep contact details, visits and recorded value together.</p></>}

          {active==="work"&&<><div className="bf-preview-stats"><div className="bf-preview-stat"><span>Active projects</span><strong>12</strong><small>Sample workload</small></div><div className="bf-preview-stat"><span>Awaiting review</span><strong>3</strong><small>Client feedback</small></div><div className="bf-preview-stat"><span>Due this week</span><strong>4</strong><small>Sample deadlines</small></div></div><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b>Projects & client work</b><span>Example project tracker</span></div>{projects.map(p=><div className="bf-preview-project" key={p[0]}><div><b>{p[0]}</b><small>{p[1]} · Due {p[3]}</small></div><span className="bf-preview-status pending">{p[2]}</span></div>)}</div><p style={{fontSize:11,color:"#819087"}}>Useful for photographers, designers, tailors, event planners and businesses delivering work beyond a single appointment.</p></>}

          {active==="payments"&&<><div className="bf-preview-stats"><div className="bf-preview-stat"><span>Recorded payments</span><strong>MK 362k</strong><small>Sample successful records</small></div><div className="bf-preview-stat"><span>Outstanding</span><strong>MK 124k</strong><small>Sample balance</small></div><div className="bf-preview-stat"><span>Payments pending</span><strong>5</strong><small>Sample records</small></div></div><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b>Business activity</b><span>Illustrative weekly totals</span></div>{[["Mon","8"],["Tue","12"],["Wed","10"],["Thu","16"],["Fri","13"],["Sat","18"],["Sun","7"]].map(([day,n])=><div key={day} style={{display:"grid",gridTemplateColumns:"32px 1fr 25px",alignItems:"center",gap:10,margin:"13px 0",fontSize:10,color:"#78857c"}}><span>{day}</span><div style={{height:8,background:"#edf2ed",borderRadius:8,overflow:"hidden"}}><div style={{height:"100%",width:(Number(n)/18*100)+"%",background:"#3c8057",borderRadius:8}}/></div><b>{n}</b></div>)}</div><p style={{fontSize:11,color:"#819087"}}>Your live reports distinguish scheduled booking value from payments actually recorded. Manual entries are not presented as provider-verified payments.</p></>}

          {active==="assistant"&&<><div className="bf-preview-panel"><div className="bf-preview-panel-head"><b><Sparkles size={14} style={{display:"inline",marginRight:6}}/>BookFlow assistant</b><span>Illustrative conversation</span></div><div className="bf-preview-chat"><div className="bf-preview-bubble">Hello! Welcome to Willow & Sage Studio. How can I help you today?</div><div className="bf-preview-bubble user">Hi, do you have an appointment for a haircut tomorrow?</div><div className="bf-preview-bubble">I can help check available times. Do you prefer morning or afternoon?</div><div className="bf-preview-bubble user">Morning, please.</div><div className="bf-preview-bubble">There are sample openings at 09:00 and 10:30. Which would you prefer?</div></div></div><p style={{fontSize:11,color:"#819087"}}>This is a concept demonstration, not a live WhatsApp connection or an active AI conversation. Direct WhatsApp account integration is not currently connected.</p></>}
        </div>
      </div>

      {showTour&&<div className="bf-preview-tour"><div><b>Explore the workspace · {tourStep+1} of 3</b><p>{["Start with the overview to understand the business at a glance.","Move through the workspace sections to see how daily operations connect.","Ready to use your own business data? Create a workspace to get started."][tourStep]}</p></div><div className="bf-preview-tour-actions"><button className="bf-preview-iconbtn" aria-label="Previous tour step" onClick={()=>{setTourStep(v=>Math.max(0,v-1));previous();}} disabled={tourStep===0}><ChevronLeft size={15}/></button><button className="bf-preview-iconbtn" aria-label="Next tour step" onClick={()=>{if(tourStep===2){setShowTour(false);return;}setTourStep(v=>v+1);next();}}>{tourStep===2?<X size={15}/>:<ChevronRight size={15}/>}</button></div></div>}
    </section>
    <footer className="bf-preview-foot"><span>© {new Date().getFullYear()} BookFlow AI · Sample workspace only</span><Link href="/" className="bf-preview-link"><ArrowLeft size={13} style={{display:"inline",verticalAlign:"middle"}}/> Back to BookFlow</Link></footer>
  </main>;
}
