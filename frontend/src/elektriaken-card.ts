import { LitElement, css, html, nothing, svg } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { localize, type MessageKey } from "./localize";
import type { ElektriakenConfig, HomeAssistant, PricePoint, PriceResponse } from "./types";

const DEFAULT_15 = [15, 30, 60, 120, 180, 240];
const DEFAULT_60 = [60, 120, 180, 240, 360, 480];

@customElement("elektriaken-card")
export class ElektriakenCard extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @state() private config: ElektriakenConfig = { type: "custom:elektriaken-card" };
  @state() private data?: PriceResponse;
  @state() private loading = true;
  @state() private error = false;
  private requestKey = "";
  private refreshTimer?: number;

  connectedCallback(): void {
    super.connectedCallback();
    this.refreshTimer = window.setInterval(() => void this.load(), 300_000);
  }

  disconnectedCallback(): void {
    if (this.refreshTimer !== undefined) window.clearInterval(this.refreshTimer);
    super.disconnectedCallback();
  }

  static getConfigElement(): HTMLElement {
    return document.createElement("elektriaken-card-editor");
  }

  static getStubConfig(): ElektriakenConfig {
    return { type: "custom:elektriaken-card", resolution: 15, duration_minutes: 60, include_vat: true };
  }

  setConfig(config: ElektriakenConfig): void {
    if (!config || config.type !== "custom:elektriaken-card") throw new Error("Invalid Elektriaken card configuration");
    this.config = { resolution: 15, duration_minutes: 60, include_vat: true, ...config };
    this.requestKey = "";
  }

  protected updated(): void {
    if (!this.hass) return;
    const key = `${this.config.resolution}/${this.config.duration_minutes}/${this.config.include_vat}`;
    if (key !== this.requestKey) {
      this.requestKey = key;
      void this.load();
    }
  }

  private t(key: MessageKey): string {
    return localize(this.hass?.locale?.language || this.hass?.language, key);
  }

  private async load(): Promise<void> {
    if (!this.hass) return;
    this.loading = true;
    this.error = false;
    try {
      this.data = await this.hass.connection.sendMessagePromise<PriceResponse>({
        type: "elektriaken/get_prices",
        resolution: this.config.resolution ?? 15,
        duration_minutes: this.config.duration_minutes ?? 60,
        include_vat: this.config.include_vat !== false,
      });
    } catch (_err) {
      this.error = true;
    } finally {
      this.loading = false;
    }
  }

  private patchConfig(patch: Partial<ElektriakenConfig>): void {
    this.config = { ...this.config, ...patch };
  }

  private formatDuration(minutes: number): string {
    return minutes < 60 ? `${minutes} ${this.t("minutes")}` : `${minutes / 60} ${this.t("hours")}`;
  }

  private currentPoint(): PricePoint | undefined {
    const now = Date.now();
    return this.data?.points.find((point) => Date.parse(point.start) <= now && now < Date.parse(point.end));
  }

  private renderChart(points: PricePoint[]) {
    if (!points.length) return html`<div class="empty">${this.t("noData")}</div>`;
    const width = 720;
    const height = 180;
    const top = 12;
    const bottom = 32;
    const values = points.map((point) => point.price);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    const span = max - min || 1;
    const barWidth = width / points.length;
    const y = (value: number) => top + ((max - value) / span) * (height - top - bottom);
    const zeroY = y(0);
    const sorted = [...values].sort((a, b) => a - b);
    const low = sorted[Math.floor((sorted.length - 1) / 3)];
    const high = sorted[Math.floor(((sorted.length - 1) * 2) / 3)];
    const now = Date.now();
    const bestStart = this.data?.best_window ? Date.parse(this.data.best_window.start) : NaN;
    const bestEnd = this.data?.best_window ? Date.parse(this.data.best_window.end) : NaN;
    const todayCount = points.filter((point) => point.day === "today").length;

    return html`
      <div class="chart-wrap">
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label=${this.t("relativeScale")}>
          ${svg`<line class="zero" x1="0" x2="${width}" y1="${zeroY}" y2="${zeroY}" />`}
          ${points.map((point, index) => {
            const valueY = y(point.price);
            const start = Date.parse(point.start);
            const isNow = start <= now && now < Date.parse(point.end);
            const isBest = start >= bestStart && start < bestEnd;
            const tier = point.price <= low ? "low" : point.price >= high ? "high" : "middle";
            const rectY = Math.min(valueY, zeroY);
            const rectHeight = Math.max(Math.abs(valueY - zeroY), 1);
            return svg`
              <g>
                <title>${new Date(point.start).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}: ${point.price.toFixed(3)} c/kWh</title>
                <rect class="bar ${tier} ${isBest ? "selected" : ""}" x="${index * barWidth + 1}" y="${rectY}" width="${Math.max(barWidth - 2, 1)}" height="${rectHeight}" />
                ${isNow ? svg`<path class="now-marker" d="M ${index * barWidth + barWidth / 2 - 5} 3 h10 l-5 7 z"/><title>${this.t("current")}</title>` : nothing}
                ${isBest ? svg`<circle class="best-marker" cx="${index * barWidth + barWidth / 2}" cy="${height - 19}" r="3"/>` : nothing}
              </g>`;
          })}
          ${todayCount > 0 && todayCount < points.length ? svg`<line class="divider" x1="${todayCount * barWidth}" x2="${todayCount * barWidth}" y1="0" y2="${height - bottom + 8}"/>` : nothing}
          <text x="8" y="${height - 5}">${this.t("today")}</text>
          ${todayCount < points.length ? svg`<text x="${todayCount * barWidth + 8}" y="${height - 5}">${this.t("tomorrow")}</text>` : nothing}
        </svg>
      </div>`;
  }

  protected render() {
    const title = this.config.title || this.t("title");
    const configuredPresets = this.config.duration_presets || (this.config.resolution === 60 ? DEFAULT_60 : DEFAULT_15);
    const presets = [...new Set([this.config.duration_minutes ?? 60, ...configuredPresets])].sort((a, b) => a - b);
    const current = this.currentPoint();
    return html`
      <ha-card>
        <div class="header">
          <div><h2>${title}</h2>${current ? html`<div class="price">${current.price.toFixed(3)} <small>c/kWh</small></div>` : nothing}</div>
          <label class="vat"><input type="checkbox" .checked=${this.config.include_vat !== false} @change=${(event: Event) => this.patchConfig({include_vat: (event.target as HTMLInputElement).checked})}> ${this.t("vat")}</label>
        </div>
        <div class="controls" aria-label=${this.t("resolution")}>
          <div class="segmented">
            ${([15, 60] as const).map(value => html`<button class=${this.config.resolution === value ? "active" : ""} @click=${() => this.patchConfig({resolution: value, duration_minutes: value === 60 ? 60 : 15})}>${value === 15 ? `15 ${this.t("minutes")}` : `1 ${this.t("hours")}`}</button>`)}
          </div>
          <select aria-label=${this.t("duration")} .value=${String(this.config.duration_minutes)} @change=${(event: Event) => this.patchConfig({duration_minutes: Number((event.target as HTMLSelectElement).value)})}>
            ${presets.map(value => html`<option value=${value}>${this.formatDuration(value)}</option>`)}
          </select>
        </div>
        ${this.loading ? html`<div class="status" aria-live="polite">${this.t("loading")}</div>` : this.error ? html`<div class="status error" role="alert">${this.t("error")} <button @click=${this.load}>${this.t("retry")}</button></div>` : this.data ? html`
          ${this.renderChart(this.data.points)}
          ${this.data.best_window ? html`<div class="summary"><span class="best-symbol" aria-hidden="true">◆</span><strong>${this.t("best")}</strong> ${new Date(this.data.best_window.start).toLocaleString([], {weekday: "short", hour: "2-digit", minute: "2-digit"})}–${new Date(this.data.best_window.end).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})}<span>${this.data.best_window.average_price.toFixed(3)} c/kWh ${this.t("average")}</span></div>` : nothing}
          ${!this.data.tomorrow_available ? html`<div class="notice">ⓘ ${this.t("tomorrowMissing")}</div>` : nothing}
        ` : html`<div class="status">${this.t("noData")}</div>`}
      </ha-card>`;
  }

  static styles = css`
    :host { display:block; color:var(--primary-text-color); }
    ha-card { padding:16px; overflow:hidden; }
    .header,.controls,.summary { display:flex; align-items:center; justify-content:space-between; gap:12px; }
    h2 { margin:0 0 4px; font-size:1.15rem; font-weight:500; }
    .price { font-size:1.8rem; font-weight:600; font-variant-numeric:tabular-nums; }
    small { font-size:.8rem; font-weight:400; color:var(--secondary-text-color); }
    .vat { font-size:.82rem; color:var(--secondary-text-color); white-space:nowrap; }
    .controls { margin:14px 0 8px; flex-wrap:wrap; }
    .segmented { display:flex; border:1px solid var(--divider-color); border-radius:9px; overflow:hidden; }
    button,select { min-height:36px; border:1px solid var(--divider-color); color:var(--primary-text-color); background:var(--card-background-color); font:inherit; }
    button { cursor:pointer; padding:0 12px; border:0; }
    button + button { border-left:1px solid var(--divider-color); }
    button.active { background:var(--primary-color); color:var(--text-primary-color,white); }
    button:focus-visible,select:focus-visible,input:focus-visible { outline:2px solid var(--primary-color); outline-offset:2px; }
    select { border-radius:9px; padding:0 9px; }
    .chart-wrap { overflow-x:auto; }
    svg { width:100%; min-width:400px; height:auto; overflow:visible; }
    .bar { fill:var(--warning-color,#f0ad4e); opacity:.82; }
    .bar.low { fill:var(--success-color,#43a047); }
    .bar.high { fill:var(--error-color,#db4437); }
    .bar.selected { stroke:var(--primary-text-color); stroke-width:2; stroke-dasharray:3 2; opacity:1; }
    .zero,.divider { stroke:var(--divider-color); stroke-width:1; }
    .divider { stroke-dasharray:4 3; }
    .now-marker,.best-marker { fill:var(--primary-text-color); }
    text { fill:var(--secondary-text-color); font:12px sans-serif; }
    .summary { justify-content:flex-start; flex-wrap:wrap; font-size:.88rem; margin-top:6px; }
    .summary span:last-child { margin-left:auto; }
    .best-symbol { font-size:.7rem; }
    .notice,.status { color:var(--secondary-text-color); text-align:center; padding:12px 0 2px; font-size:.88rem; }
    .error { color:var(--error-color); }
    .error button { margin-left:8px; border:1px solid currentColor; border-radius:7px; }
    @media (max-width:480px) { ha-card{padding:12px}.price{font-size:1.55rem}.summary span:last-child{width:100%;margin-left:18px}.controls{align-items:stretch}.segmented{flex:1}.segmented button{flex:1} }
  `;
}

@customElement("elektriaken-card-editor")
export class ElektriakenCardEditor extends LitElement {
  @property({ attribute: false }) hass?: HomeAssistant;
  @state() private config: ElektriakenConfig = { type: "custom:elektriaken-card" };

  setConfig(config: ElektriakenConfig): void { this.config = { ...config }; }

  private change(key: keyof ElektriakenConfig, value: unknown): void {
    this.config = { ...this.config, [key]: value };
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: this.config }, bubbles: true, composed: true }));
  }

  protected render() {
    const language = this.hass?.language;
    return html`<div class="form">
      <label>Title<input .value=${this.config.title || ""} @input=${(e: Event) => this.change("title", (e.target as HTMLInputElement).value)}></label>
      <label>${localize(language,"resolution")}<select .value=${String(this.config.resolution || 15)} @change=${(e: Event) => this.change("resolution", Number((e.target as HTMLSelectElement).value))}><option value="15">15 min</option><option value="60">1 h</option></select></label>
      <label>${localize(language,"duration")}<input type="number" min="15" step="15" .value=${String(this.config.duration_minutes || 60)} @change=${(e: Event) => this.change("duration_minutes", Number((e.target as HTMLInputElement).value))}></label>
      <label>Duration presets (minutes)<input .value=${(this.config.duration_presets || []).join(", ")} placeholder="15, 30, 60, 120" @change=${(e: Event) => this.change("duration_presets", (e.target as HTMLInputElement).value.split(",").map(value => Number(value.trim())).filter(value => Number.isFinite(value) && value > 0))}></label>
      <label class="check"><input type="checkbox" .checked=${this.config.include_vat !== false} @change=${(e: Event) => this.change("include_vat", (e.target as HTMLInputElement).checked)}> ${localize(language,"includeVat")}</label>
    </div>`;
  }
  static styles = css`.form{display:grid;gap:14px;padding:8px 0}label{display:grid;gap:5px;color:var(--primary-text-color)}input,select{box-sizing:border-box;width:100%;padding:10px;border:1px solid var(--divider-color);border-radius:6px;color:var(--primary-text-color);background:var(--card-background-color);font:inherit}.check{display:flex;align-items:center}.check input{width:auto}`;
}

declare global { interface Window { customCards?: Array<Record<string, unknown>> } }
window.customCards = window.customCards || [];
window.customCards.push({ type: "elektriaken-card", name: "Elektriaken", description: "Estonian day-ahead electricity prices and cheapest windows", preview: true });

