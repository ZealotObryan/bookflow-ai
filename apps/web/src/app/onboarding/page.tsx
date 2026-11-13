"use client";
import Link from "next/link";
import {useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import {ArrowLeft,ArrowRight,CalendarDays,CheckCircle2,LoaderCircle,MessageCircle,BriefcaseBusiness,CalendarCheck,ClipboardList} from "lucide-react";
import {apiConfigured,apiRequest} from "@/lib/api";
import {useAuth} from "@/components/auth-provider";

type Business={id:string;name:string;timezone:string;currency:string;role:string;business_type:string;workflow_mode:string;whatsapp_priority:string};
const businessTypes=[
 {value:"salon",label:"Salon / beauty studio",detail:"Hair, beauty and treatment services"},
 {value:"nail_tech",label:"Nail technician",detail:"Manicures, pedicures and nail art"},
 {value:"barber",label:"Barber",detail:"Cuts, grooming and walk-ins"},
 {value:"designer_tailor",label:"Designer / tailor",detail:"Fittings, measurements and orders"},
 {value:"event_planner",label:"Event planner",detail:"Clients, events and timelines"},
 {value:"photographer",label:"Photographer / creative",detail:"Sessions, projects and deliverables"},
 {value:"fitness_wellness",label:"Fitness / wellness",detail:"Classes, coaching and sessions"},
 {value:"consultant",label:"Consultant / professional",detail:"Client meetings and service work"},
 {value:"other",label:"Other business",detail:"A flexible workspace for your work"},
];
const workflows=[
 {value:"bookings",label:"I mainly need bookings",detail:"Let customers request appointments and manage my schedule.",icon:CalendarCheck},
 {value:"tracking",label:"I mainly need business tracking",detail:"Organise customers, projects, work, payments and follow-ups.",icon:ClipboardList},
 {value:"both",label:"I need both",detail:"Manage bookings as well as the wider day-to-day business.",icon:BriefcaseBusiness},
];
const whatsappOptions=[
 {value:"essential",label:"Essential",detail:"WhatsApp should be a primary way customers contact and book me."},
 {value:"important",label:"Important",detail:"I want WhatsApp booking and updates alongside my dashboard."},
 {value:"not_now",label:"Not a priority right now",detail:"I want to start with the web workspace and connect WhatsApp later."},
];
export default function OnboardingPage(){
 const router=useRouter();const {accessToken,user,ready}=useAuth();
 const [businesses,setBusinesses]=useState<Business[]>([]);const [name,setName]=useState("");
 const [businessType,setBusinessType]=useState("salon");const [workflowMode,setWorkflowMode]=useState("both");
 const [whatsappPriority,setWhatsappPriority]=useState("important");const [step,setStep]=useState(1);
 const [error,setError]=useState("");const [busy,setBusy]=useState(false);const [loading,setLoading]=useState(true);
 useEffect(()=>{let active=true;async function load(){if(!ready)return;if(!accessToken){router.replace("/login");return;}try{const rows=await apiRequest<Business[]>("/api/v1/businesses",{},accessToken);if(active){if(rows.length>0){router.replace("/dashboard");return;}setBusinesses(rows);}}catch(e){if(active)setError(e instanceof Error?e.message:"Unable to load your businesses.");}finally{if(active)setLoading(false);}}void load();return()=>{active=false;};},[ready,accessToken,router]);
 async function create(e:React.FormEvent<HTMLFormElement>){e.preventDefault();if(!accessToken||!user?.email_verified)return;setError("");setBusy(true);try{await apiRequest<Business>("/api/v1/businesses",{method:"POST",body:JSON.stringify({name,business_type:businessType,workflow_mode:workflowMode,whatsapp_priority:whatsappPriority})},accessToken);router.push("/dashboard");}catch(err){setError(err instanceof Error?err.message:"Business setup could not be completed.");}finally{setBusy(false);}}
 if(!ready||loading)return <main className="auth-shell"><section className="auth-card"><LoaderCircle size={24}/><p>Preparing your workspace…</p></section></main>;
 if(!accessToken)return null;
 return <main className="auth-shell onboarding-shell">
  <Link className="auth-back" href="/"><ArrowLeft size={15}/> BookFlow home</Link>
  <section className="auth-card onboarding-card">
   <Link className="brand-lockup" href="/"><span className="brand-symbol"><CalendarDays size={18}/></span><span>BookFlow<span className="brand-period">.</span></span><span className="brand-ai">AI</span></Link>
   <span className="section-overline">YOUR BUSINESS, YOUR WORKFLOW</span>
   <h1>Let’s make BookFlow<br/><em>work your way.</em></h1>
   <p>{user?.email_verified?"Tell us a little about your business. We’ll use this to shape your workspace.":"Please verify your email before creating a business workspace."}</p>
   {businesses.length>0&&<div className="business-list"><span className="onboarding-subtitle">YOUR EXISTING WORKSPACES</span>{businesses.map(b=><button key={b.id} onClick={()=>router.push("/dashboard")}><span><b>{b.name}</b><small>{b.role} · {b.currency} · {b.timezone}</small></span><ArrowRight size={16}/></button>)}</div>}
   {user?.email_verified&&<form className="auth-form onboarding-form" onSubmit={create}>
    <div className="onboarding-progress"><span>STEP {step} OF 3</span><div>{[1,2,3].map(n=><i key={n} className={n<=step?"complete":""}/>)}</div></div>
    {step===1&&<section className="onboarding-step">
     <h2>First, what should we call your business?</h2>
     <label className="field"><span>Business name</span><input value={name} onChange={e=>setName(e.target.value)} minLength={2} maxLength={160} required placeholder="e.g. The Green Room Studio"/></label>
     <span className="onboarding-subtitle">WHAT KIND OF BUSINESS DO YOU RUN?</span>
     <div className="onboarding-choice-grid">{businessTypes.map(item=><button type="button" key={item.value} className={"onboarding-choice "+(businessType===item.value?"selected":"")} aria-pressed={businessType===item.value} onClick={()=>setBusinessType(item.value)}><b>{item.label}</b><small>{item.detail}</small></button>)}</div>
    </section>}
    {step===2&&<section className="onboarding-step">
     <h2>How do you want to use BookFlow?</h2>
     <p>There’s no wrong answer. You can change how you work as your business grows.</p>
     <div className="onboarding-option-list">{workflows.map(item=>{const Icon=item.icon;return <button type="button" key={item.value} className={"onboarding-option "+(workflowMode===item.value?"selected":"")} aria-pressed={workflowMode===item.value} onClick={()=>setWorkflowMode(item.value)}><span className="onboarding-option-icon"><Icon size={19}/></span><span><b>{item.label}</b><small>{item.detail}</small></span><i/></button>;})}</div>
    </section>}
    {step===3&&<section className="onboarding-step">
     <h2>How important is WhatsApp to your business?</h2>
     <p>We’re building WhatsApp as a key way for customers to interact with businesses on BookFlow. This helps us understand your priorities.</p>
     <div className="onboarding-option-list">{whatsappOptions.map(item=><button type="button" key={item.value} className={"onboarding-option "+(whatsappPriority===item.value?"selected":"")} aria-pressed={whatsappPriority===item.value} onClick={()=>setWhatsappPriority(item.value)}><span className="onboarding-option-icon whatsapp"><MessageCircle size={19}/></span><span><b>{item.label}</b><small>{item.detail}</small></span><i/></button>)}</div>
     <div className="onboarding-summary"><b><CheckCircle2 size={15}/> Your workspace will be set up for:</b><span>{businessTypes.find(x=>x.value===businessType)?.label} · {workflows.find(x=>x.value===workflowMode)?.label} · WhatsApp: {whatsappOptions.find(x=>x.value===whatsappPriority)?.label}</span></div>
    </section>}
    {error&&<p className="form-error" role="alert">{error}</p>}
    <div className="onboarding-actions">{step>1&&<button type="button" className="button button-outline" onClick={()=>setStep(s=>s-1)}><ArrowLeft size={14}/> Back</button>}{step<3?<button type="button" className="button button-primary" disabled={step===1&&name.trim().length<2} onClick={()=>setStep(s=>s+1)}>Continue <ArrowRight size={14}/></button>:<button className="button button-primary" disabled={busy||!apiConfigured}>{busy?"Creating workspace…":"Create my workspace"} <ArrowRight size={14}/></button>}</div>
   </form>}
   {!user?.email_verified&&<div className="auth-preview-notice">Check your inbox for the verification email. You can return to sign in after verifying.</div>}
   <div className="auth-note"><CheckCircle2 size={15}/> New workspaces use Malawi Kwacha and Africa/Blantyre by default.</div>
  </section>
  <span className="auth-footer">© {new Date().getFullYear()} BookFlow AI</span>
 </main>;
}
