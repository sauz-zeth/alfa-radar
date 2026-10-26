"""Standalone, searchable HTML report from the cluster explorer."""
import json
import html

STYLE = """<style>
:root{color-scheme:light}body{margin:0;background:#f4f6f8;color:#18212b;font:14px/1.5 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:#fff;border-bottom:1px solid #d9e0e6;padding:14px max(18px,calc((100vw - 1200px)/2))}
main{max-width:1200px;margin:20px auto;padding:0 18px}h1{font-size:22px;margin:0 0 4px}.meta{color:#5f6b76;font-size:12px}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.controls input,.controls select,.controls button{font:inherit;padding:8px;border:1px solid #c8d1d9;border-radius:5px;background:#fff;color:inherit}
.controls input{flex:1;min-width:220px}.controls select{min-width:155px}.controls button{cursor:pointer}
details.cluster{border-bottom:1px solid #d8dfe5;padding:12px 0}summary{cursor:pointer;font-weight:600}article{border-left:3px solid #b8c7d4;padding:10px 14px;margin:10px 0;background:#fff}
.badge{display:inline-block;background:#e8f0f4;border-radius:4px;padding:2px 7px;margin:3px;font-size:12px}.post-meta{color:#65717c;font-size:12px}.text{white-space:pre-wrap;overflow-wrap:anywhere;margin-top:8px}
</style>"""
def esc(value):
    return html.escape(str(value), quote=True)
def badges(labels):
    return " ".join(f'<span class="badge">{esc(x["label"])} · {float(x["score"]):.1%}</span>' for x in labels)
def cluster_html(cluster):
    members=sorted(cluster["members"],key=lambda m:(m.get("date", ""),str(m.get("post_id", ""))))
    cards=[]
    for m in members:
        cards.append(f'<article><b>{esc(m["source"])}</b> <span class="post-meta">{esc(m.get("date", ""))} · ID {esc(m.get("post_id", ""))}</span><div>{badges(m.get("labels", []))}</div><div class="text">{esc(m.get("text", ""))}</div></article>')
    labels=json.dumps([x["label"].lower() for x in cluster.get("labels", [])],ensure_ascii=False)
    sources=json.dumps([x.lower() for x in cluster.get("sources", [])],ensure_ascii=False)
    title=members[0].get("text", "")[:110] if members else ""
    return (f'<details class="cluster" data-labels="{esc(labels.lower())}" data-sources="{esc(sources.lower())}"><summary>Кластер #{esc(cluster["event_id"])} · {len(members)} новостей · {esc(title)}</summary>'
            f'<p class="meta">{len(members)} новостей · {len(cluster.get("sources", []))} источников</p><div>{badges(cluster.get("labels", []))}</div>{"".join(cards)}</details>')
def export_html(path, clusters, run_info):
    if clusters is None or run_info is None:
        raise RuntimeError('Сначала выполните пересчет')
    parts=[cluster_html(c) for c in sorted(clusters,key=lambda c:(-len(c["members"]),c["event_id"]))]
    doc=('<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Кластеры новостей</title>'
         +STYLE+'<header><h1>Кластеры новостей</h1>'
         +f'<div class="meta">{len(clusters)} кластеров · BGE top-8 + локальный reranker · параметры: {esc(json.dumps(run_info,ensure_ascii=False))}</div>'
         +'<div class="controls"><input id="q" type="search" placeholder="Поиск по тексту, источнику или метке"><select id="source"><option value="">Все источники</option></select><select id="label"><option value="">Все метки</option></select><button id="open">Развернуть все</button><button id="close">Свернуть все</button></div></header><main><p id="count" class="meta"></p>'
         +''.join(parts)+"""<script>
const clusters=[...document.querySelectorAll('.cluster')];
const sourceSelect=document.querySelector('#source'), labelSelect=document.querySelector('#label');
function fill(select, values){for(const value of [...values].sort()){const option=document.createElement('option');option.value=value;option.textContent=value;select.append(option)}}
fill(sourceSelect,new Set(clusters.flatMap(x=>JSON.parse(x.dataset.sources))));
fill(labelSelect,new Set(clusters.flatMap(x=>JSON.parse(x.dataset.labels))));
function filter(){const q=document.querySelector('#q').value.trim().toLocaleLowerCase(),source=sourceSelect.value,label=labelSelect.value;let shown=0;for(const el of clusters){const text=el.textContent.toLocaleLowerCase();const ok=text.includes(q)&&(!source||JSON.parse(el.dataset.sources).includes(source))&&(!label||JSON.parse(el.dataset.labels).includes(label));el.hidden=!ok;if(ok)shown++}document.querySelector('#count').textContent=`Показано ${shown} из ${clusters.length} кластеров`}
for(const el of [document.querySelector('#q'),sourceSelect,labelSelect])el.addEventListener('input',filter);
document.querySelector('#open').onclick=()=>clusters.filter(x=>!x.hidden).forEach(x=>x.open=true);
document.querySelector('#close').onclick=()=>clusters.forEach(x=>x.open=false);filter();
</script></main></html>""")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(doc,encoding='utf-8')
    return path
