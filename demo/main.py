"""nicegui-diagnostics documentation & live demo.

This app dogfoods the diagnostics module — it installs itself and
displays its own diagnostic data. Run with: python demo/main.py
"""
from __future__ import annotations

from nicegui import ui

import nicegui_diagnostics


def main() -> None:
    # --- Global styles ---
    ui.add_head_html('''<style>
        .hero { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); }
        .metric-card { 
            background: rgba(255,255,255,0.05); 
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 1.5rem;
            transition: all 0.2s;
        }
        .metric-card:hover { 
            background: rgba(255,255,255,0.08);
            border-color: rgba(99, 102, 241, 0.5);
            transform: translateY(-2px);
        }
        .probe-card {
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 8px;
            padding: 1rem;
        }
        .stat-value { font-size: 2rem; font-weight: 700; line-height: 1; }
        .stat-label { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; opacity: 0.6; }
        .section-title { 
            font-size: 1.5rem; 
            font-weight: 600; 
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid rgba(99, 102, 241, 0.3);
        }
    </style>''')

    ui.dark_mode(True)

    # --- Hero section ---
    with ui.element('div').classes('hero w-full py-12 px-8'):  # noqa: SIM117 — nested with is intentional in NiceGUI
        with ui.row().classes('w-full max-w-6xl mx-auto items-center gap-8'):
            with ui.column().classes('flex-1'):
                ui.label('nicegui-diagnostics').classes('text-4xl font-bold text-white')
                ui.label(f'v{nicegui_diagnostics.__version__}').classes('text-lg text-indigo-300 mt-1')
                ui.label('Production-grade diagnostics for NiceGUI apps.').classes('text-xl text-gray-300 mt-4')
                ui.label('Born from a real 4.3 GB OOM. Caught actual NiceGUI bugs.').classes('text-gray-400 mt-2')
            with ui.column().classes('gap-3'):
                ui.button('Quick Start', on_click=lambda: ui.navigate.to('#quickstart')).props('color=indigo-300 text-color=black')
                ui.button('View on GitHub', on_click=lambda: ui.navigate.to('https://github.com/evnchn-nicegui/nicegui-diagnostics')).props('flat color=white')

    # --- Main content ---
    with ui.column().classes('w-full max-w-6xl mx-auto px-8 py-12 gap-12'):

        # --- Live metrics dashboard ---
        ui.label('Live Dashboard').classes('section-title text-white')
        ui.label('This app is instrumented by nicegui-diagnostics. These metrics are live.').classes('text-gray-400 mb-6')

        metrics_row = ui.row().classes('w-full gap-4')
        
        def update_metrics():
            metrics_row.clear()
            with metrics_row:
                snap = nicegui_diagnostics.collect_snapshot()
                
                # Tasks card
                with ui.element('div').classes('metric-card flex-1'):
                    tasks = snap.get('asyncio_tasks', {})
                    ui.label(tasks.get('total', 0)).classes('stat-value text-indigo-400')
                    ui.label('Async Tasks').classes('stat-label text-gray-400 mt-2')
                
                # Memory card
                with ui.element('div').classes('metric-card flex-1'):
                    mem = snap.get('memory', {})
                    rss_mb = (mem.get('current_rss_bytes') or mem.get('peak_rss_bytes', 0)) / (1024 * 1024)
                    ui.label(f'{rss_mb:.0f}').classes('stat-value text-emerald-400')
                    ui.label('MB RSS').classes('stat-label text-gray-400 mt-2')
                
                # Clients card
                with ui.element('div').classes('metric-card flex-1'):
                    clients = snap.get('clients', {})
                    ui.label(clients.get('total', 0)).classes('stat-value text-amber-400')
                    ui.label('Connected Clients').classes('stat-label text-gray-400 mt-2')
                
                # Event loop lag card
                with ui.element('div').classes('metric-card flex-1'):
                    lag = snap.get('event_loop_lag_ms', 0)
                    ui.label(f'{lag:.1f}').classes('stat-value text-rose-400')
                    ui.label('ms Loop Lag').classes('stat-label text-gray-400 mt-2')

        update_metrics()
        ui.timer(2.0, update_metrics)

        # --- Quick start ---
        ui.label('Quick Start').classes('section-title text-white').props('id=quickstart')
        with ui.element('div').classes('w-full'):
            ui.code('''from nicegui import ui
import nicegui_diagnostics

nicegui_diagnostics.install()

ui.label('Hello, diagnostics!')
ui.run()''', language='python').classes('w-full')

        with ui.row().classes('w-full gap-4 mt-4'):
            with ui.element('div').classes('probe-card flex-1'):
                ui.label('📊  11 Probes').classes('text-lg font-semibold text-white')
                ui.label('Tasks, memory, clients, config, loop lag, stack dumps, delta, lifecycle, eio, WS RTT, heartbeat').classes('text-sm text-gray-400 mt-1')
            with ui.element('div').classes('probe-card flex-1'):
                ui.label('🔌  HTTP Endpoint').classes('text-lg font-semibold text-white')
                ui.label('GET /_nicegui/diagnostics with auth gating').classes('text-sm text-gray-400 mt-1')
            with ui.element('div').classes('probe-card flex-1'):
                ui.label('🛡️  Graceful Restart').classes('text-lg font-semibold text-white')
                ui.label('Memory-threshold shutdown with exit code 75').classes('text-sm text-gray-400 mt-1')

        # --- Probes ---
        ui.label('Probes').classes('section-title text-white')
        
        with ui.grid().classes('w-full grid-cols-2 gap-4'):
            probes = [
                ('tasks', '📋', 'Asyncio task summary + oldest_age_s', 'Per-qualname counts. Wraps background_tasks.create() to stamp birth times.'),
                ('memory', '💾', 'Cross-platform RSS probe', 'Peak via getrusage (POSIX), current via /proc/self/status (Linux). Graceful on macOS.'),
                ('clients', '👥', 'Client counts + verbose detail', 'Total/connected counts. Verbose mode shows per-client element counts.'),
                ('config', '⚙️', 'Server config snapshot', 'async_handlers, transports, reconnect_timeout, binding_refresh_interval.'),
                ('event_loop_lag', '⏱️', 'Loop responsiveness', 'Schedules a no-op via call_soon, measures wall-clock overshoot.'),
                ('stack_dump', '🔍', 'Separate-thread HTTP server', 'Returns sys._current_frames() on GET /stacks. Works when loop is blocked.'),
                ('delta', '📈', 'Current-vs-previous diff', 'The "all deltas positive" pattern is the leak signal. Automates manual diffing.'),
                ('lifecycle', '🔄', 'Connect/disconnect counters', 'Monotonic counters reveal on_disconnect vs on_delete semantic surprises.'),
                ('eio', '🔌', 'Engine.io session counts', 'Reads core.sio.eio.sockets, compares against Client.instances for orphans.'),
                ('ws_rtt', '📡', 'WebSocket round-trip latency', 'Measures full round-trip: network + browser RAF + JSON serialization.'),
                ('heartbeat', '💓', 'Client-count with TTL purge', 'Catches tab-killed clients that on_disconnect misses.'),
            ]
            for name, icon, title, desc in probes:
                with ui.element('div').classes('probe-card'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label(icon).classes('text-2xl')
                        ui.label(title).classes('text-base font-semibold text-white')
                    ui.label(desc).classes('text-sm text-gray-400 mt-2')

        # --- API ---
        ui.label('API Endpoints').classes('section-title text-white')
        with ui.row().classes('w-full gap-4'):
            with ui.element('div').classes('probe-card flex-1'):
                ui.label('GET /_nicegui/diagnostics').classes('text-lg font-mono text-indigo-300')
                ui.label('Returns JSON snapshot. Add ?verbose=true for per-client detail, ?delta=true for diffs.').classes('text-sm text-gray-400 mt-2')
                ui.link('Try it →', '/_nicegui/diagnostics', new_tab=True).classes('text-indigo-400 mt-2')
            with ui.element('div').classes('probe-card flex-1'):
                ui.label('GET http://127.0.0.1:9999/stacks').classes('text-lg font-mono text-indigo-300')
                ui.label('Returns thread stacks. Works when the event loop is blocked.').classes('text-sm text-gray-400 mt-2')

        # --- Footer ---
        ui.separator().classes('my-8')
        ui.label('Built with nicegui-diagnostics — dogfooding in action').classes('text-center text-sm text-gray-500')


if __name__ in {'__main__', '__mp_main__'}:
    try:
        nicegui_diagnostics.install(
            features=['tasks', 'memory', 'clients', 'config', 'event_loop_lag', 'stack_dump', 'delta'],
            stack_dump_port=9999,
        )
    except RuntimeError:
        pass  # already installed (NiceGUI re-executes the script)
    main()
    ui.run(title='nicegui-diagnostics docs', port=8081, dark=True, reload=False)
