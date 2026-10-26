"""Observed runtime, routing and API usage metrics; absent measurements stay unknown."""
from collections import Counter
import math


def finite_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def usage_metrics(envelope, model, pricing=None, api_currency="API"):
    usage = envelope.get("usage") or {}
    def number(container, key):
        value = container.get(key)
        return value if finite_number(value) else None
    details = usage.get("completion_tokens_details") or {}
    inputs = usage.get("prompt_tokens_details") or {}
    tokens = {"input": number(usage, "prompt_tokens"), "output": number(usage, "completion_tokens"),
              "total": number(usage, "total_tokens"), "reasoning": number(details, "reasoning_tokens"),
              "cached_input": number(inputs, "cached_tokens")}
    if tokens["total"] is None and tokens["input"] is not None and tokens["output"] is not None:
        tokens["total"] = tokens["input"] + tokens["output"]
    cost = None
    if finite_number(usage.get("cost")):
        cost = {"amount": usage["cost"], "currency": usage.get("cost_currency") or api_currency, "source": "api"}
    elif pricing and model in pricing.get("models", {}) and tokens["input"] is not None and tokens["output"] is not None:
        rate = pricing["models"][model]
        cached = min(tokens["input"], tokens["cached_input"] or 0)
        amount = ((tokens["input"] - cached) * rate["input_per_million"] +
                  cached * rate.get("cached_input_per_million", rate["input_per_million"]) +
                  tokens["output"] * rate["output_per_million"]) / 1_000_000
        cost = {"amount": amount, "currency": pricing["currency"], "source": "estimate"}
    return {"tokens": tokens, "cost": cost}


def validate_pricing(value):
    if not isinstance(value, dict) or not isinstance(value.get("currency"), str) or not value["currency"] or not isinstance(value.get("models"), dict):
        raise ValueError("pricing: ожидаются currency и models")
    for rate in value["models"].values():
        if not isinstance(rate, dict) or any(not finite_number(rate.get(k)) for k in ("input_per_million", "output_per_million")):
            raise ValueError("pricing: нужны неотрицательные input_per_million и output_per_million")
        if "cached_input_per_million" in rate and not finite_number(rate["cached_input_per_million"]):
            raise ValueError("pricing: некорректный cached_input_per_million")
    return value


def distribution(values):
    values = sorted(v for v in values if v is not None and math.isfinite(v))
    if not values:
        return {"n": 0, "sum": 0, "mean": None, "p50": None, "p95": None, "min": None, "max": None}
    def percentile(p):
        position = (len(values)-1)*p
        left = int(position)
        right = min(left+1,len(values)-1)
        return values[left] + (values[right]-values[left])*(position-left)
    return {"n":len(values), "sum":sum(values), "mean":sum(values)/len(values),
            "p50":percentile(.5), "p95":percentile(.95), "min":values[0], "max":values[-1]}


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def summarize_cpu_inference(batches):
    if not batches:
        return {"batches": 0, "queries": 0, "elapsed_seconds": distribution([]), "by_length": {}}
    rows = []
    for item in batches:
        size = int(item.get("batch_size", 0))
        elapsed = item.get("elapsed_seconds")
        if size and finite_number(elapsed):
            rows.extend({"chars": item.get("avg_chars", 0), "seconds": elapsed / size} for _ in range(size))
    buckets = (("0-256", -1, 256), ("257-512", 256, 512), ("513-1024", 512, 1024), ("1025+", 1024, float("inf")))
    by_length = {}
    for name, low, high in buckets:
        values = [row["seconds"] for row in rows if low < row["chars"] <= high]
        by_length[name] = {**distribution(values), "chars_min_exclusive": low, "chars_max": None if high == float("inf") else high}
    return {"batches": len(batches), "queries": len(rows),
            "elapsed_seconds": distribution([row["seconds"] for row in rows]),
            "by_length": by_length,
            "measurement": "batch duration / batch size; buckets use average batch text length",
            "batch_elapsed_seconds": distribution([b.get("elapsed_seconds") for b in batches])}


def summarize_requests(events):
    calls = [e for e in events if e.get("source") == "api"]
    totals = {}
    for field in ("input", "output", "total", "reasoning", "cached_input"):
        measured = [e.get("tokens", {}).get(field) for e in calls]
        known = [v for v in measured if finite_number(v)]
        totals[field] = {"known_sum":sum(known), "measured_calls":len(known), "total_calls":len(calls),
                         "complete":len(known)==len(calls)}
    costs = {}
    for event in calls:
        cost = event.get("cost")
        if cost is None:
            continue
        key = (cost["currency"], cost["source"])
        item = costs.setdefault(key, {"currency":key[0], "source":key[1], "amount":0, "calls":0})
        item["amount"] += cost["amount"]
        item["calls"] += 1
    measured_costs = sum(item["calls"] for item in costs.values())
    return {"api_calls":len(calls), "cache_hits":sum(e.get("source")=="cache" for e in events),
            "successful_calls":sum(e.get("outcome")=="success" for e in calls),
            "failed_calls":sum(e.get("outcome")!="success" for e in calls),
            "retries":sum(e.get("attempt",1)>1 for e in calls),
            "fallback_calls":sum(e.get("fallback",False) for e in calls),
            "http_429":sum(e.get("http_status")==429 for e in calls),
            "http_5xx":sum(e.get("http_status",0)>=500 for e in calls),
            "invalid_responses":sum(e.get("outcome")=="invalid_response" for e in calls),
            "timeouts_or_network_errors":sum(e.get("outcome")=="network_error" for e in calls),
            "latency_seconds":distribution([e.get("duration_seconds") for e in calls]),
            "tokens":totals, "costs":list(costs.values()), "cost_measured_calls":measured_costs,
            "cost_unknown_calls":len(calls)-measured_costs, "cost_complete":measured_costs==len(calls)}


def with_breakdowns(events):
    result = summarize_requests(events)
    for field in ("model", "stage"):
        result["by_"+field] = {key:summarize_requests([e for e in events if e.get(field)==key])
                               for key in sorted({e[field] for e in events if e.get(field)})}
    return result


def result_route(record):
    if record.get("analysis_kind") == "qwen_screening":
        return "qwen_screening"
    if record.get("analysis_kind") == "kimi_final" or record.get("model", "").startswith("moonshotai/"):
        return "kimi_final"
    if record.get("routing", {}).get("qwen_multi_source"):
        return "multi_source_qwen"
    return record.get("status", "unknown")


def historical_metrics_missing(record):
    telemetry = record.get('telemetry', {})
    return bool(telemetry.get('historical_metrics_missing') or
                ((record.get('assessment') or record.get('topic_id') is not None)
                 and not telemetry.get('analysis_requests')))


def build_metrics(records, events, elapsed, requested, setup_seconds=0, export_seconds=0, funnel=None):
    current = with_breakdowns(events)
    history = {e["request_id"]:e for record in records for e in record.get("telemetry", {}).get("analysis_requests", [])}
    analysis = with_breakdowns(list(history.values()))
    routes = Counter(result_route(r) for r in records)
    preliminary = []
    reviewed = []
    def preliminary_score(r):
        a = r['preliminary']
        if not a.get('related'):
            return 0
        return (40 * a.get('related', False) + 25 * a.get('direct', False)
                + 20 * a.get('fact', False) + 15 * a.get('within_month', False))
    changes = [r['importance']-preliminary_score(r) for r in reviewed if 'importance' in r]
    assessed = [r for r in records if 'importance' in r]
    missing = sum(historical_metrics_missing(r) for r in records)
    per_news = []
    for r in records:
        t=r.get('telemetry',{})
        owned = [e for e in events if str(e.get('event_id'))==str(r['event_id'])]
        per_news.append({'event_id':r['event_id'], 'status':r['status'], 'route':result_route(r),
                         'publications':len(r.get('members',[])), 'sources':r.get('sources',0),
                         'resumed':t.get('resumed',False), 'processing_seconds':t.get('processing_seconds'),
                         'analysis_seconds':t.get('analysis_seconds'), 'importance':r.get('importance'),
                         'current_run':summarize_requests(owned),
                         'analysis':summarize_requests(t.get('analysis_requests',[])),
                         'historical_metrics_missing':historical_metrics_missing(r)})
    api_events = len({str(e.get('event_id')) for e in events if e.get('source')=='api'})
    current['events_with_api'] = api_events
    current['events_without_api'] = len(records)-api_events
    current['tokens_per_api_event'] = ratio(current['tokens']['total']['known_sum'], api_events)
    current['cost_per_api_event'] = [{**c,'amount':c['amount']/api_events} for c in current['costs']] if api_events else []
    current['cost_per_processed_news']=[{**c,'amount':c['amount']/len(records)} for c in current['costs']] if records else []
    current['tokens_per_processed_news']=ratio(current['tokens']['total']['known_sum'],len(records))
    current['api_calls_per_processed_news']=ratio(current['api_calls'],len(records))
    publications=sum(len(r.get('members',[])) for r in records)
    routing = {'routes':dict(routes), 'qwen_assessed':len([r for r in records if r.get('analysis_kind') == 'qwen_screening']),
               'escalations':0, 'escalation_rate':None,
               'reviews_completed':sum(r.get('analysis_kind') == 'kimi_final' for r in records),
               'direct_kimi':sum(1 for r in records if r.get('impact') == 'прямое' and r.get('analysis_kind') == 'kimi_final'),
               'qwen_to_kimi':sum(1 for r in records if r.get('analysis_kind') == 'kimi_final' and r.get('routing', {}).get('kimi_after_qwen') is True),
               'multi_source_qwen':routes['multi_source_qwen'],
               'source_promotions':sum(r.get('routing',{}).get('source_promotion',False) for r in records),
               'review_importance_delta':distribution(changes),
               'review_downgraded_below_50':sum(r.get('importance',100)<50 for r in reviewed),
               'review_removed_from_feed':sum(r.get('importance',100)<50 for r in reviewed)}
    llm_interesting = sum(r.get('status') in ('feed', 'tracked') for r in records)
    llm_uninteresting = sum(r.get('status') == 'weak' for r in records)
    category_counts = Counter(label.get('label') for r in records for label in r.get('matched_labels', []) if label.get('label'))
    cpu_batches = (funnel or {}).get('inference_cpu', [])
    funnel_data = {**(funnel or {}),
                   'processed_clusters': len(records), 'processed_publications': publications,
                   'requested_clusters': requested, 'category_counts': dict(category_counts),
                   'llm_interesting': llm_interesting, 'llm_uninteresting': llm_uninteresting,
                   'feed_news': sum(r.get('status') == 'feed' for r in records),
                   'feed_publications': sum(len(r.get('members', [])) for r in records if r.get('status') == 'feed'),
                   'tracked_news': sum(r.get('status') == 'tracked' for r in records),
                   'weak_news': llm_uninteresting,
                   'cpu_inference': summarize_cpu_inference(cpu_batches),
                   'llm_latency_by_model': current.get('by_model', {}),
                   'analysis_llm_latency_by_model': analysis.get('by_model', {}),
                   'qwen_kimi_routing': True}
    return {'unit':'news = event cluster, not individual publication',
            'elapsed_seconds':elapsed, 'setup_seconds':setup_seconds, 'export_seconds':export_seconds,
            'processed':len(records), 'requested':requested, 'remaining':requested-len(records),
            'completed':sum(r['status'] != 'error' for r in records),
            'failed':sum(r['status'] == 'error' for r in records),
            'publications':publications, 'publication_to_event_ratio':ratio(publications,len(records)),
            'events_per_minute':ratio(60*len(records),elapsed),
            'statuses':dict(Counter(r['status'] for r in records)),
            'impacts':dict(Counter(r['impact'] for r in records)),
            'resumed_events':sum(r.get('telemetry',{}).get('resumed',False) for r in records),
            'current_run':current, 'result_analysis':analysis, 'historical_metrics_missing_events':missing,
            'routing':routing, 'importance':distribution([r['importance'] for r in assessed]),
            'processing_seconds_per_news':distribution([r.get('telemetry',{}).get('processing_seconds') for r in records]),
            'analysis_api_seconds_per_news':distribution([
                sum(e.get('duration_seconds', 0) for e in r.get('telemetry', {}).get('analysis_requests', [])
                    if e.get('source') == 'api') for r in records
                if r.get('telemetry', {}).get('analysis_requests')]),
            'sources_per_event':distribution([r.get('sources',0) for r in records]),
            'feed_yield':ratio(sum(r['status']=='feed' for r in records),len(records)),
            'funnel': funnel_data,
            'per_news':per_news,
            'quality_note':'Precision/recall/NDCG и точность LLM требуют эталонной разметки; здесь не вычисляются.'}


def render_metrics(metrics):
    """Static HTML keeps the report accessible without duplicating calculations in JS."""
    if not metrics:
        return ""
    from html import escape
    esc = lambda value: escape(str(value))
    fmt = lambda value: "—" if value is None else f"{value:,.3f}".replace(",", " ")
    integer = lambda value: "—" if value is None else f"{value:,.0f}".replace(",", " ")
    def money(summary):
        costs=summary.get('costs',[])
        if not costs:
            return '0 (нет API-вызовов)' if not summary.get('api_calls') else 'нет данных'
        text=' + '.join(f"{item['amount']:.8f} {esc(item['currency'])}" + (' (оценка)' if item['source']=='estimate' else '') for item in costs)
        if summary.get('cost_unknown_calls'):
            text+=f"; ещё {summary['cost_unknown_calls']} выз. без стоимости"
        return text
    def token_text(summary, field='total'):
        item=summary['tokens'][field]
        text=integer(item['known_sum'])
        if not item['complete']:
            text+=f" (известно для {item['measured_calls']}/{item['total_calls']} выз.)"
        return text
    def table(headers, rows):
        return '<div class="scroll-table"><table><thead><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    current=metrics['current_run'];history=metrics['result_analysis'];routing=metrics['routing'];funnel=metrics.get('funnel',{})
    names={'qwen_screening':'Скрининг Qwen','kimi_final':'Финальный анализ Kimi','qwen_multi_source':'Скрининг Qwen: >5 источников','multi_source_qwen':'Скрининг Qwen: >5 источников'}
    processing=metrics['processing_seconds_per_news'];latency=current['latency_seconds']
    rows=[['Исходный корпус: сырых публикаций / после ruBERT / после кластеризации',
           ' / '.join(integer(funnel.get(k)) for k in ('raw_news','bert_retained','clustered_news'))],
          ['После отбора источников компании: публикаций / кластеров',
           f"{integer(funnel.get('company_publications'))} / {integer(funnel.get('company_clusters'))}"],
          ['LLM обработано событий / публикаций',f"{metrics['processed']} / {metrics['publications']}"],
          ['LLM план / осталось',f"{metrics['requested']} / {metrics['remaining']}"],
          ['LLM завершено / с ошибкой',f"{metrics.get('completed', metrics['processed'])} / {metrics.get('failed', 0)}"],
          ['Время запуска, с',fmt(metrics['elapsed_seconds'])],
          ['Подготовка / экспорт предыдущих снимков, с',fmt(metrics['setup_seconds'])+' / '+fmt(metrics['export_seconds'])],
          ['Событий в минуту',fmt(metrics['events_per_minute'])],
          ['Время на событие в текущем запуске (включая кеш): среднее / p50 / p95, с',' / '.join(fmt(processing[k]) for k in ('mean','p50','p95'))],
          ['Время API-запроса: среднее / p50 / p95, с',' / '.join(fmt(latency[k]) for k in ('mean','p50','p95'))],
          ['API-вызовы: успешные / неуспешные',f"{current['successful_calls']} / {current['failed_calls']}"],
          ['Повторы / резервный адрес',f"{current['retries']} / {current['fallback_calls']}"],
          ['HTTP 429 / HTTP 5xx / невалидный ответ / сеть',f"{current['http_429']} / {current['http_5xx']} / {current['invalid_responses']} / {current['timeouts_or_network_errors']}"],
          ['Кэш ответов / события из сохранённого состояния',f"{current['cache_hits']} / {metrics['resumed_events']}"],
          ['Токены вход / выход / всего',' / '.join(token_text(current,k) for k in ('input','output','total'))],
          ['Reasoning / кэшированные входные токены',token_text(current,'reasoning')+' / '+token_text(current,'cached_input')],
          ['Событий с API / без API',f"{current['events_with_api']} / {current['events_without_api']}"],
          ['Расход текущего запуска',money(current)],
          ['Средние токены на событие с API',fmt(current['tokens_per_api_event'])+(' (частичные данные)' if not current['tokens']['total']['complete'] else '')],
          ['Средний расход на событие с API',money({**current,'costs':current['cost_per_api_event']})],
          ['Средние токены на обработанное событие',fmt(current['tokens_per_processed_news'])+(' (частичные данные)' if not current['tokens']['total']['complete'] else '')],
          ['Средний расход на обработанное событие',money({**current,'costs':current['cost_per_processed_news']} )],
          ['Известный расход исходного анализа результатов',money(history)],
          ['Исходный анализ: API-вызовы / входные / выходные / все токены',str(history['api_calls'])+' / '+' / '.join(token_text(history,k) for k in ('input','output','total'))],
          ['Исходные API-вызовы: среднее / p50 / p95, с',' / '.join(fmt(history['latency_seconds'][k]) for k in ('mean','p50','p95'))],
          ['Результаты без исторической телеметрии',str(metrics['historical_metrics_missing_events'])],
          ['Первичная → полная оценка: событий / доля первичных оценок',str(routing['escalations'])+' / '+('—' if routing['escalation_rate'] is None else f"{100*routing['escalation_rate']:.1f}%")],
          ['Сразу полный анализ по правилу >5 источников',str(routing.get('multi_source_qwen',0))],
          ['Повторный анализ при пересечении порога источников',str(routing.get('source_promotions',0))],
          ['Прямой анализ Kimi / завершённые финальные анализы',f"{routing.get('direct_kimi',0)} / {routing['reviews_completed']}"],
          ['После перепроверки: I < 50 / убраны из ленты',f"{routing['review_downgraded_below_50']} / {routing['review_removed_from_feed']}"],
          ['Изменение I после полного анализа: среднее / min / max',' / '.join(fmt(routing['review_importance_delta'][k]) for k in ('mean','min','max'))],
          ['Попало в ленту, %',fmt(100*metrics['feed_yield']) if metrics['feed_yield'] is not None else '—'],
          ['Маршруты',esc(', '.join(f'{names.get(k,k)}: {v}' for k,v in routing['routes'].items()))],
          ['Разделы',esc(', '.join(f'{k}: {v}' for k,v in metrics['statuses'].items()))]]
    html='<section id="metrics-report"><h2>Метрики тестового запуска</h2><p class="muted">Единица новости — кластер-событие. Средние расходы включают события без LLM. Время текущего запуска относится к шагам 3–7; ruBERT/BGE уже выполнены. Исходный анализ включает сохранённые API-вызовы: их стоимость не прибавляется к расходу текущего запуска. API означает единицы стоимости шлюза без подтверждённой валюты. Неизвестные расходы не считаются нулевыми. Статистика относится ко всему запуску, а не к фильтрам ленты.</p>'
    if metrics['historical_metrics_missing_events']:
        html+='<p class="muted">История расходов и токенов неполная: отсутствуют измерения для '+str(metrics['historical_metrics_missing_events'])+' событий. Приведены только известные суммы.</p>'
    html+='<details open><summary>Время, расходы и маршрутизация</summary>'+table(['Метрика','Значение'],rows)+'</details>'
    funnel_rows=[
        ['Всего сырых новостей', integer(funnel.get('raw_news'))],
        ['После ruBERT: классифицировано / оставлено', f"{integer(funnel.get('bert_classified'))} / {integer(funnel.get('bert_retained'))}"],
        ['Кластеризовано публикаций / кластеров', f"{integer(funnel.get('clustered_news'))} / {integer(funnel.get('clusters'))}"],
        ['После отбора источников компании: публикаций / кластеров', f"{integer(funnel.get('company_publications'))} / {integer(funnel.get('company_clusters'))}"],
        ['Запрошено / обработано кластеров', f"{integer(funnel.get('requested_clusters'))} / {integer(funnel.get('processed_clusters'))}"],
        ['Публикаций в обработанных кластерах', integer(funnel.get('processed_publications'))],
        ['Источники RSS', f"{integer(funnel.get('source_count_rss'))}"],
        ['Исключено после фильтра источников', integer(funnel.get('source_excluded_news'))],
        ['В ленте / отслеживаемые', f"{integer(funnel.get('feed_news'))} / {integer(funnel.get('tracked_news'))}"],
        ['Публикаций в событиях ленты / доля сырых публикаций', '—' if not funnel.get('raw_news') else f"{integer(funnel.get('feed_publications'))} ({100 * funnel.get('feed_publications', 0) / funnel['raw_news']:.1f}%)"],
        ['LLM признала интересными / неинтересными', f"{integer(funnel.get('llm_interesting'))} / {integer(funnel.get('llm_uninteresting'))}"],
          ['Qwen → Kimi', str(sum(r.get('analysis_kind') == 'kimi_final' and r.get('routing', {}).get('kimi_after_qwen') for r in metrics.get('per_news', [])))],
        ['Категории кластеров', esc(', '.join(f'{k}: {v}' for k,v in sorted(funnel.get('category_counts', {}).items()))) or '—'],
    ]
    html+='<details open><summary>Итоговая воронка отбора новостей</summary>'+table(['Этап','Количество'],funnel_rows)+'</details>'
    cpu=funnel.get('cpu_inference',{})
    cpu_rows=[]
    for name,item in cpu.get('by_length',{}).items():
        cpu_rows.append([name, integer(item.get('n')), fmt(item.get('mean')), fmt(item.get('p50')), fmt(item.get('p95'))])
    if cpu_rows:
        html+='<details><summary>CPU-инференс ruBERT: амортизированное время</summary><p>Время батча делится на число текстов; группировка по средней длине батча. Это не замеры задержки отдельных запросов.</p>'+table(['Средняя длина батча, символы','Текстов','Среднее, с','p50, с','p95, с'],cpu_rows)+'</details>'
    else:
        html+='<p class="muted">Время CPU-инференса ruBERT: нет измерений в корпусе (например, использован кеш предсказаний).</p>'
    llm_rows=[]
    for model,item in current.get('by_model',{}).items():
        llm_rows.append([esc(model), item.get('api_calls',0), fmt(item.get('latency_seconds',{}).get('mean')), fmt(item.get('latency_seconds',{}).get('p50')), fmt(item.get('latency_seconds',{}).get('p95'))])
    if llm_rows:
        html+='<details><summary>Время вызовов LLM</summary>'+table(['Модель','Вызовов','Среднее, с','p50, с','p95, с'],llm_rows)+'</details>'
    history_rows=[]
    for model,item in history.get('by_model',{}).items():
        history_rows.append([esc(model),item['api_calls'],fmt(item['latency_seconds']['mean']),fmt(item['latency_seconds']['p95']),token_text(item),money(item)])
    if history_rows:
        html+='<details open><summary>Исходный анализ результатов · включая сохранённые вызовы</summary>'+table(['Модель','API','Среднее, с','p95, с','Токены','Стоимость'],history_rows)+'</details>'
    for field,title in [('model','По моделям'),('stage','По этапам')]:
        values=[]
        for key,summary in current['by_'+field].items():
            values.append([esc(names.get(key,key)),summary['api_calls'],summary['cache_hits'],summary['failed_calls'],fmt(summary['latency_seconds']['mean']),fmt(summary['latency_seconds']['p95']),token_text(summary),money(summary)])
        html+='<details open><summary>'+title+' · текущий запуск</summary>'+table(['Модель / этап','API','Кэш','Ошибки','Среднее, с','p95, с','Токены','Стоимость'],values)+'</details>'
    rows=[]
    for news in metrics['per_news']:
        rows.append([esc(news['event_id']),esc(names.get(news['route'],news['route'])),fmt(news['processing_seconds']),fmt(news['analysis_seconds']),
                     news['current_run']['api_calls'],token_text(news['current_run']),money(news['current_run']),
                     'нет исторических данных' if news['historical_metrics_missing'] else token_text(news['analysis']),
                     'нет исторических данных' if news['historical_metrics_missing'] else money(news['analysis']),fmt(news['importance'])])
    html+='<details><summary>Время, токены и стоимость каждой новости ('+str(len(rows))+')</summary>'+table(['Событие','Маршрут','Сейчас, с','Первичный анализ, с','API сейчас','Токены сейчас','Стоимость сейчас','Токены анализа','Стоимость анализа','I'],rows)+'</details>'
    html+='<p class="muted">'+esc(metrics['quality_note'])+' Стоимость без валюты отображается как API. Reasoning-токены входят в выходные токены и повторно к итогу не прибавляются. Неуспешные запросы включены в расход, если шлюз вернул usage.</p><button type="button" id="download-metrics">Скачать метрики JSON</button></section>'
    return html
