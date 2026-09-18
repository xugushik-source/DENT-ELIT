# CLAUDE.md — ORDER PROFIT house style / ELIT DENT engine

Read this before doing anything else in this repo, and before setting up a new repo
for a different ORDER PROFIT client or vertical.

## Infra workflow — read before touching git remotes or hosting

**Never create a GitHub repository, Vercel project, or any other piece of
infrastructure on your own initiative for this line of work.** The client/agency
(the user) creates every repository manually and hands it to you — adds it to the
session, gives you a clone URL, whatever the mechanism. Your job starts once you have
a repo in hand: build into it and push. You do not provision the container yourself,
ever, even if it would be faster to just create one. If you don't have a repo yet,
say so and wait — don't improvise one.

This is a standing rule for the whole ORDER PROFIT line of work, not just ELIT DENT.

## This is a house style, not just a dental template

The reusable part of this codebase is two separate layers:

1. **The ORDER PROFIT visual/interaction system** — palette-driven design tokens,
   type scale, the component set (header/footer/nav/cards/buttons/modal), the
   full-screen session-gated intro splash (client's real logo, fades in then out,
   plays once per browser session), scroll-reveal-on-view animation on every section
   (`IntersectionObserver`, staggered, `prefers-reduced-motion`-safe), breadcrumb
   navigation on every page, the mobile bottom bar + floating WhatsApp button +
   booking modal with server-rendered `wa.me` links. **This layer is vertical-agnostic.**
   If asked to make a restaurant site, a hotel site, anything else "look and feel like
   ELIT DENT," this is what gets carried over — the look, the transitions, the
   navigation mechanics — not the dental content.
2. **The dental data schema** — doctors, services, technology, the specific page set
   built around them. This layer is what changes shape for a different vertical (a
   restaurant needs a menu/dishes schema and different page types; a hotel needs
   rooms/amenities/booking-by-date, etc.) — it is not "reusable as-is" the way layer 1
   is, and building it for a new vertical is real design work, not just data entry.

See `CUSTOMIZATION_GUIDE.md`'s "replication contract" section for the detailed
variable-vs-mechanical breakdown — it's framed around "the next clinic," but the same
split (swap data/content, never touch the mechanics list) applies when porting layer 1
to a different vertical too.

## How this actually got built — the repeatable shape for the next site

1. **Get the repo and the client's real assets first.** Real logo files (never invent
   or redesign one — technical prep only: crop/resize/recompress exactly what's
   supplied) and real photography. No placeholder logo, no stock-photo-as-permanent
   content.
2. **Build the data model before templates.** `data/site.json` (brand/contact/SEO/
   feature flags) first, then the vertical-specific structured data (`doctors.json`/
   `services.json`/`technology.json` for a clinic — different nouns for a different
   vertical), `content/{lang}.json` for UI strings, `reviews.json`.
3. **Build the Jinja2 pipeline**: `build.py`, directory-style URLs, `base.html` +
   shared partials (header/footer/mobile-nav/booking-modal/bottom-bar/whatsapp-float/
   breadcrumb), one page template per content type.
4. **Build the design system**: `tokens.css` (palette + type — the *only* layer that's
   supposed to differ per client) and `main.css` (component structure, shared).
5. **Build the interaction layer**: scroll-reveal, mobile nav with a real focus trap,
   the booking modal (server-side `wa_url()` for every static link, client-side
   message-template interpolation for the live form submission), the intro splash.
   **The visitor's phone number must reach the WhatsApp message** — this specific
   thing broke once already; treat it as the one mechanic that gets end-to-end
   verified, not just read, on every new build.
6. **SEO machinery**: `SITE_URL` env var with a `productionUrl` fallback, canonical/
   hreflang/OG/sitemap/robots, structured data, and a `demoMode` flag that forbids
   fabricated schema (`AggregateRating` etc.) while content is still fictional/demo.
7. **Write (or reuse) `validate.py`**: broken links/images, leftover placeholder text,
   per-language content parity, cross-file numeric consistency (counts in `stats` vs.
   the actual data). Every new site gets "PASSED: 0 errors" before it ships, no
   exceptions.
8. **Do real browser QA before calling anything done** — run the built site locally
   (dev server or `python3 -m http.server`) and drive it with Playwright: actual
   scroll-throughs, not just a `full_page` screenshot (its `IntersectionObserver`
   blind spot produced a false "everything's blank" scare once — verify with a real
   scroll before reporting a visual bug). Verify the WhatsApp payload by intercepting
   `window.open`'s argument, not by reading the JS and assuming it's right.
9. **Commit with a message that explains why, push to `main`**, then verify the
   Vercel deployment through the Vercel MCP tools (`get_deployment`/
   `list_deployments`) instead of assuming a push went live.
10. **Write the docs as part of the deliverable**: an audit doc (what was found, what
    was fixed, what was a deliberate trade-off — see `AUDIT_V2.md`'s shape) and a
    replication contract (`CUSTOMIZATION_GUIDE.md`'s shape) aren't an afterthought,
    they're what makes step-1-for-the-next-site fast instead of a re-discovery.

## Known limitation: this file's reach

This `CLAUDE.md` is only read automatically by sessions working *in this repository*.
A brand-new repository the user creates for a different client or vertical starts with
none of this context — nothing here carries over on its own. When handed a new repo,
bring this playbook forward deliberately (copy the relevant sections into that repo's
own `CLAUDE.md`, or ask to be pointed back here) rather than assuming it persists
automatically.
