"""Componentes visuais compartilhados do frontend PagControl.

Este módulo concentra somente apresentação. Nenhuma regra de negócio ou
integração com a API deve ser adicionada aqui.
"""

from datetime import datetime
from html import escape
from urllib.parse import quote

import streamlit as st

# Base das paletas (identidade anterior, verde-azulado). Cada paleta sobrescreve
# só o que muda; a padrão do sistema é a PALETA_PADRAO, definida mais abaixo.
_PALETA_BASE = {
    "primary": "#0f766e",
    "primary_dark": "#115e59",
    "ink": "#172033",
    "muted": "#667085",
    "border": "#e4e7ec",
    "surface": "#ffffff",
    "canvas": "#f6f8fb",
    "sidebar_top": "#132238",
    "sidebar_bottom": "#172a46",
    "header_to": "#f0fdfa",
    "logo_a": "#2dd4bf",
    "icon_bg": "#ccfbf1",
    # cartões de indicadores (o 1º usa a cor primária)
    "card_2": "#1d4ed8",
    "card_3": "#7c3aed",
    "card_4": "#f79009",
    # situação da cobrança
    "pago": "#3f9a89",
    "pendente": "#e8bc4f",
    "atrasado": "#e2884a",
    "inadimplente": "#d16057",
    # séries dos gráficos
    "previsto": "#c9ced9",
    "recebido": "#1d4ed8",
    "realce": "#e8edfb",
    "heat_claro": "#deebf7",
    "heat_escuro": "#08519c",
}

# Paletas para teste (inspiradas em referências de academia/fitness). Escolha
# na barra lateral; a escolhida vale para todas as páginas da sessão.
PALETAS: dict[str, dict[str, str]] = {
    "Energia (laranja + grafite)": {
        **_PALETA_BASE,
        "primary": "#c2410c",
        "primary_dark": "#9a3412",
        "ink": "#111827",
        "muted": "#6b7280",
        "border": "#e5e7eb",
        "canvas": "#f8f7f4",
        "sidebar_top": "#111827",
        "sidebar_bottom": "#1f2937",
        "header_to": "#fff7ed",
        "logo_a": "#fb923c",
        "icon_bg": "#ffedd5",
        "card_2": "#1d4ed8",
        "card_3": "#f97316",
        "card_4": "#dc2626",
        "pago": "#16a34a",
        "pendente": "#64748b",
        "atrasado": "#eab308",
        "inadimplente": "#dc2626",
        "previsto": "#d1d5db",
        "recebido": "#c2410c",
        "realce": "#fff1e6",
        "heat_claro": "#ffedd5",
        "heat_escuro": "#9a3412",
    },
    "Atual (verde-azulado)": _PALETA_BASE,
    "Azul e amarelo (treino)": {
        **_PALETA_BASE,
        "primary": "#0a62d0",
        "primary_dark": "#084ea6",
        "ink": "#191718",
        "muted": "#5c6370",
        "border": "#dfe3e8",
        "canvas": "#f3f5f7",
        "sidebar_top": "#191718",
        "sidebar_bottom": "#2a2629",
        "header_to": "#eef5ff",
        "logo_a": "#f3d849",
        "icon_bg": "#dbe9fb",
        "card_2": "#e0b400",
        "card_3": "#191718",
        "card_4": "#d92d20",
        "pago": "#1e9e6a",
        "pendente": "#f3d849",
        "atrasado": "#f08c2e",
        "inadimplente": "#d92d20",
        "previsto": "#cdd4db",
        "recebido": "#0a62d0",
        "realce": "#e6effc",
        "heat_claro": "#dbe9fb",
        "heat_escuro": "#0a3f8f",
    },
    "Vermelho profundo + amarelo": {
        **_PALETA_BASE,
        "primary": "#79031d",
        "primary_dark": "#5a0216",
        "ink": "#1a0a0e",
        "muted": "#6b6264",
        "border": "#ebe3e4",
        "canvas": "#f5f7f7",
        "sidebar_top": "#0a0204",
        "sidebar_bottom": "#3a0210",
        "header_to": "#fdf2f4",
        "logo_a": "#edb518",
        "icon_bg": "#fde7ea",
        "card_2": "#edb518",
        "card_3": "#000407",
        "card_4": "#f21137",
        "pago": "#1e9e6a",
        "pendente": "#edb518",
        "atrasado": "#f08c2e",
        "inadimplente": "#f21137",
        "previsto": "#d9d4d5",
        "recebido": "#000407",
        "realce": "#fbe9ec",
        "heat_claro": "#fde7ea",
        "heat_escuro": "#79031d",
    },
    "Terra (laranja + vermelho)": {
        **_PALETA_BASE,
        "primary": "#aa210f",
        "primary_dark": "#86190b",
        "ink": "#2b2a28",
        "muted": "#6a6864",
        "border": "#e3e4e2",
        "canvas": "#edefee",
        "sidebar_top": "#2f2e2b",
        "sidebar_bottom": "#41403c",
        "header_to": "#f6efe9",
        "logo_a": "#d08856",
        "icon_bg": "#f5e3d6",
        "card_2": "#d08856",
        "card_3": "#41403c",
        "card_4": "#aa210f",
        "pago": "#4f8a5b",
        "pendente": "#d9a441",
        "atrasado": "#d08856",
        "inadimplente": "#aa210f",
        "previsto": "#d3d6d4",
        "recebido": "#41403c",
        "realce": "#f1e6dd",
        "heat_claro": "#f5e3d6",
        "heat_escuro": "#aa210f",
    },
}
PALETA_PADRAO = "Energia (laranja + grafite)"  # identidade padrão do PagControl


def paleta_atual() -> dict[str, str]:
    """Paleta escolhida no seletor da barra lateral (ou a padrão)."""
    return PALETAS.get(st.session_state.get("paleta", PALETA_PADRAO), _PALETA_BASE)


def _variaveis_da_paleta(paleta: dict[str, str]) -> str:
    nomes = {
        "primary": "--pc-primary",
        "primary_dark": "--pc-primary-dark",
        "ink": "--pc-ink",
        "muted": "--pc-muted",
        "border": "--pc-border",
        "surface": "--pc-surface",
        "canvas": "--pc-canvas",
        "sidebar_top": "--pc-sidebar-top",
        "sidebar_bottom": "--pc-sidebar-bottom",
        "header_to": "--pc-header-to",
        "logo_a": "--pc-logo-a",
        "icon_bg": "--pc-icon-bg",
    }
    return "".join(f"{css}: {paleta[chave]};" for chave, css in nomes.items())


def _previa_paleta_html(paleta: dict[str, str]) -> str:
    """Miniatura de como a página ficaria com a paleta (lateral, cartões, gráficos)."""
    p = paleta
    cartoes = [p["primary"], p["card_2"], p["card_3"], p["card_4"]]
    cartoes_html = "".join(
        f'<div style="flex:1;background:{p["surface"]};border:1px solid {p["border"]};'
        f'border-top:3px solid {cor};border-radius:6px;padding:5px 6px;">'
        f'<div style="height:4px;width:60%;background:{p["muted"]};opacity:.45;'
        f'border-radius:2px;"></div>'
        f'<div style="height:8px;width:45%;background:{p["ink"]};border-radius:2px;'
        f'margin-top:6px;"></div></div>'
        for cor in cartoes
    )
    situacoes = "".join(
        f'<div style="width:14%;height:{altura}%;background:{p[chave]};'
        f'border-radius:2px 2px 0 0;"></div>'
        for chave, altura in (
            ("pago", 90),
            ("inadimplente", 28),
            ("pendente", 22),
            ("atrasado", 10),
        )
    )
    pares = "".join(
        f'<div style="display:flex;gap:2px;align-items:flex-end;height:100%;">'
        f'<div style="width:7px;height:{a}%;background:{p["previsto"]};"></div>'
        f'<div style="width:7px;height:{b}%;background:{p["recebido"]};"></div></div>'
        for a, b in ((60, 52), (68, 60), (75, 70), (82, 76), (70, 66))
    )
    amostras = "".join(
        f'<span title="{chave}: {p[chave]}" style="display:inline-block;width:16px;'
        f"height:16px;border-radius:50%;background:{p[chave]};"
        f'border:1px solid rgba(0,0,0,.15);margin-right:4px;"></span>'
        for chave in (
            "primary",
            "card_2",
            "pago",
            "pendente",
            "atrasado",
            "inadimplente",
            "sidebar_top",
        )
    )
    return f"""
    <div style="border:1px solid {p["border"]};border-radius:10px;overflow:hidden;
                background:{p["canvas"]};">
      <div style="display:flex;height:118px;">
        <div style="width:22%;background:linear-gradient(180deg,{p["sidebar_top"]},{p["sidebar_bottom"]});
                    padding:8px 6px;">
          <div style="display:flex;align-items:center;gap:4px;">
            <div style="width:14px;height:14px;border-radius:4px;
                        background:linear-gradient(135deg,{p["logo_a"]},{p["primary"]});"></div>
            <div style="height:5px;width:40%;background:#fff;opacity:.85;border-radius:2px;"></div>
          </div>
          <div style="height:16px;margin-top:12px;border-radius:5px;
                      background:linear-gradient(135deg,{p["primary"]},{p["primary_dark"]});"></div>
        </div>
        <div style="flex:1;padding:8px;display:flex;flex-direction:column;gap:6px;">
          <div style="border-radius:7px;padding:6px 8px;border:1px solid {p["border"]};
                      background:linear-gradient(125deg,{p["surface"]},{p["header_to"]});">
            <div style="height:4px;width:22%;background:{p["primary"]};border-radius:2px;"></div>
            <div style="height:7px;width:48%;background:{p["ink"]};border-radius:2px;margin-top:4px;"></div>
          </div>
          <div style="display:flex;gap:5px;">{cartoes_html}</div>
          <div style="display:flex;gap:5px;flex:1;min-height:0;">
            <div style="flex:1;background:{p["surface"]};border:1px solid {p["border"]};
                        border-radius:6px;padding:5px;display:flex;align-items:flex-end;
                        justify-content:space-around;">{situacoes}</div>
            <div style="flex:1;background:{p["surface"]};border:1px solid {p["border"]};
                        border-radius:6px;padding:5px;display:flex;align-items:flex-end;
                        justify-content:space-around;">{pares}</div>
          </div>
        </div>
      </div>
      <div style="padding:6px 8px;background:{p["surface"]};border-top:1px solid {p["border"]};">
        {amostras}
      </div>
    </div>
    """


@st.dialog("Paletas de cores", width="large")
def _dialogo_paletas() -> None:
    """Janela sobre a página: mostra cada paleta numa miniatura e aplica ao clicar."""
    st.caption(
        "Cada miniatura mostra como a página ficaria: lateral, cartões, situação das "
        "cobranças e previsto x recebido. Os círculos são as cores principais. "
        "A escolha vale para todas as páginas desta sessão."
    )
    em_uso = st.session_state.get("paleta", PALETA_PADRAO)
    colunas = st.columns(3, gap="small")
    for posicao, (nome, paleta) in enumerate(PALETAS.items()):
        with colunas[posicao % 3]:
            st.html(
                f"<div style='font-size:0.82rem;font-weight:700;margin-bottom:4px'>{escape(nome)}</div>"
            )
            st.html(_previa_paleta_html(paleta))
            ativa = nome == em_uso
            if st.button(
                "Em uso" if ativa else "Usar",
                key=f"usar_paleta_{posicao}",
                disabled=ativa,
                width="stretch",
            ):
                st.session_state["paleta"] = nome
                st.rerun()


# Haltere de traço (cinza, no estilo dos ícones do topo do Streamlit); o CSS faz
# o haltere subir e descer enquanto o aviso de carregamento está na tela.
_SVG_HALTERE = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="26" height="26" viewBox="0 0 24 24" '
    'fill="none" stroke="#374151" stroke-width="1.7" stroke-linecap="round" '
    'stroke-linejoin="round">'
    '<path d="M8 12 H16"/>'
    '<rect x="4.2" y="8.2" width="3.6" height="7.6" rx="1"/>'
    '<rect x="16.2" y="8.2" width="3.6" height="7.6" rx="1"/>'
    '<path d="M2.4 10.4 V13.6 M21.6 10.4 V13.6"/></svg>'
)


def _css_aviso_carregamento() -> str:
    """Aviso de carregamento do cache: sem o nome da função, só a bolinha girando,
    o "Running" e um haltere subindo e descendo."""
    imagem = "data:image/svg+xml;utf8," + quote(_SVG_HALTERE, safe="")
    return f"""
    <style>
    [data-testid="stSpinner"] [data-testid="stMarkdownContainer"] p {{
        font-size: 0;
    }}

    [data-testid="stSpinner"] [data-testid="stMarkdownContainer"] p::before {{
        content: "Running";
        font-size: 1rem;
    }}

    [data-testid="stSpinner"] [data-testid="stMarkdownContainer"] p::after {{
        content: "";
        display: inline-block;
        width: 26px;
        height: 26px;
        margin-left: 0.5rem;
        vertical-align: middle;
        background: url("{imagem}") center / 26px 26px no-repeat;
        animation: pc-levanta 1s ease-in-out infinite alternate;
    }}

    @keyframes pc-levanta {{
        from {{ transform: translateY(4px); }}
        to {{ transform: translateY(-4px); }}
    }}

    @media (prefers-reduced-motion: reduce) {{
        [data-testid="stSpinner"] [data-testid="stMarkdownContainer"] p::after {{
            animation: none;
        }}
    }}
    </style>
    """


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
            --pc-sidebar-top: #132238;
            --pc-sidebar-bottom: #172a46;
            --pc-header-to: #f0fdfa;
            --pc-logo-a: #2dd4bf;
            --pc-icon-bg: #ccfbf1;
        }

        .stApp {
            background:
                radial-gradient(circle at 94% 3%, color-mix(in srgb, var(--pc-primary) 8%, transparent), transparent 24rem),
                var(--pc-canvas);
            color: var(--pc-ink);
        }

        /* Conteúdo centralizado e com largura limitada: em tela cheia o texto e os
           cartões não se esticam por toda a janela. */
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewContainer"] > .main .block-container {
            max-width: 1180px;
            /* a barra do Streamlit (Deploy) tem ~3,75rem e fica por cima do conteúdo */
            padding-top: 4.5rem;
            padding-bottom: 2.5rem;
        }

        [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
            gap: 0.8rem;
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, var(--pc-sidebar-top) 0%, var(--pc-sidebar-bottom) 100%);
            border-right: 0;
        }

        [data-testid="stSidebar"] * {
            color: #eaf2ff;
        }

        /* Caixas de seleção da lateral: o texto fica escuro sobre o fundo claro. */
        [data-testid="stSidebar"] [data-testid="stSelectbox"] input,
        [data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] * {
            color: var(--pc-ink) !important;
            -webkit-text-fill-color: var(--pc-ink) !important;
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
            background: linear-gradient(135deg, var(--pc-logo-a), var(--pc-primary));
            box-shadow: 0 8px 18px color-mix(in srgb, var(--pc-primary) 24%, transparent);
        }

        .pc-sidebar-caption {
            margin-top: 0.55rem;
            color: #a9bbd4 !important;
            font-size: 0.76rem;
            line-height: 1.4;
        }

        .pc-header {
            padding: 1.3rem 1.5rem;
            margin-bottom: 0.9rem;
            border: 1px solid color-mix(in srgb, var(--pc-primary) 14%, transparent);
            border-radius: 20px;
            background: linear-gradient(125deg, var(--pc-surface) 0%, var(--pc-header-to) 100%);
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
            margin: 1.25rem 0 0.5rem;
            color: var(--pc-ink);
            font-size: 1.05rem;
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
            background: var(--pc-icon-bg);
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
            min-height: 108px;
            padding: 0.95rem 1.05rem;
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
            font-size: 1.55rem;
            font-weight: 760;
            letter-spacing: -0.04em;
            white-space: nowrap;
        }

        /* Cartões de indicadores: quebram em 2x2 (ou 1 coluna) quando falta
           largura, em vez de espremer o valor em duas linhas. */
        .pc-insights {
            padding: 1.1rem 1.25rem;
            margin: 1rem 0 0.2rem;
            border: 1px solid var(--pc-border);
            border-left: 4px solid var(--pc-primary);
            border-radius: 14px;
            background: var(--pc-surface);
            box-shadow: 0 4px 16px rgba(16, 24, 40, 0.045);
        }

        .pc-insights-title {
            margin: 0 0 0.6rem;
            color: var(--pc-ink);
            font-size: 1.02rem;
            font-weight: 720;
        }

        .pc-insight {
            display: flex;
            gap: 0.65rem;
            align-items: flex-start;
            padding: 0.45rem 0;
            color: var(--pc-ink);
            font-size: 0.9rem;
            line-height: 1.5;
        }

        .pc-insight + .pc-insight {
            border-top: 1px solid var(--pc-border);
        }

        .pc-insight-marker {
            flex: none;
            width: 1.45rem;
            height: 1.45rem;
            margin-top: 0.1rem;
            border-radius: 50%;
            font-size: 0.72rem;
            font-weight: 800;
            line-height: 1.45rem;
            text-align: center;
        }

        .pc-insight.alta .pc-insight-marker { color: #15803d; background: #dcfce7; }
        .pc-insight.queda .pc-insight-marker { color: #b91c1c; background: #fee2e2; }
        .pc-insight.atencao .pc-insight-marker { color: #b45309; background: #fef3c7; }
        .pc-insight.info .pc-insight-marker { color: var(--pc-muted); background: #f2f4f7; }

        .pc-insights-foot {
            margin: 0.7rem 0 0;
            color: var(--pc-muted);
            font-size: 0.76rem;
            line-height: 1.45;
        }

        .pc-metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 0.8rem;
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
        div[data-testid="stElementContainer"]:has(div[data-testid="stVegaLiteChart"]) {
            padding: 1rem;
            border: 1px solid var(--pc-border);
            border-radius: 16px;
            background: var(--pc-surface);
            box-shadow: 0 4px 16px rgba(16, 24, 40, 0.04);
        }

        div[data-testid="stForm"] {
            padding: 1.25rem 1.25rem 0.35rem;
        }

        /* O cartão dos gráficos fica no contêiner externo: o Streamlit calcula a
           largura do gráfico sem descontar o padding do próprio elemento, e o
           desenho passava da borda direita do cartão. */
        div[data-testid="stElementContainer"]:has(div[data-testid="stVegaLiteChart"])
            div[data-testid="stVegaLiteChart"] {
            padding: 0;
            border: 0;
            background: transparent;
            box-shadow: none;
        }

        .stButton > button,
        [data-testid="stFormSubmitButton"] > button {
            min-height: 2.65rem;
            border: 0;
            border-radius: 10px;
            color: #ffffff;
            background: linear-gradient(135deg, var(--pc-primary), var(--pc-primary-dark));
            font-weight: 680;
            box-shadow: 0 6px 14px color-mix(in srgb, var(--pc-primary) 20%, transparent);
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
            [data-testid="stMainBlockContainer"],
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
    st.html(f"<style>:root {{ {_variaveis_da_paleta(paleta_atual())} }}</style>")
    st.html(_css_aviso_carregamento())


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
    # Janela temporária para comparar paletas sem sair da página.
    st.sidebar.caption(f"Paleta: {st.session_state.get('paleta', PALETA_PADRAO)}")
    if st.sidebar.button(
        "Ver paletas de cores",
        key="abrir_paletas",
        icon=":material/palette:",
        width="stretch",
    ):
        _dialogo_paletas()


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


def _metric_html(
    label: str,
    value: str,
    delta: str,
    accent: str = "var(--pc-primary)",
    attention: bool = False,
) -> str:
    delta_class = " attention" if attention else ""
    return f"""
        <div class="pc-metric" style="--metric-accent: {escape(accent)};">
            <div class="pc-metric-label">{escape(label)}</div>
            <div class="pc-metric-value">{escape(value)}</div>
            <div class="pc-metric-delta{delta_class}">{escape(delta)}</div>
        </div>
    """


def metric_card(
    label: str,
    value: str,
    delta: str,
    *,
    accent: str = "var(--pc-primary)",
    attention: bool = False,
) -> None:
    st.html(_metric_html(label, value, delta, accent, attention))


_MARCADORES_INSIGHT = {"alta": "▲", "queda": "▼", "atencao": "!", "info": "i"}


def insights_box(
    itens: list[dict], rodape: str, titulo: str = "Resumo analítico"
) -> None:
    """Caixa de texto com os alertas do resumo analítico.

    Cada item: {"tipo": "alta"|"queda"|"atencao"|"info", "titulo": str, "texto": str}.
    """
    linhas = "".join(
        f"""
        <div class="pc-insight {escape(item["tipo"])}">
            <span class="pc-insight-marker">{_MARCADORES_INSIGHT.get(item["tipo"], "i")}</span>
            <div><strong>{escape(item["titulo"])}</strong> — {escape(item["texto"])}</div>
        </div>
        """
        for item in itens
    )
    st.html(
        f"""
        <div class="pc-insights">
            <div class="pc-insights-title">{escape(titulo)}</div>
            {linhas}
            <p class="pc-insights-foot">{escape(rodape)}</p>
        </div>
        """
    )


def metric_grid(cartoes: list[dict]) -> None:
    """Vários cartões numa grade responsiva. Cada item aceita as mesmas chaves de
    `metric_card`: label, value, delta e, opcionalmente, accent e attention."""
    html = "".join(_metric_html(**cartao) for cartao in cartoes)
    st.html(f'<div class="pc-metric-grid">{html}</div>')


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


# Expressão (Vega) dos rótulos dos eixos: 250000 -> "250 k", 2500000 -> "2,5 mi".
EIXO_NUMERO_EXPR = (
    "datum.value >= 1000000000 "
    "? replace(format(datum.value / 1000000000, '.2~f'), '.', ',') + ' bi' "
    ": datum.value >= 1000000 "
    "? replace(format(datum.value / 1000000, '.2~f'), '.', ',') + ' mi' "
    ": datum.value >= 1000 "
    "? replace(format(datum.value / 1000, '.1~f'), '.', ',') + ' k' "
    ": format(datum.value, '.0f')"
)


def formatar_inteiro(valor: float) -> str:
    """Número inteiro com ponto como separador de milhar (1.234.567)."""
    return f"{round(valor):,}".replace(",", ".")


def abreviar_numero(valor: float, moeda: bool = False) -> str:
    """Número compacto em pt-BR: 850, 385,2 k, 1,31 mi, 2,5 bi (com `moeda`, R$ na frente)."""
    absoluto = abs(round(valor))
    if absoluto >= 1_000_000_000:
        texto = f"{valor / 1_000_000_000:.2f}".rstrip("0").rstrip(".") + " bi"
    elif absoluto >= 1_000_000:
        texto = f"{valor / 1_000_000:.2f}".rstrip("0").rstrip(".") + " mi"
    elif absoluto >= 1_000:
        texto = f"{valor / 1_000:.1f}".rstrip("0").rstrip(".") + " k"
    else:
        texto = f"{valor:.0f}"
    texto = texto.replace(".", ",")
    return f"R$ {texto}" if moeda else texto


def formatar_moeda_inteira(valor: float) -> str:
    """Moeda sem centavos, para rótulos de gráfico (R$ 1.234.567)."""
    return f"R$ {formatar_inteiro(valor)}"


def formatar_moeda(valor: float) -> str:
    """Formata valores numéricos para o padrão de moeda brasileiro (R$ X.XXX,XX)."""
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


MESES_ABREV = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set"]
MESES_ABREV += ["Out", "Nov", "Dez"]
MESES_LABEL = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}
# Expressão (Vega) do eixo dos meses ("Nov/25"): só o primeiro mês e janeiro
# mostram o ano, numa segunda linha sob o mês.
EIXO_MESES_EXPR = (
    "datum.index == 0 || slice(datum.label, 0, 3) == 'Jan' "
    "? [slice(datum.label, 0, 3), '20' + slice(datum.label, 4, 6)] "
    ": slice(datum.label, 0, 3)"
)


def rotulo_mes(competencia: str) -> str:
    """ "2025-11" -> "Nov/25"."""
    return f"{MESES_ABREV[int(competencia[5:7]) - 1]}/{competencia[2:4]}"


def formatar_competencia(competencia: str) -> str:
    """ "2025-11" -> "Novembro/2025"."""
    data = datetime.strptime(competencia, "%Y-%m")
    return f"{MESES_LABEL[data.month]}/{data.year}"
