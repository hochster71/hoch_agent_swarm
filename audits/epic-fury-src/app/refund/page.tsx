/**
 * /refund — Refund & Cancellation Policy.
 *
 * A published refund policy is a HARD REQUIREMENT for a merchant of record (Lemon
 * Squeezy / Stripe MoR) and one of the most common reasons an application is rejected.
 *
 * It also has to be TRUE. The MoR is the legal seller: if this page promises something
 * the operator will not honour, the MoR eats the chargeback and terminates the account.
 * Keep it honest, and keep it matched to what the store is actually configured to do.
 */
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

export const metadata = {
  title: 'Refund & Cancellation Policy',
  description: 'Refund and cancellation terms for Epic Fury subscriptions.',
}

const SUPPORT_EMAIL = 'michael.b.hoch@gmail.com'

export default function RefundPolicyPage() {
  return (
    <div className="min-h-screen bg-zinc-950 font-mono text-zinc-100">
      <div className="mx-auto max-w-3xl space-y-8 px-6 py-12">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs text-zinc-400 transition-colors hover:text-white"
        >
          <ArrowLeft size={12} /> Back
        </Link>

        <header className="border-b border-zinc-800 pb-4">
          <h1 className="text-2xl font-bold uppercase tracking-widest text-emerald-300">
            Refund &amp; Cancellation Policy
          </h1>
          <p className="mt-2 text-[11px] uppercase tracking-widest text-zinc-500">
            Last updated 13 July 2026
          </p>
        </header>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400">
            1. What you are buying
          </h2>
          <p className="text-xs leading-relaxed text-zinc-400">
            An Epic Fury subscription grants access to a{' '}
            <strong className="text-zinc-200">conflict-modeling and analysis web application</strong>.
            Most figures in the product are{' '}
            <strong className="text-amber-400">projections produced by a model</strong> — they are not
            live reporting and are not verified current intelligence. Views backed by a live ingested
            source are labelled as such on the page. Please read the{' '}
            <Link href="/terms" className="text-emerald-400 hover:underline">
              Terms
            </Link>{' '}
            before you subscribe.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400">
            2. 14-day refund
          </h2>
          <p className="text-xs leading-relaxed text-zinc-400">
            If Epic Fury is not what you expected, email{' '}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-emerald-400 hover:underline">
              {SUPPORT_EMAIL}
            </a>{' '}
            within <strong className="text-zinc-200">14 days</strong> of your first payment and we
            will refund it in full. No justification required. We would rather return your money than
            keep a subscriber who feels misled.
          </p>
          <p className="text-xs leading-relaxed text-zinc-400">
            Refunds are issued to the original payment method by our merchant of record and typically
            appear within 5–10 business days, depending on your bank.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400">
            3. Cancellation
          </h2>
          <p className="text-xs leading-relaxed text-zinc-400">
            You may cancel at any time from your account settings, or by emailing{' '}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-emerald-400 hover:underline">
              {SUPPORT_EMAIL}
            </a>
            . Cancelling stops all future billing. You keep access until the end of the period you
            have already paid for.{' '}
            <strong className="text-zinc-200">We do not bill you again after you cancel</strong>, and
            we do not make you phone anyone to do it.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400">
            4. Renewals
          </h2>
          <p className="text-xs leading-relaxed text-zinc-400">
            Monthly subscriptions renew monthly; annual subscriptions renew annually, at the price
            shown to you at checkout. If the price ever changes, existing subscribers are notified
            before it takes effect and may cancel first.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-[11px] font-bold uppercase tracking-widest text-zinc-400">
            5. If something is wrong
          </h2>
          <p className="text-xs leading-relaxed text-zinc-400">
            If you were charged in error, charged twice, or charged after cancelling, email{' '}
            <a href={`mailto:${SUPPORT_EMAIL}`} className="text-emerald-400 hover:underline">
              {SUPPORT_EMAIL}
            </a>{' '}
            and we will refund it — including outside the 14-day window. A billing mistake is our
            problem, not yours.
          </p>
        </section>

        <footer className="border-t border-zinc-800 pt-6">
          <p className="text-[10px] uppercase tracking-widest text-zinc-600">
            Payments are processed by <strong className="text-zinc-300">Stripe</strong> acting as our
            merchant of record. Your purchase will appear on your statement as{' '}
            <strong className="text-zinc-300">LINK.COM* EPIC FURY</strong> and your receipt will come
            from Link — this is expected, and it is us. You can also manage or cancel your
            subscription at any time at{' '}
            <a href="https://link.com" className="text-emerald-400 hover:underline">link.com</a>.
          </p>
        </footer>
      </div>
    </div>
  )
}
