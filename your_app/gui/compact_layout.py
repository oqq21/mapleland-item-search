"""Viewport-sized workspace; scrolling belongs to the result grid and popovers."""

COMPACT_CSS = '''<style>
html, body, [data-testid="stAppViewContainer"] {height:100%;overflow:hidden;}
[data-testid="stHeader"], [data-testid="stSidebar"], footer {display:none;}
[data-testid="stMain"] {height:100dvh;overflow:hidden;}
[data-testid="stMainBlockContainer"] {height:100%;max-width:100%;padding:8px 12px;overflow:hidden;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {height:100%;min-height:0;gap:0;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> .st-key-workspace) {height:100%;min-height:0;flex:1 1 0%;}
.st-key-workspace {height:100%;min-height:0;gap:5px!important;}
.st-key-workspace > div {flex-shrink:0;}
.st-key-workspace [data-testid="stHorizontalBlock"] {gap:8px;align-items:center;}
.st-key-workspace [data-testid="stForm"] {border:0;padding:0;}
.st-key-workspace [data-testid="stForm"] [data-testid="stVerticalBlock"] {gap:0;}
.st-key-workspace [data-testid="stTextInput"] > div {min-height:30px;}
.st-key-workspace [data-baseweb="input"], .st-key-workspace [data-baseweb="select"] > div {min-height:30px;height:30px;font-size:13px;}
.st-key-workspace input {height:28px;min-height:28px;padding:4px 8px;font-size:13px;}
.st-key-workspace button {min-height:28px;padding:3px 10px;font-size:13px;line-height:1.3;}
.st-key-workspace button p, .st-key-workspace [data-testid="stWidgetLabel"] p {font-size:13px;line-height:1.35;}
.st-key-workspace [data-testid="stLinkButton"] a {min-height:28px;padding:3px 10px;font-size:13px;}
.st-key-workspace [data-testid="stCaptionContainer"] p {font-size:12px;line-height:1.35;margin:0;}
.st-key-workspace [data-testid="stMarkdownContainer"] p {margin:0;}
.app-title {font-size:17px;font-weight:750;line-height:28px;white-space:nowrap;color:#26354a;}
.app-meta {font-size:11px;color:#687487;line-height:1.3;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.result-summary {font-size:12px;line-height:28px;color:#526074;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}
.applied-query {font-size:12px;line-height:1.4;color:#526074;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}
.st-key-workspace > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-results_"]) {flex:1 1 0%!important;height:0;min-height:0;display:flex;flex-direction:column;overflow:hidden;}
.st-key-workspace [class*="st-key-results_"] {flex:1 1 0%!important;min-height:0!important;overflow:hidden;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stVerticalBlock"] {height:100%;min-height:0;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stElementContainer"] {height:100%;min-height:0;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stHtml"] {height:100%;min-height:0;}
.st-key-workspace .search-grid {height:100%;max-height:none;min-height:0;overscroll-behavior:contain;}
.st-key-workspace .search-grid th {padding:7px 9px;}
.st-key-workspace .search-grid td {padding:6px 9px;}
[data-testid="stPopoverBody"] {max-height:75dvh;overflow:auto;overscroll-behavior:contain;}
[data-testid="stPopoverBody"] button {min-height:28px;padding:4px 9px;}
[data-testid="stPopoverBody"] p {font-size:13px;}
@media(max-width:900px) {
 [data-testid="stMainBlockContainer"] {padding:6px 8px;}
 .st-key-workspace [data-testid="stHorizontalBlock"] {gap:5px;}
 .app-title {font-size:15px;}
 .st-key-workspace button {padding:3px 7px;}
 .app-meta {display:none;}
}
</style>'''
