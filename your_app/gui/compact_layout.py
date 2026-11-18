"""Viewport-sized workspace; scrolling belongs to the result grid and popovers."""

COMPACT_CSS = '''<style>
html, body, [data-testid="stAppViewContainer"] {height:100%;overflow:hidden;}
[data-testid="stHeader"], footer {display:none;}
[data-testid="stMain"] {height:100dvh;overflow:hidden;}
[data-testid="stMainBlockContainer"] {height:100%;max-width:100%;padding:10px 16px;overflow:hidden;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {height:100%;min-height:0;gap:0;}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:has(> .st-key-workspace) {height:100%;min-height:0;flex:1 1 0%;}
.st-key-workspace {height:100%;min-height:0;gap:7px!important;}
.st-key-workspace > div {flex-shrink:0;}
.st-key-workspace [data-baseweb="input"] {min-height:42px;}
.st-key-workspace input {min-height:40px;padding:6px 12px;font-size:18px;}
.st-key-workspace button {min-height:38px;padding:5px 12px;font-size:16px;line-height:1.35;}
.st-key-workspace button p {font-size:16px;line-height:1.35;}
.st-key-workspace [data-testid="stWidgetLabel"] p {font-size:16px;line-height:1.35;}
.st-key-workspace [data-testid="stLinkButton"] a {min-height:38px;padding:5px 12px;font-size:16px;}
.st-key-workspace [data-testid="stCaptionContainer"] p {font-size:14px;line-height:1.35;margin:0;}
.st-key-workspace [data-testid="stMarkdownContainer"] p {margin:0;}
.app-title {font-size:23px;font-weight:750;line-height:38px;margin-right:12px;white-space:nowrap;color:#26354a;}
.applied-query {font-size:14px;line-height:1.4;color:#526074;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;}
.st-key-search_controls [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-search_fields) {
 display:grid;grid-template-columns:minmax(0,510px) minmax(275px,320px) minmax(210px,1fr);gap:14px;
}
.st-key-search_fields {gap:5px!important;border:1px solid #dbe2ec;border-radius:8px;padding:9px 12px;background:#f8faff;}
.st-key-search_fields [data-testid="stHorizontalBlock"] {
 display:grid;grid-template-columns:repeat(3,minmax(0,1fr)) minmax(68px,.65fr);align-items:end;gap:8px;
}
.st-key-search_controls [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-search_fields) > [data-testid="stColumn"],
.st-key-search_fields [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width:100%;min-width:0;}
.st-key-search_fields [data-testid="stButton"] button {min-height:42px;}
.st-key-filter_fields {gap:5px!important;padding:4px 0;}
.filter-label {min-width:44px;font-size:16px;font-weight:700;line-height:38px;white-space:nowrap;}
.st-key-recent_searches {padding-top:4px;}
.recent-label {font-size:14px;font-weight:700;line-height:1.5;}
.st-key-workspace .st-key-recent_searches button {min-height:28px;max-width:174px;padding:3px 7px;font-size:13px;}
.st-key-workspace .st-key-recent_searches button p {font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.st-key-pagination button {min-height:34px;}
.st-key-workspace > [data-testid="stLayoutWrapper"]:has(> [class*="st-key-results_"]) {flex:1 1 0%!important;height:0;min-height:0;display:flex;flex-direction:column;overflow:hidden;}
.st-key-workspace [class*="st-key-results_"] {flex:1 1 0%!important;min-height:0!important;overflow:hidden;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stVerticalBlock"] {height:100%;min-height:0;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stElementContainer"] {height:100%;min-height:0;}
.st-key-workspace [class*="st-key-results_"] [data-testid="stHtml"] {height:100%;min-height:0;}
.st-key-workspace .search-grid {height:100%;max-height:none;min-height:0;overscroll-behavior:contain;}
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
 .app-title {font-size:20px;}
 .st-key-workspace button {padding:5px 9px;}
 .st-key-search_controls [data-testid="stHorizontalBlock"]:has(> [data-testid="stColumn"] .st-key-search_fields) {grid-template-columns:minmax(0,1fr);gap:7px;}
 .st-key-search_fields {max-width:510px;}
 .st-key-filter_fields {display:flex;flex-flow:row wrap;column-gap:12px!important;}
 .st-key-filter_fields > [data-testid="stLayoutWrapper"] {width:auto;}
 .st-key-filter_fields > [data-testid="stElementContainer"]:has(.applied-query) {flex-basis:100%;}
}
@media(max-width:560px) {
 .st-key-search_fields {padding:7px 8px;}
 .st-key-search_fields button {padding:4px 6px;}
 .st-key-workspace input {font-size:16px;padding-inline:6px;}
 .filter-label {min-width:36px;}
}
</style>'''
