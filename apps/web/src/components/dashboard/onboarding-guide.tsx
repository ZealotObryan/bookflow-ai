"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Check, ChevronRight, Circle, RotateCcw, Sparkles } from "lucide-react";
import { apiRequest } from "@/lib/api";

type Progress = {
  business_id: string;
  completed_steps: string[];
  dismissed: boolean;
  updated_at: string;
};

type Props = {
  businessId: string;
  accessToken: string;
  workflowMode: "bookings" | "tracking" | "both";
  businessType: string;
};

const steps = [
  { id: "business_profile", title: "Review your business profile", detail: "Check your business name, type and workspace preferences.", href: "/dashboard/settings", modes: ["bookings", "tracking", "both"] },
  { id: "services", title: "Add your services or packages", detail: "Set the services, packages or work types you offer.", href: "/dashboard/services", modes: ["bookings", "both"] },
  { id: "availability", title: "Set your availability", detail: "Prepare the hours customers can request appointments.", href: "/dashboard/settings", modes: ["bookings", "both"] },
  { id: "team", title: "Set up your team and resources", detail: "Add the people, rooms or equipment needed for your work.", href: "/dashboard/team", modes: ["bookings", "both"] },
  { id: "first_booking", title: "Create your first booking", detail: "Create a booking hold and review it before confirming.", href: "/dashboard/bookings", modes: ["bookings", "both"] },
  { id: "first_project", title: "Create your first project", detail: "Track a client, deliverables, dates and payments.", href: "/dashboard/projects", modes: ["tracking", "both"] },
  { id: "payments", title: "Review payment setup", detail: "Prepare deposits, balances and payment collection.", href: "/dashboard/payments", modes: ["bookings", "tracking", "both"] },
  { id: "whatsapp", title: "Review WhatsApp preferences", detail: "Choose how customers should contact your business.", href: "/dashboard/settings", modes: ["bookings", "tracking", "both"] },
] as const;

export default function OnboardingGuide({ businessId, accessToken, workflowMode, businessType }: Props) {
  const [progress, setProgress] = useState<Progress | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const visibleSteps = useMemo(
    () => steps.filter((step) => (step.modes as readonly string[]).includes(workflowMode)),
    [workflowMode],
  );

  useEffect(() => {
    let active = true;
    setLoading(true);
    apiRequest<Progress>(`/api/v1/businesses/${businessId}/onboarding`, {}, accessToken)
      .then((value) => { if (active) setProgress(value); })
      .catch((err) => { if (active) setError(err instanceof Error ? err.message : "Onboarding could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [businessId, accessToken]);

  async function save(next: string[], dismissed: boolean) {
    if (!progress) return;
    setSaving(true);
    setError("");
    try {
      const updated = await apiRequest<Progress>(`/api/v1/businesses/${businessId}/onboarding`, {
        method: "PUT",
        body: JSON.stringify({ completed_steps: next, dismissed }),
      }, accessToken);
      setProgress(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Your progress could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !progress) {
    return <section className="panel" aria-live="polite">{loading ? "Preparing your setup checklist…" : error || "Setup checklist is unavailable."}</section>;
  }

  const completed = visibleSteps.filter((step) => progress.completed_steps.includes(step.id)).length;
  const percent = Math.round((completed / visibleSteps.length) * 100);
  const isPhotography = businessType === "photographer";

  if (progress.dismissed) {
    return <section className="panel" style={{ marginBottom: 20, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16 }}>
      <span><b>Setup checklist paused</b><small style={{ display: "block", color: "var(--muted)" }}>{completed} of {visibleSteps.length} steps completed</small></span>
      <button className="button button-outline button-small" disabled={saving} onClick={() => save(progress.completed_steps, false)}><RotateCcw size={14} /> Resume setup</button>
    </section>;
  }

  return <section className="panel" style={{ marginBottom: 20 }}>
    <div className="panel-head">
      <div>
        <span className="section-overline"><Sparkles size={13} /> YOUR FIRST STEPS</span>
        <h2>Let’s get your workspace ready</h2>
        <p>{isPhotography ? "Set up your photography workflow, from client enquiry to final delivery." : workflowMode === "tracking" ? "A few quick steps will prepare your client and project workspace." : "Complete these steps to start managing your business with BookFlow."}</p>
      </div>
      <button className="button button-outline button-small" disabled={saving} onClick={() => save(progress.completed_steps, true)}>Pause checklist</button>
    </div>
    <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "8px 0 16px" }}>
      <div style={{ flex: 1, height: 7, borderRadius: 10, background: "var(--border)", overflow: "hidden" }}>
        <div style={{ width: percent + "%", height: "100%", background: "var(--accent)", transition: "width .2s ease" }} />
      </div>
      <b style={{ whiteSpace: "nowrap", fontSize: 13 }}>{completed}/{visibleSteps.length} complete</b>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 10 }}>
      {visibleSteps.map((step) => {
        const done = progress.completed_steps.includes(step.id);
        return <div key={step.id} style={{ border: "1px solid var(--border)", borderRadius: 12, padding: 13, display: "flex", alignItems: "flex-start", gap: 10 }}>
          <span style={{ color: done ? "var(--success)" : "var(--muted)", paddingTop: 2 }}>{done ? <Check size={17} /> : <Circle size={17} />}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <b style={{ display: "block", fontSize: 13 }}>{step.title}</b>
            <small style={{ display: "block", color: "var(--muted)", lineHeight: 1.5, margin: "4px 0 9px" }}>{step.detail}</small>
            <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
              <Link href={step.href} style={{ fontSize: 12, fontWeight: 600, color: "var(--accent)" }}>Open <ChevronRight size={12} style={{ display: "inline" }} /></Link>
              <button type="button" disabled={saving} onClick={() => save(done ? progress.completed_steps.filter((id) => id !== step.id) : [...progress.completed_steps, step.id], false)} style={{ border: 0, padding: 0, background: "transparent", color: "var(--muted)", fontSize: 11, cursor: saving ? "wait" : "pointer" }}>{done ? "Undo" : "Mark complete"}</button>
            </div>
          </div>
        </div>;
      })}
    </div>
    {error && <p role="alert" style={{ color: "var(--danger)", fontSize: 12, marginTop: 12 }}>{error}</p>}
    {completed === visibleSteps.length && <p style={{ color: "var(--success)", fontWeight: 600, fontSize: 13, marginTop: 14 }}>Your initial setup checklist is complete. You can revisit it any time.</p>}
  </section>;
}
