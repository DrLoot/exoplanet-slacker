# 🌌 Exoplanet Slacker

**Exoplanet Slacker** is a community-built hub for participants of [NASA Exoplanet Watch](https://exoplanets.nasa.gov/exoplanet-watch/).
It extends the Slack community with tutorials, curated news, mission explainers, and an archive of community videos — all in a lightweight GitHub Pages site.

> **Note:** This is a community resource and **not an official NASA website**. It does not represent NASA, AAVSO, or affiliated institutions.

---

## 🌐 Live Site
Set your Pages URL here once deployed: `https://<your-username>.github.io/exoplanet-slacker`

---

## 📖 What’s Inside
- **Citizen Science Overview** — What NASA Exoplanet Watch is and how to contribute.
- **Slack Hub** — Community news, FAQs, and digest highlights.
- **News** — Curated exoplanet discoveries and mission updates.
- **EXOTIC Tutorials** — Docs and video walkthroughs for the EXOTIC pipeline.
- **AAVSO Tutorials** — How to submit data to AAVSO.
- **Video Archive** — Biweekly Teams call recordings with quick summaries.
- **Pandora Mission** — Mission explainer and (coming soon) top 20 targets list.

---

## 🗂 Suggested Structure
```
root/
├─ index.html                # Exoplanet Slacker homepage
├─ citizen-science.html
├─ slack-hub.html
├─ news.html
├─ exotic.html
├─ aavso.html
├─ videos.html
├─ pandora.html
└─ assets/
   ├─ images/
   └─ css/ js/
```
> You can use plain HTML (as provided) or switch to Jekyll/MkDocs later without changing content.

---

## 🚀 Getting Started (Local)
- **Quick preview:** Open `index.html` directly in your browser.
- **With a simple server (optional):**
  ```bash
  # Python 3
  python -m http.server 4000
  # -> visit http://localhost:4000
  ```

---

## ☁️ Deploying on GitHub Pages
1. Push this repo to GitHub.
2. Go to **Settings → Pages**.
3. **Source:** select the `main` branch and **root** (or `/docs` if you put files there).
4. Click **Save** — your site will build in a minute or two.
5. Your public URL appears at the top of the Pages settings.

> If you prefer, deploy on Vercel/Netlify; the site works as static HTML anywhere.

---

## 🤝 Contributing
Contributions are welcome!
- Add/update tutorials and screenshots.
- Propose news items and meeting summaries.
- Improve accessibility, layout, or copy.
- Add translations.

**Workflow:**
1. Fork the repo and create a branch: `feat/your-change`.
2. Make edits (keep pages lightweight, accessible, and mobile-friendly).
3. Open a Pull Request with a short description and screenshots if UI changes.

---

## 🔒 Attribution & Media
- NASA images/media are typically public domain unless otherwise noted.
- Credit other sources clearly in alt text/captions and link back to originals.

---

## 📜 License
Code and site content are offered under the **MIT License** (see `LICENSE`).

---

Made with ✨ by the exoplanet community.
