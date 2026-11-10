"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { API_BASE } from "@/lib/api";

type PublicService = {
  id: string;
  name: string;
  description: string | null;
  duration_minutes: number;
  price_amount: string;
  currency: string;
};
type PublicBusiness = {
  name: string;
  slug: string;
  business_type: string;
  timezone: string;
  currency: string;
  services: PublicService[];
};
type Slot = { starts_at: string; ends_at: string; employee_id: string | null };

function localDateValue() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}
function money(value: string, currency: string) {
  return new Intl.NumberFormat("en", { style: "currency", currency, maximumFractionDigits: 2 }).format(Number(value));
}

export default function PublicBookingPage() {
  const params = useParams<{ slug: string }>();
  const slug = params.slug;
  const [business, setBusiness] = useState<PublicBusiness | null>(null);
  const [selectedService, setSelectedService] = useState("");
  const [date, setDate] = useState(localDateValue);
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading, setLoading] = useState(true);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedSlot, setSelectedSlot] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    async function loadBusiness() {
      setLoading(true);
      setError("");
      try {
        if (!API_BASE) throw new Error("Online booking is not connected yet. Please contact the business directly.");
        const response = await fetch(`${API_BASE}/api/v1/public/businesses/${encodeURIComponent(slug)}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "This booking page could not be found.");
        const profile = body as PublicBusiness;
        setBusiness(profile);
        setSelectedService(profile.services[0]?.id ?? "");
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Unable to load this business.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    if (slug) void loadBusiness();
    return () => controller.abort();
  }, [slug]);

  useEffect(() => {
    if (!business || !selectedService || !date || !API_BASE) {
      setSlots([]);
      return;
    }
    const controller = new AbortController();
    async function loadSlots() {
      setSlotsLoading(true);
      setSelectedSlot("");
      setError("");
      try {
        const query = new URLSearchParams({ service_id: selectedService, date, slot_interval_minutes: "15" });
        const response = await fetch(`${API_BASE}/api/v1/public/businesses/${encodeURIComponent(slug)}/availability?${query}`, {
          cache: "no-store",
          signal: controller.signal,
        });
        const body = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(body.detail || "Availability could not be loaded.");
        setSlots((body.slots ?? []) as Slot[]);
      } catch (err) {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : "Availability could not be loaded.");
      } finally {
        if (!controller.signal.aborted) setSlotsLoading(false);
      }
    }
    void loadSlots();
    return () => controller.abort();
  }, [business, selectedService, date, slug]);

  if (loading) return <main className="marketing-shell" style={{ paddingTop: 100 }}><p>Loading booking page…</p></main>;
  if (error && !business) return <main className="marketing-shell" style={{ paddingTop: 100 }}><h1>Booking page unavailable</h1><p>{error}</p><Link className="text-link" href="/">Back to BookFlow</Link></main>;

  const service = business?.services.find((item) => item.id === selectedService);
  return (
    <main className="marketing-shell" style={{ maxWidth: 760, paddingBottom: 80 }}>
      <header className="marketing-nav">
        <Link className="brand-lockup" href="/"><span className="brand-symbol">B</span><span>BookFlow<span className="brand-period">.</span></span><span className="brand-ai">Ai</span></Link>
        <span className="nav-login">SECURE ONLINE BOOKING</span>
      </header>
      <section style={{ padding: "64px 0 28px" }}>
        <span className="section-overline">BOOK AN APPOINTMENT</span>
        <h1 style={{ font: "800 clamp(34px, 6vw, 54px) Manrope, sans-serif", letterSpacing: "-2px", margin: "12px 0" }}>{business?.name}</h1>
        <p style={{ color: "#78837d", margin: 0 }}>Choose a service and find a time that works for you.</p>
      </section>
      {error && <p role="alert" style={{ color: "#a33", background: "#fff1ef", padding: 12, borderRadius: 8 }}>{error}</p>}
      <section style={{ background: "#fff", border: "1px solid #e8ece7", borderRadius: 16, padding: 24, boxShadow: "0 18px 60px rgba(31,55,42,.05)" }}>
        <label htmlFor="service" className="section-overline">01 — CHOOSE A SERVICE</label>
        {business?.services.length ? (
          <div style={{ display: "grid", gap: 10, marginTop: 14 }}>
            {business.services.map((item) => (
              <button key={item.id} type="button" onClick={() => setSelectedService(item.id)} aria-pressed={selectedService === item.id}
                style={{ textAlign: "left", padding: 16, borderRadius: 10, border: selectedService === item.id ? "1.5px solid #23684e" : "1px solid #e8ece7", background: selectedService === item.id ? "#f1f7f2" : "#fff", color: "#182720" }}>
                <span style={{ display: "flex", justifyContent: "space-between", gap: 12, fontWeight: 700 }}><span>{item.name}</span><span>{money(item.price_amount, item.currency)}</span></span>
                <span style={{ display: "block", color: "#78837d", fontSize: 12, marginTop: 6 }}>{item.duration_minutes} minutes{item.description ? ` · ${item.description}` : ""}</span>
              </button>
            ))}
          </div>
        ) : <p style={{ color: "#78837d" }}>This business has not published any bookable services yet.</p>}
        <div style={{ marginTop: 28 }}>
          <label htmlFor="booking-date" className="section-overline">02 — CHOOSE A DATE</label>
          <input id="booking-date" type="date" min={localDateValue()} value={date} onChange={(event) => setDate(event.target.value)}
            style={{ display: "block", marginTop: 12, width: "100%", maxWidth: 280, padding: 13, border: "1px solid #dfe6df", borderRadius: 9, color: "#182720", background: "#fff" }} />
        </div>
        <div style={{ marginTop: 28 }}>
          <span className="section-overline">03 — AVAILABLE TIMES</span>
          {slotsLoading ? <p style={{ color: "#78837d" }}>Checking availability…</p> : slots.length ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 9, marginTop: 14 }}>
              {slots.map((slot) => {
                const value = new Intl.DateTimeFormat("en-GB", { timeZone: business?.timezone, hour: "2-digit", minute: "2-digit" }).format(new Date(slot.starts_at));
                return <button key={slot.starts_at} type="button" aria-pressed={selectedSlot === slot.starts_at} onClick={() => setSelectedSlot(slot.starts_at)}
                  style={{ border: selectedSlot === slot.starts_at ? "1.5px solid #23684e" : "1px solid #dfe6df", borderRadius: 8, padding: "10px 15px", background: selectedSlot === slot.starts_at ? "#eaf3ed" : "#fff", color: "#23684e", fontWeight: 700 }}>{value}</button>;
              })}
            </div>
          ) : <p style={{ color: "#78837d" }}>{selectedService ? "No available times for this date. Try another day." : "Choose a service to see available times."}</p>}
        </div>
        <div style={{ marginTop: 30, padding: 16, borderRadius: 10, background: "#f6f8f5", border: "1px solid #e8ece7" }}>
          <strong style={{ display: "block", fontSize: 13 }}>Booking requests are being prepared</strong>
          <p style={{ color: "#78837d", fontSize: 12, lineHeight: 1.6, margin: "6px 0 0" }}>You can preview services and availability here. Online booking submission will be enabled once customer verification and booking protection are connected.</p>
        </div>
        {service && selectedSlot && <p style={{ color: "#23684e", fontSize: 12, marginBottom: 0 }}>Selected: {service.name} · {new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: business?.timezone }).format(new Date(date + "T12:00:00"))} · {new Intl.DateTimeFormat("en-GB", { timeZone: business?.timezone, hour: "2-digit", minute: "2-digit" }).format(new Date(selectedSlot))}</p>}
      </section>
      <p style={{ textAlign: "center", color: "#9aa39d", fontSize: 11, marginTop: 24 }}>Powered by BookFlow Ai</p>
    </main>
  );
}
