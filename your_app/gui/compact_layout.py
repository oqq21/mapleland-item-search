"""Viewport-sized workspace; scrolling belongs to the result grid and popovers."""

COMPACT_CSS = '''<style>
html, body, [data-testid="stAppViewContainer"] {height:100%;overflow:hidden;}
[data-testid="stHeader"], footer {display:none;}
[data-testid="stSidebar"] {width:176px!important;min-width:176px!important;max-width:176px!important;}
[data-testid="stSidebarUserContent"] {padding:12px 8px;}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {gap:5px;}
[data-testid="stSidebar"] button {min-height:34px;padding:5px 8px;}
[data-testid="stSidebar"] button p {font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px;}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {font-size:13px;}
[data-testid="stMain"] {height:100dvh;overflow:hidden;}
[data-testid="stMainBlockContainer"] {height:100%;max-width:100%;padding:8px 12px;overflow:hidden;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {height:100%;min-height:0;gap:0;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> .st-key-workspace) {height:100%;min-height:0;flex:1 1 0%;}
.st-key-workspace {height:100%;min-height:0;gap:7px!important;}
.st-key-workspace > div {flex-shrink:0;}
.st-key-workspace [data-testid="stHorizontalBlock"] {gap:8px;align-items:center;}
.st-key-workspace [data-testid="stForm"] {border:0;padding:0;}
.st-key-workspace [data-testid="stForm"] [data-testid="stVerticalBlock"] {gap:0;}
.st-key-workspace [data-testid="stTextInput"] > div {min-height:36px;}
.st-key-workspace [data-baseweb="input"] {min-height:36px;height:36px;font-size:16px;}
.st-key-workspace input {height:34px;min-height:34px;padding:5px 10px;font-size:16px;}
.st-key-workspace button {min-height:36px;padding:5px 12px;font-size:15px;line-height:1.35;}
.st-key-workspace button p {font-size:15px;line-height:1.35;}
.st-key-workspace [data-testid="stWidgetLabel"] p {font-size:14px;line-height:1.35;}
.st-key-workspace [data-testid="stLinkButton"] a {min-height:36px;padding:5px 12px;font-size:15px;}
.st-key-workspace [data-testid="stCaptionContainer"] p {font-size:14px;line-height:1.35;margin:0;}
.st-key-workspace [data-testid="stMarkdownContainer"] p {margin:0;}
.app-title {font-size:20px;font-weight:750;line-height:36px;white-space:nowrap;color:#26354a;}
.app-meta {font-size:12px;color:#687487;line-height:1.3;text-align:right;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.applied-query {font-size:14px;line-height:1.4;color:#526074;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}
.st-key-search_fields {gap:4px!important;border:1px solid #dbe2ec;border-radius:8px;padding:8px 10px;background:#f8faff;}
.st-key-search_fields [data-testid="stHorizontalBlock"] {align-items:flex-end;}
.st-key-filter_fields {gap:7px!important;padding:8px 4px;}
.filter-label {font-size:15px;font-weight:650;line-height:36px;white-space:nowrap;}
.st-key-workspace > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-results_"]) {flex:1 1 0%!important;height:0;min-height:0;display:flex;flex-direction:column;overflow:hidden;}
.st-key-workspace [class*="st-key-results_"] {flex:1 1 0%!important;min-height:0!important;overflow:hidden;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stVerticalBlock"] {height:100%;min-height:0;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stElementContainer"] {height:100%;min-height:0;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stHtml"] {height:100%;min-height:0;}
.st-key-workspace .search-grid {height:100%;max-height:none;min-height:0;overscroll-behavior:contain;}
.st-key-workspace .search-grid th {padding:7px 6px;}
.st-key-workspace .search-grid td {padding:6px;}
[data-testid="stPopoverBody"] {max-height:75dvh;overflow:auto;overscroll-behavior:contain;}
[data-testid="stPopoverBody"] button {min-height:36px;padding:5px 11px;}
[data-testid="stPopoverBody"] p {font-size:16px;}
[role="dialog"]:has(.gem-price-table) {width:min(900px,94vw)!important;max-width:94vw;max-height:94dvh;overflow:auto;}
.gem-price-table {width:100%;border-collapse:collapse;font-size:16px;line-height:1.4;}
.gem-price-table th,.gem-price-table td {padding:6px 12px;border-bottom:1px solid #dce3ed;text-align:right;}
.gem-price-table th {background:#edf2fa;font-weight:700;}
.gem-price-table th:first-child,.gem-price-table td:first-child {text-align:left;}
@media(max-width:900px) {
 [data-testid="stMainBlockContainer"] {padding:6px 8px;}
 .st-key-workspace [data-testid="stHorizontalBlock"] {gap:5px;}
 .app-title {font-size:18px;}
 .st-key-workspace button {padding:5px 9px;}
 .app-meta {display:none;}
}
</style>'''
