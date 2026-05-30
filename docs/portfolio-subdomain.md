# Portfolio subdomain: `rate-limiter.kaustuvbasak.com`

This guide wires the Render deploy into your portfolio the same way as `dns.kaustuvbasak.com` and `hvac.kaustuvbasak.com`.

## 1. Render — custom domain

The Blueprint already declares the domain in `render.yaml`:

```yaml
domains:
  - rate-limiter.kaustuvbasak.com
```

After pushing to `deploy`:

1. Open [Render Dashboard](https://dashboard.render.com/) → service **rate-limiter** → **Settings** → **Custom Domains**.
2. Confirm `rate-limiter.kaustuvbasak.com` appears (or click **Sync Blueprint** if it does not).
3. Render shows the DNS record to add. It will look like:

| Type  | Name            | Target                          |
|-------|-----------------|---------------------------------|
| CNAME | `rate-limiter`  | `rate-limiter-xxxx.onrender.com` |

Copy the exact `*.onrender.com` hostname from your dashboard (yours may differ from other services).

4. Wait for Render to show **Verified** and issue TLS (usually a few minutes after DNS propagates).

Free tier includes custom domains; Hobby workspaces get 2 included.

## 2. DNS (Cloudflare / registrar)

At the DNS provider for `kaustuvbasak.com`, add:

| Type  | Name            | Content / Target                | Proxy |
|-------|-----------------|---------------------------------|-------|
| CNAME | `rate-limiter`  | `<your-service>.onrender.com`   | DNS only recommended |

**Cloudflare:** set the record to **DNS only** (grey cloud), not proxied, unless you have already validated Render + Cloudflare for your other demos the same way.

Verify:

```bash
dig +short rate-limiter.kaustuvbasak.com CNAME
curl -s https://rate-limiter.kaustuvbasak.com/health
```

Expected: CNAME points to Render; health returns `{"status":"ok","storage":"session",...}`.

## 3. Portfolio site — Live Projects card

Add a third card in the **Live Projects** section on [kaustuvbasak.com](https://kaustuvbasak.com/), matching your DNS and HVAC cards.

### Suggested copy

**Title:** Sliding Window Rate Limiter  
**Subtitle:** AI API Rate Limiting · Live  
**Tags:** React · FastAPI · SQLite · Session storage  
**Description:** Multi-policy sliding-window limiter (tenant, user, model, tier). Per-browser demo sessions reset on reload. Dark mode.  
**Link:** https://rate-limiter.kaustuvbasak.com  

### HTML snippet (adapt to your site structure)

```html
<article class="project-card">
  <h3>Sliding Window Rate Limiter</h3>
  <p class="project-meta">AI API Rate Limiting · <span class="badge-live">Live</span></p>
  <p class="project-stack">React · FastAPI · SQLite · Session storage</p>
  <p class="project-desc">
    Interactive demo of a multi-policy sliding-window rate limiter — tenant, user, model,
    and tier scopes. Each visitor gets an isolated session; reload to reset counters.
  </p>
  <a
    href="https://rate-limiter.kaustuvbasak.com"
    target="_blank"
    rel="noopener noreferrer"
  >
    Visit rate-limiter.kaustuvbasak.com (opens in new tab)
  </a>
</article>
```

### Live demos footer line

Update the compact links row (where you list `dns.kaustuvbasak.com · hvac.kaustuvbasak.com`) to:

```text
Live demos: dns.kaustuvbasak.com · hvac.kaustuvbasak.com · rate-limiter.kaustuvbasak.com
```

### SEO / sitemap (optional)

Add to `sitemap.xml` on the main portfolio:

```xml
<url>
  <loc>https://rate-limiter.kaustuvbasak.com/</loc>
  <changefreq>monthly</changefreq>
  <priority>0.7</priority>
</url>
```

The demo app itself uses `robots.txt` `Disallow: /` so the subdomain is not indexed separately unless you change that.

## 4. Checklist

- [ ] Push `deploy` branch with updated `render.yaml`
- [ ] Sync Blueprint / verify custom domain on Render
- [ ] Add CNAME `rate-limiter` → your `*.onrender.com` host
- [ ] TLS shows as active on Render
- [ ] `curl https://rate-limiter.kaustuvbasak.com/health` succeeds
- [ ] Add Live Projects card on kaustuvbasak.com
- [ ] Update live demos link row on portfolio homepage

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DNS not verifying | Confirm CNAME name is `rate-limiter`, not `rate-limiter.kaustuvbasak.com` as the name field |
| SSL pending | Wait 15–30 min; ensure CNAME targets the exact Render hostname |
| 502 / spin-up delay | Free tier sleeps after idle; first hit may take ~30s |
| Still on old UI | Hard refresh; confirm latest `deploy` build finished on Render |
