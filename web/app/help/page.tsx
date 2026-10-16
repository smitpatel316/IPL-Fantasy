/* P5-W11: how-to-play guide. Every rule statement on this page is
   traced to a locked decision in DECISIONS.md (D1–D11) — the source
   is named on each section so QA can re-check the copy. Nothing here
   is invented; where a mechanic comes from the blueprint rather than
   a D-item (can't-cut list), that is said too. */

import Link from "next/link";
import { PageHeader } from "@/components/ui";

function Section({
  title,
  source,
  children,
}: {
  title: string;
  source: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-slate-800 bg-midnight-soft p-5">
      <h2 className="text-sm font-bold uppercase tracking-wider text-zinc-200">
        {title}
        <span className="ml-2 text-[11px] font-medium normal-case tracking-normal text-zinc-500">
          {source}
        </span>
      </h2>
      <div className="mt-3 space-y-2 text-sm leading-relaxed text-zinc-300">
        {children}
      </div>
    </section>
  );
}

export default function HelpPage() {
  return (
    <div>
      <PageHeader
        title="How to play"
        sub="The locked rules of this league, in manager language — no surprises mid-season"
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Section title="The draft" source="D2 · D7">
          <p>
            We draft <strong>snake style</strong>: the order reverses every round, so the
            manager who picks last in round 1 picks first in round 2. The draft runs{" "}
            <strong>14 rounds</strong> with a pick clock — if your clock expires, auto-pick
            takes the best player from your custom ranks (or the league consensus ranks if
            you never set yours). A do-not-draft list keeps auto-pick away from players you
            never want.
          </p>
        </Section>

        <Section title="Your roster" source="D7">
          <p>
            Rosters hold <strong>15 players: 11 starters</strong> — 1 wicket-keeper (WK),
            3 batters (BAT), 2 all-rounders (AR), 3 bowlers (BOWL) and 2 utility (UTIL) —{" "}
            plus <strong>3 bench (BN)</strong> and <strong>1 injured list (IL)</strong> spot.
          </p>
          <p>
            The IL spot is never filled during the draft. After the draft, a player who has
            missed — or is expected to miss — a game is IL-eligible; moving him to IL frees
            a roster spot for a pickup.
          </p>
        </Section>

        <Section title="The overseas rule" source="D8">
          <p>
            At most <strong>4 overseas players</strong> may be in your 11 starters each
            week — the real IPL rule. Bench and IL players don't count against the cap;
            only the starting XI does.
          </p>
        </Section>

        <Section title="Scoring" source="D3 · D11">
          <p>
            Scoring uses the <strong>standard T20 fantasy points table</strong> — runs,
            wickets, catches, strike-rate and economy bonuses, and the rest of the usual
            table. There are <strong>no captain or vice-captain multipliers</strong>:
            every starter scores face value. Points are tallied at the end of each match,
            not ball by ball.
          </p>
        </Section>

        <Section title="Weekly matchups & lineup lock" source="D4 · D5">
          <p>
            Each week (Monday–Sunday) you face one other manager head-to-head; your
            starters' points decide the winner. You set your XI <strong>once per week</strong>{" "}
            — lineups lock at the week's first ball, so there are no daily 7am alarms even
            though matches start in the evening in India.
          </p>
        </Section>

        <Section title="Waivers & FAAB" source="D6">
          <p>
            Free agents are claimed with <strong>FAAB: a $100 budget for the whole
            season</strong>. Bids are <strong>blind</strong> — nobody sees your bid, and
            you never see rivals' bids — and claims run every{" "}
            <strong>Wednesday around 3am PT</strong>. The highest bid wins the player and
            pays their bid; ties go to the team lower in the standings. Dropped players
            sit in a 2-day freeze before they can be claimed.
          </p>
          <p>
            Some stars sit on the <strong>can't-cut list</strong> and can't be dropped to
            the wire at all — it protects the league from dump trades (set by the
            commissioner; by default it covers the top preseason-ranked players).
          </p>
        </Section>

        <Section title="Trades" source="blueprint §6.4 · league settings">
          <p>
            Trades are <strong>player-for-player, equal numbers each side</strong>. The
            other manager accepts or rejects; accepted trades sit in a{" "}
            <strong>2-day commissioner review window</strong> during which the league can
            veto (one-third of the non-involved teams vetoes a deal). The trade deadline
            is the <strong>end of week 6</strong> — after that, rosters move only through
            waivers. Shopping a player? Put him on the <strong>trade block</strong> on the
            Trades page with a note on what you want back.
          </p>
        </Section>

        <Section title="Schedule luck" source="D10">
          <p>
            IPL teams don't all play the same number of matches in a fantasy week. The
            draft room and waiver wire show <strong>games-per-week badges</strong> per IPL
            team, so schedule is a skill you can draft and bid around — not hidden noise.
          </p>
        </Section>

        <Section title="Playoffs" source="D9">
          <p>
            The top <strong>4 teams</strong> make the playoffs in <strong>weeks 7–8</strong>{" "}
            (semifinals, then the final). The fantasy season ends before the real IPL
            playoffs, while every team still has a full squad to pick from.
          </p>
        </Section>

        <Section title="Your first week" source="the walkthrough">
          <ol className="list-decimal space-y-1.5 pl-5">
            <li>
              <strong>Claim your team</strong> — open your{" "}
              <Link href="/league/1" className="font-semibold text-pitch-green hover:underline">
                league page
              </Link>{" "}
              and claim your team in the standings so only you can manage it.
            </li>
            <li>
              <strong>Set your ranks</strong> — order the draft board your way in the draft
              room; auto-pick follows your list when your clock runs out.
            </li>
            <li>
              <strong>Run a mock draft</strong> — practice against sharp and casual bots
              from the league page; your real league is never touched.
            </li>
            <li>
              <strong>Set your lineup</strong> — after the real draft, save your week-1 XI
              before the first ball, then work the waiver wire every Wednesday.
            </li>
          </ol>
        </Section>
      </div>
    </div>
  );
}
