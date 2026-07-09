# HOCH NEURO — Dashboard Wiring Snippet

This snippet details the HTML changes required to expose the `HOCH NEURO` panel as a tab in the production dashboard `frontend/index.html`.

## 1. Tab Navigation Entry
Insert this button block directly after the PERT tab button (`id="nav-pert"`, around line 126):

```html
                        <button class="nav-item" id="nav-neuro" data-view="neuro" type="button" style="background: none; border: none; font-family: inherit; font-size: inherit; text-align: left; cursor: pointer; width: 100%; color: var(--text-secondary); font-weight: 500;">
                            <i data-lucide="activity"></i>
                            <span>Neuro Command</span>
                        </button>
```

## 2. View Section Root
Insert this section view block directly after the PERT view section (`id="view-pert"`, around line 5146):

```html
<section class="view live-view" id="view-neuro" data-view="neuro" hidden>
  <header class="section-header">
    <div>
      <p class="eyebrow">CANONICAL CONTROL PLANE</p>
      <h2>Neuro Command Center</h2>
    </div>
  </header>
  <div id="react-neuro-root"></div>
</section>
```

## 3. Dynamic Switching Verification
Ensure that clicking `nav-neuro` correctly reveals `view-neuro` and hides other tabs. The class `.live-view` sections are toggled automatically based on the `data-view` property by the core router.
