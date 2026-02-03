import { useEffect, useRef, useState } from "react";

const isValidName = (v: string) => /^[A-Za-zÀ-ÖØ-öø-ÿ' -]{2,100}$/.test(v.trim());

export default function Contact() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [errors, setErrors] = useState<{ name?: string; email?: string; message?: string }>({});
  const [status, setStatus] = useState<{ kind: "idle" | "loading" | "success" | "failure"; text?: string }>({ kind: "idle" });
  const honeypot = useRef<HTMLInputElement | null>(null);

  const validate = () => {
    const next: typeof errors = {};
    if (!name.trim()) next.name = "Name is required.";
    else if (!isValidName(name)) next.name = "Use letters, spaces, apostrophes, hyphens.";
    if (!email.trim()) next.email = "Email is required.";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) next.email = "Enter a valid email.";
    if (!message.trim()) next.message = "Message is required.";
    else if (message.trim().length < 10) next.message = "At least 10 characters.";
    setErrors(next);
    return Object.keys(next).length === 0;
  };

  useEffect(() => {
    // reset status on input changes
    if (status.kind !== "idle") setStatus({ kind: "idle" });
  }, [name, email, message]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (honeypot.current && honeypot.current.value.trim()) {
      setStatus({ kind: "failure", text: "Submission blocked." });
      return;
    }
    if (!validate()) return;

    setStatus({ kind: "loading", text: "Submitting…" });
    try {
      const res = await fetch("/api/form", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name.trim(), email: email.trim(), message: message.trim() }),
      });
      if (!res.ok) throw new Error(await res.text());
      setStatus({ kind: "success", text: "Thanks! Your message was sent." });
      setName(""); setEmail(""); setMessage("");
    } catch (err: any) {
      setStatus({ kind: "failure", text: `Failed to submit: ${err?.message || "Unknown error"}` });
    }
  };

  const canSubmit = name && email && message && Object.keys(errors).length === 0;

  return (
    <div className="min-h-screen bg-slate-950 text-zinc-100 flex items-start justify-center p-6">
      <main className="w-full max-w-2xl bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <h1 className="text-xl font-semibold">Form Submission in HTML</h1>
        <p className="text-zinc-400 text-sm">Accessible, validated, responsive, and backend-integrated.</p>
        <form className="mt-4 space-y-4" onSubmit={onSubmit} noValidate>
          {/* Honeypot */}
          <div className="sr-only">
            <label htmlFor="company">Company</label>
            <input id="company" name="company" ref={honeypot} />
          </div>

          <div>
            <label htmlFor="name" className="font-medium">Name</label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Ada Lovelace"
              className="mt-1 w-full rounded-md bg-slate-950 border border-slate-800 px-3 py-2 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20"
            />
            <div className="text-zinc-400 text-xs mt-1">Letters, spaces, apostrophes, hyphens only.</div>
            <div className="text-red-400 text-xs mt-1 min-h-[1.25rem]" aria-live="polite">{errors.name}</div>
          </div>

          <div>
            <label htmlFor="email" className="font-medium">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ada@example.com"
              className="mt-1 w-full rounded-md bg-slate-950 border border-slate-800 px-3 py-2 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20"
            />
            <div className="text-zinc-400 text-xs mt-1">We’ll only use this to respond.</div>
            <div className="text-red-400 text-xs mt-1 min-h-[1.25rem]" aria-live="polite">{errors.email}</div>
          </div>

          <div>
            <label htmlFor="message" className="font-medium">Message</label>
            <textarea
              id="message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="How can we help?"
              rows={6}
              className="mt-1 w-full rounded-md bg-slate-950 border border-slate-800 px-3 py-2 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-400/20"
            />
            <div className="text-zinc-400 text-xs mt-1">Min 10 characters; be as specific as you like.</div>
            <div className="text-red-400 text-xs mt-1 min-h-[1.25rem]" aria-live="polite">{errors.message}</div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={!canSubmit || status.kind === "loading"}
              className="rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-60 px-4 py-2 font-semibold"
            >{status.kind === "loading" ? "Submitting…" : "Submit"}</button>
            <span className={`text-sm min-h-[1.5rem] ${status.kind === "success" ? "text-green-400" : status.kind === "failure" ? "text-red-400" : "text-zinc-300"}`} aria-live="polite">
              {status.text}
            </span>
          </div>
        </form>
      </main>
    </div>
  );
}
