"""Componentes visuais compartilhados do frontend PagControl.

Este módulo concentra somente apresentação. Nenhuma regra de negócio ou
integração com a API deve ser adicionada aqui.
"""

from html import escape

import streamlit as st


def apply_theme() -> None:
    """Aplica a identidade visual corporativa em todas as páginas."""
    st.html(
        """
        <style>
        :root {
            --pc-primary: #0f766e;
            --pc-primary-dark: #115e59;
            --pc-secondary: #1d4ed8;
            --pc-ink: #172033;
            --pc-muted: #667085;
            --pc-border: #e4e7ec;
            --pc-surface: #ffffff;
            --pc-canvas: #f6f8fb;
        }

        .stApp {
            background:
                radial-gradient(circle at 94% 3%, rgba(15, 118, 110, 0.08), transparent 24rem),
                var(--pc-canvas);
            color: var(--pc-ink);
        }

        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1320px;
            padding-top: 2.25rem;
            padding-bottom: 3rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #132238 0%, #172a46 100%);
            border-right: 0;
        }

        [data-testid="stSidebar"] * {
            color: #eaf2ff;
        }

        [data-testid="stSidebarNav"] span {
            font-weight: 550;
        }

        [data-testid="stSidebarNav"] a {
            border-radius: 10px;
            margin: 0.15rem 0.55rem;
        }

        [data-testid="stSidebarNav"] a:hover {
            background: rgba(255, 255, 255, 0.09);
        }

        .pc-sidebar-brand {
            padding: 0.45rem 1rem 1.1rem;
            margin-bottom: 0.25rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
        }

        .pc-sidebar-logo {
            display: flex;
            align-items: center;
            gap: 0.7rem;
            font-size: 1.1rem;
            font-weight: 750;
            letter-spacing: -0.02em;
        }

        .pc-logo-mark {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.15rem;
            height: 2.15rem;
            border-radius: 11px;
            color: #ffffff;
            background: linear-gradient(135deg, #2dd4bf, #0f766e);
            box-shadow: 0 8px 18px rgba(20, 184, 166, 0.22);
        }

        .pc-sidebar-caption {
            margin-top: 0.55rem;
            color: #a9bbd4 !important;
            font-size: 0.76rem;
            line-height: 1.4;
        }

        .pc-header {
            padding: 1.65rem 1.8rem;
            margin-bottom: 1.35rem;
            border: 1px solid rgba(15, 118, 110, 0.12);
            border-radius: 20px;
            background: linear-gradient(125deg, #ffffff 0%, #f0fdfa 100%);
            box-shadow: 0 8px 28px rgba(16, 24, 40, 0.06);
        }

        .pc-eyebrow {
            margin-bottom: 0.45rem;
            color: var(--pc-primary);
            font-size: 0.74rem;
            font-weight: 750;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }

        .pc-title {
            margin: 0;
            color: var(--pc-ink);
            font-size: clamp(1.75rem, 3vw, 2.45rem);
            font-weight: 760;
            letter-spacing: -0.04em;
            line-height: 1.12;
        }

        .pc-description {
            max-width: 760px;
            margin: 0.65rem 0 0;
            color: var(--pc-muted);
            font-size: 0.98rem;
            line-height: 1.65;
        }

        .pc-section-label {
            margin: 1.7rem 0 0.75rem;
            color: var(--pc-ink);
            font-size: 1.08rem;
            font-weight: 720;
            letter-spacing: -0.015em;
        }

        .pc-card {
            min-height: 168px;
            padding: 1.35rem;
            border: 1px solid var(--pc-border);
            border-radius: 16px;
            background: var(--pc-surface);
            box-shadow: 0 4px 16px rgba(16, 24, 40, 0.045);
        }

        .pc-card-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 2.4rem;
            height: 2.4rem;
            margin-bottom: 0.9rem;
            border-radius: 12px;
            color: var(--pc-primary-dark);
            background: #ccfbf1;
            font-size: 1.05rem;
            font-weight: 750;
        }

        .pc-card h3 {
            margin: 0 0 0.45rem;
            color: var(--pc-ink);
            font-size: 1.03rem;
        }

        .pc-card p {
            margin: 0;
            color: var(--pc-muted);
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .pc-metric {
            min-height: 128px;
            padding: 1.15rem 1.2rem;
            border: 1px solid var(--pc-border);
            border-top: 3px solid var(--metric-accent, var(--pc-primary));
            border-radius: 15px;
            background: var(--pc-surface);
            box-shadow: 0 4px 16px rgba(16, 24, 40, 0.045);
        }

        .pc-metric-label {
            color: var(--pc-muted);
            font-size: 0.78rem;
            font-weight: 650;
        }

        .pc-metric-value {
            margin-top: 0.4rem;
            color: var(--pc-ink);
            font-size: 1.72rem;
            font-weight: 760;
            letter-spacing: -0.04em;
        }

        .pc-metric-delta {
            display: inline-block;
            margin-top: 0.45rem;
            padding: 0.18rem 0.48rem;
            border-radius: 999px;
            color: #067647;
            background: #ecfdf3;
            font-size: 0.72rem;
            font-weight: 650;
        }

        .pc-metric-delta.attention {
            color: #b54708;
            background: #fffaeb;
        }

        .pc-status-strip {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.7rem 0.9rem;
            border: 1px solid #d1fadf;
            border-radius: 12px;
            color: #05603a;
            background: #f0fdf4;
            font-size: 0.82rem;
            font-weight: 600;
        }

        .pc-status-dot {
            width: 0.52rem;
            height: 0.52rem;
            border-radius: 999px;
            background: #12b76a;
            box-shadow: 0 0 0 4px rgba(18, 183, 106, 0.12);
        }

        div[data-testid="stForm"],
        div[data-testid="stDataFrame"],
        div[data-testid="stDataEditor"],
        div[data-testid="stVegaLiteChart"] {
            padding: 1rem;
            border: 1px solid var(--pc-border);
            border-radius: 16px;
            background: var(--pc-surface);
            box-shadow: 0 4px 16px rgba(16, 24, 40, 0.04);
        }

        div[data-testid="stForm"] {
            padding: 1.25rem 1.25rem 0.35rem;
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] > button {
            min-height: 2.65rem;
            border: 0;
            border-radius: 10px;
            color: #ffffff;
            background: linear-gradient(135deg, var(--pc-primary), var(--pc-primary-dark));
            font-weight: 680;
            box-shadow: 0 6px 14px rgba(15, 118, 110, 0.18);
        }

        .stButton > button:hover,
        [data-testid="stFormSubmitButton"] > button:hover {
            color: #ffffff;
            border: 0;
            background: var(--pc-primary-dark);
        }

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div {
            border-radius: 10px;
        }

        hr {
            border-color: var(--pc-border) !important;
        }

        @media (max-width: 768px) {
            [data-testid="stAppViewContainer"] > .main .block-container {
                padding-top: 1.25rem;
            }

            .pc-header {
                padding: 1.3rem;
                border-radius: 16px;
            }

            .pc-card,
            .pc-metric {
                min-height: auto;
            }
        }
        </style>
        """,
    )


def sidebar_brand() -> None:
    """Exibe a assinatura do produto no topo da navegação lateral."""
    st.sidebar.html(
        """
        <div class="pc-sidebar-brand">
            <div class="pc-sidebar-logo">
                <span class="pc-logo-mark">P</span>
                <span>PagControl</span>
            </div>
            <div class="pc-sidebar-caption">Gestão de cobranças recorrentes</div>
        </div>
        """,
    )


def page_header(eyebrow: str, title: str, description: str) -> None:
    """Renderiza o cabeçalho padrão das páginas."""
    st.html(
        f"""
        <section class="pc-header">
            <div class="pc-eyebrow">{escape(eyebrow)}</div>
            <h1 class="pc-title">{escape(title)}</h1>
            <p class="pc-description">{escape(description)}</p>
        </section>
        """,
    )


def section_title(title: str) -> None:
    st.html(
        f'<div class="pc-section-label">{escape(title)}</div>',
    )


def feature_card(icon: str, title: str, description: str) -> None:
    st.html(
        f"""
        <article class="pc-card">
            <div class="pc-card-icon">{escape(icon)}</div>
            <h3>{escape(title)}</h3>
            <p>{escape(description)}</p>
        </article>
        """,
    )


def metric_card(
    label: str,
    value: str,
    delta: str,
    *,
    accent: str = "#0f766e",
    attention: bool = False,
) -> None:
    delta_class = " attention" if attention else ""
    st.html(
        f"""
        <div class="pc-metric" style="--metric-accent: {escape(accent)};">
            <div class="pc-metric-label">{escape(label)}</div>
            <div class="pc-metric-value">{escape(value)}</div>
            <div class="pc-metric-delta{delta_class}">{escape(delta)}</div>
        </div>
        """,
    )


def api_status(online: bool = True) -> None:
    """Mostra um indicador visual simples, sem consultar ou alterar a API."""
    label = "API conectada" if online else "API indisponível"
    dot_color = "#12b76a" if online else "#f79009"
    text_color = "#05603a" if online else "#93370d"
    bg_color = "#f0fdf4" if online else "#fffaeb"
    border_color = "#d1fadf" if online else "#fedf89"
    st.html(
        f"""
        <div class="pc-status-strip" style="color: {text_color}; background: {bg_color}; border-color: {border_color};">
            <span class="pc-status-dot" style="background: {dot_color};"></span>
            {escape(label)}
        </div>
        """,
    )
