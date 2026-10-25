"""Оптимизация Dota 2.

1. Моды-оптимизации как в Minify: файлы игры из списков blacklist.txt подменяются
   «пустышками» (blank.vpcf_c и т.д.) прямо в собираемом VPK. Списки и пустышки
   берутся из репозитория Minify (GPL-3.0) и кэшируются в data/cache/minify.
2. Параметры запуска: полезные флаги, которые DotaCat прописывает в Steam.
3. Графика: настройки из userdata/<аккаунт>/570/local/cfg/video.txt и лимиты FPS
   из machine_convars.vcfg — меняются при закрытой игре, с резервной копией.
"""

import os
import re
import shutil
import time

from . import net, paths, steam, vdf
from .store import config

MINIFY_RAW = "https://raw.githubusercontent.com/Egezenn/dota2-minify/main/Minify/"
MINIFY_URL = "https://github.com/Egezenn/dota2-minify"
CACHE_DIR = os.path.join(paths.CACHE_DIR, "minify")
LIST_MAX_AGE = 7 * 86400
BLANK_MAX_AGE = 30 * 86400
BLANK_EXTENSIONS = tuple(f".{ext}" for ext in ("vcss_c", "vjs_c", "vmat_c", "vmdl_c", "vpcf_c", "vsnd_c", "vtex_c", "vxml_c", "txt"))

GROUPS = {
    "hud": "Интерфейс игры",
    "fps": "Больше FPS",
    "clean": "Чище экран",
    "sound": "Звук (на FPS не влияет)",
}

# Моды Minify, сделанные только списками blacklist.txt или готовыми файлами (files/) —
# их можно собрать без инструментов Valve.
TWEAKS = [
    {"id": "networth", "mod": "Show NetWorth", "group": "hud", "impact": 0, "kind": "files",
     "files": ["panorama/layout/hud/dota_hud_quick_stats.vxml_c"],
     "name": "Показывать нетворс",
     "desc": "Ваш текущий нетворс (золото + стоимость предметов) появляется в панели быстрой статистики "
             "слева вверху, рядом с убийствами и смертями. Данные — только ваши, как в обычном интерфейсе.",
     "warn": "Если HUD-мод из каталога меняет ту же панель, остаётся вариант HUD-мода."},
    {"id": "spells", "mod": "Minify Spells & Items", "group": "fps", "impact": 3,
     "name": "Упрощённые способности и предметы",
     "desc": "Убирает лишние частицы у стандартных заклинаний и предметов. Сильнее всего поднимает FPS в драках."},
    {"id": "base_attacks", "mod": "Minify Base Attacks", "group": "fps", "impact": 2,
     "name": "Упрощённые атаки",
     "desc": "Меньше частиц у снарядов автоатак героев дальнего боя."},
    {"id": "misc", "mod": "Misc Optimization", "group": "fps", "impact": 2,
     "name": "Прочие эффекты",
     "desc": "Убирает свечение фонтана и зданий, эффекты снарядов и разрушения башен, частицы статуй, упрощает иллюзии.",
     "settings": [
         {"key": "disable_courier_particles", "label": "Убрать эффекты курьеров", "default": True},
         {"key": "disable_event_particles", "label": "Убрать эффекты ивентов", "default": False},
     ]},
    {"id": "weather", "mod": "Remove Weather Effects", "group": "fps", "impact": 1,
     "name": "Без погодных эффектов",
     "desc": "Убирает дождь, снег и другую погоду (от предметов погоды и команды cl_weather)."},
    {"id": "foliage", "mod": "Remove Foliage", "group": "fps", "impact": 1,
     "name": "Без кустов и травы",
     "desc": "Убирает кусты, цветы, камни и прочие декорации — на земле остаются только плитки.",
     "warn": "Нужна стандартная карта: не включайте вместе с модами ландшафта."},
    {"id": "sprays", "mod": "Remove Sprays", "group": "clean", "impact": 0,
     "name": "Без спреев", "desc": "Не показывает спреи и не проигрывает их звук."},
    {"id": "pings", "mod": "Remove Pings", "group": "clean", "impact": 0,
     "name": "Без пингов", "desc": "Убирает звуки и частицы пингов.",
     "warn": "Вы перестанете замечать пинги союзников.",
     "settings": [{"key": "disable_ping_particles", "label": "Убирать и частицы, не только звук", "default": True}]},
    {"id": "ambient", "mod": "Mute Ambient Sounds", "group": "sound", "impact": 0,
     "name": "Без звуков окружения", "desc": "Выключает птиц, летучих мышей, шум реки и прочий фон карты."},
    {"id": "taunts", "mod": "Mute Taunt Sounds", "group": "sound", "impact": 0,
     "name": "Без звуков насмешек", "desc": "Выключает звуки насмешек (taunt)."},
    {"id": "voice", "mod": "Mute Voice Line Sounds", "group": "sound", "impact": 0,
     "name": "Без реплик героев", "desc": "Выключает голосовые реплики героев.",
     "settings": [{"key": "disable_all_hero_lines", "label": "Вообще все реплики героев", "default": False}]},
    {"id": "announcer", "mod": "Mute Default Announcer", "group": "sound", "impact": 0,
     "name": "Без стандартного комментатора", "desc": "Глушит стандартного комментатора (свой из каталога продолжит работать)."},
    {"id": "killstreak", "mod": "Mute Default Kill Spree Sounds", "group": "sound", "impact": 0,
     "name": "Без звуков серий убийств", "desc": "Глушит стандартные реплики серий убийств."},
]
TWEAKS_BY_ID = {t["id"]: t for t in TWEAKS}

# --- параметры запуска ---

LAUNCH_OPTIONS = [
    {"id": "novid", "tokens": ["-novid"], "rating": "good", "default": True,
     "name": "Без заставки", "desc": "Пропускает вступительный ролик — игра открывается быстрее. На FPS не влияет."},
    {"id": "no_menu_bg", "tokens": ["+map_enable_background_maps", "0"], "rating": "good", "default": True,
     "name": "Без 3D-сцены в главном меню",
     "desc": "Отключает анимированный фон меню: он нагружает видеокарту даже во время поиска игры."},
    {"id": "nojoy", "tokens": ["-nojoy"], "rating": "ok", "default": False,
     "name": "Без поддержки геймпада", "desc": "Не загружает поддержку джойстика — чуть меньше памяти. Не включайте, если играете с геймпадом."},
    {"id": "high", "tokens": ["-high"], "rating": "maybe", "default": False,
     "name": "Высокий приоритет процесса",
     "desc": "Windows отдаёт Dota больше процессорного времени. Иногда помогает на слабых CPU, но может мешать стриму и Discord."},
    {"id": "map", "tokens": ["-map", "dota"], "rating": "maybe", "default": False,
     "name": "Предзагрузка карты", "desc": "Грузит карту при запуске: первая игра открывается быстрее, но сам запуск дольше. FPS не меняет."},
    {"id": "console", "tokens": ["-console"], "rating": "ok", "default": False,
     "name": "Консоль разработчика", "desc": "Включает консоль (клавиша назначается в настройках управления)."},
]
RENDERERS = [
    {"id": "", "name": "Как в настройках игры", "desc": "Обычно это DirectX 11."},
    {"id": "-dx11", "name": "DirectX 11", "desc": "Самый стабильный вариант на большинстве ПК."},
    {"id": "-vulkan", "name": "Vulkan",
     "desc": "На процессорах с 6+ ядрами часто даёт больше FPS и ровнее просадки. Если игра вылетает — верните DirectX 11."},
]
LAUNCH_MYTHS = [
    ["-threads N", "движок сам распределяет нагрузку по ядрам"],
    ["-heapsize, -processheap", "ручное управление памятью из старых гайдов, эффекта нет"],
    ["-dx9, -nod3d9ex", "DirectX 9 из Dota 2 удалён"],
    ["-noaafonts", "только отключает сглаживание шрифтов, FPS не меняет"],
    ["-prewarm, -nocrashdialog, -novr, -nohltv", "на производительность не влияют"],
    ["+r_rootlod, +mat_hdr_level, +r_waterforceexpensive", "переменные движка Source 1, в Dota 2 не работают"],
    ["+fps_max в параметрах запуска", "игра перезаписывает его своей настройкой — лимит FPS лучше задать в разделе «Графика»"],
]
_FLAG_TOKENS = {"-novid", "-nojoy", "-high", "-console", "-dx11", "-vulkan", "-gl"}
_PAIR_TOKENS = {"-language", "-map", "+map_enable_background_maps"}

# --- графика (video.txt) ---

GRAPHICS = [
    {"key": "mat_viewportscale", "type": "scale", "fps": None, "name": "Качество рендера",
     "desc": "Разрешение 3D-сцены. Даёт больше всего FPS: 80–90% почти незаметно на глаз."},
    {"key": "cl_globallight_shadow_mode", "type": "select", "fps": "0", "name": "Тени",
     "options": [["0", "Выкл / низкие"], ["1", "Средние"], ["2", "Высокие"], ["3", "Ультра"]]},
    {"key": "r_texture_stream_mip_bias", "type": "select", "fps": None, "name": "Текстуры",
     "options": [["0", "Высокие"], ["1", "Средние"], ["2", "Низкие"]],
     "desc": "Влияют в основном на видеопамять: на видеокартах с 4 ГБ и больше можно оставить средние."},
    {"key": "shaderquality", "type": "select", "fps": "0", "name": "Качество шейдеров",
     "options": [["0", "Низкое"], ["1", "Высокое"]]},
    {"key": "dota_cheap_water", "type": "bool", "fps": True, "name": "Упрощённая вода"},
    {"key": "r_ssao", "type": "bool", "fps": False, "name": "Ambient occlusion"},
    {"key": "r_deferred_height_fog", "type": "bool", "fps": False, "name": "Атмосферный туман"},
    {"key": "r_deferred_specular", "type": "bool", "fps": False, "name": "Блики"},
    {"key": "r_deferred_specular_bloom", "type": "bool", "fps": False, "name": "Свечение бликов"},
    {"key": "r_deferred_additive_pass", "type": "bool", "fps": False, "name": "Дополнительное освещение"},
    {"key": "r_dota_normal_maps", "type": "bool", "fps": False, "name": "Карты нормалей"},
    {"key": "r_dota_allow_parallax_mapping", "type": "bool", "fps": False, "name": "Параллакс"},
    {"key": "r_grass_quality", "type": "bool", "fps": False, "name": "Трава"},
    {"key": "r_dota_allow_wind_on_trees", "type": "bool", "fps": False, "name": "Ветер в деревьях"},
    {"key": "dota_ambient_creatures", "type": "bool", "fps": False, "name": "Живность на карте"},
    {"key": "dota_ambient_cloth", "type": "bool", "fps": False, "name": "Симуляция ткани"},
    {"key": "dota_portrait_animate", "type": "bool", "fps": False, "name": "Анимированный портрет"},
    {"key": "r_dashboard_render_quality", "type": "bool", "fps": False, "name": "Качественный фон меню"},
    {"key": "r_depth_of_field", "type": "bool", "fps": False, "name": "Глубина резкости"},
    {"key": "mat_vsync", "type": "bool", "fps": False, "name": "Вертикальная синхронизация",
     "desc": "Ограничивает FPS частотой монитора и добавляет задержку ввода."},
    {"key": "r_low_latency", "type": "select", "fps": "1", "name": "Низкая задержка (NVIDIA Reflex)",
     "options": [["0", "Выкл"], ["1", "Вкл"], ["2", "Вкл + Boost"]]},
    {"key": "r_dota_fxaa", "type": "bool", "fps": None, "name": "Сглаживание FXAA", "desc": "Почти не влияет на FPS — по вкусу."},
    {"key": "r_dota_bloom_compute_shader", "type": "bool", "fps": None, "name": "Compute-шейдеры"},
    {"key": "r_dota_fsr_upsample", "type": "bool", "fps": None, "name": "AMD FSR (при качестве рендера < 100%)"},
]
GRAPHICS_BY_KEY = {g["key"]: g for g in GRAPHICS}
GPU_VENDORS = {
    "4318": ("NVIDIA", "https://www.nvidia.com/Download/index.aspx"),
    "4098": ("AMD", "https://www.amd.com/en/support"),
    "32902": ("Intel", "https://www.intel.com/content/www/us/en/support/detect.html"),
}

# --- Windows и Steam ---

SYSTEM_TARGETS = {
    "gamemode": "ms-settings:gaming-gamemode",
    "graphics": "ms-settings:display-advancedgraphics",
    "power": "powercfg.cpl",
    "startup": "ms-settings:startupapps",
    "captures": "ms-settings:gaming-gamedvr",
}
SYSTEM_TIPS = [
    {"title": "Игровой режим Windows", "open": "gamemode",
     "desc": "Включите: Windows будет меньше отвлекать процессор фоновыми задачами."},
    {"title": "Планирование GPU и видеокарта для Dota", "open": "graphics",
     "desc": "Включите «Аппаратное планирование GPU». На ноутбуке добавьте dota2.exe и выберите «Высокая производительность», чтобы игра шла на дискретной видеокарте."},
    {"title": "Электропитание", "open": "power",
     "desc": "Схема «Высокая производительность» (или «Сбалансированная» на новых CPU). Ноутбук — только от сети."},
    {"title": "Автозагрузка", "open": "startup",
     "desc": "Отключите лишние программы: браузер, лаунчеры и мониторинг съедают процессор и память."},
    {"title": "Запись игр Xbox", "open": "captures",
     "desc": "Выключите фоновую запись — она постоянно нагружает видеокарту."},
    {"title": "Оверлеи Steam и Discord",
     "desc": "Steam → Dota 2 → Свойства → «Включить оверлей Steam» — выключите. В Discord: Настройки → Оверлей игры. Эти оверлеи часто вызывают фризы."},
    {"title": "Кэш шейдеров Steam",
     "desc": "Steam → Настройки → Загрузки → «Предварительное кэширование шейдеров» — включите, особенно для Vulkan: меньше подлагиваний в первые минуты."},
    {"title": "Драйвер видеокарты",
     "desc": "Ставьте драйвер с сайта производителя. В панели NVIDIA: «Режим управления электропитанием — максимальная производительность»."},
    {"title": "SSD и место на диске",
     "desc": "Dota на SSD грузится в разы быстрее. Оставьте 15–20 ГБ свободного места на диске с игрой."},
]


# --- моды-оптимизации ---

def _cached(rel, binary=False, max_age=LIST_MAX_AGE):
    """Файл из репозитория Minify с кэшем; без сети берётся сохранённая копия."""
    path = os.path.join(CACHE_DIR, *rel.split("/"))
    fresh = os.path.isfile(path) and time.time() - os.path.getmtime(path) < max_age
    if not fresh:
        try:
            net.download(MINIFY_RAW + net.quote(rel), path, timeout=60)
        except Exception:
            if not os.path.isfile(path):
                raise
    with open(path, "rb") as f:
        data = f.read()
    return data if binary else data.decode("utf-8", "replace")


def _condition(expr, settings):
    """#if:выражение из blacklist.txt: имя настройки, «!», «&&» и «||»."""
    def term(token):
        token = token.strip()
        negate = token.startswith("!")
        value = bool(settings.get(token.lstrip("!").strip()))
        return not value if negate else value

    return any(all(term(part) for part in group.split("&&")) for group in expr.split("||"))


def parse_blacklist(text, settings):
    exact, patterns, exclude_patterns, exclude_exact = set(), [], [], set()
    active = []
    for raw in text.splitlines():
        line = raw.strip()
        cond = re.match(r"#\s*if:(.+)$", line, re.IGNORECASE)
        if cond:
            active.append((active[-1] if active else True) and _condition(cond.group(1), settings))
            continue
        if re.match(r"#\s*endif\b", line, re.IGNORECASE):
            if active:
                active.pop()
            continue
        if (active and not active[-1]) or not line or line.startswith("#"):
            continue
        if line.startswith(">>"):
            patterns.append(line[2:] + "/")  # вся папка
        elif line.startswith("**"):
            patterns.append(line[2:])  # регулярное выражение
        elif line.startswith("*-"):
            exclude_patterns.append(line[2:])
        elif line.startswith("--"):
            exclude_exact.add(line[2:].lower())
        else:
            exact.add(line.lower())
    return exact, patterns, exclude_patterns, exclude_exact


def _any_regex(patterns):
    parts = []
    for pattern in patterns:
        try:
            re.compile(pattern)
            parts.append(f"(?:{pattern})")
        except re.error:
            parts.append(re.escape(pattern))
    return re.compile("|".join(parts))


def resolve_blacklist(parsed, game_paths):
    exact, patterns, exclude_patterns, exclude_exact = parsed
    result = {p for p in exact if p.endswith(BLANK_EXTENSIONS)}
    if patterns:
        regex = _any_regex(patterns)
        result.update(p for p in game_paths if p.endswith(BLANK_EXTENSIONS) and regex.search(p))
    if exclude_patterns:
        regex = _any_regex(exclude_patterns)
        result = {p for p in result if not regex.search(p)}
    return result - exclude_exact


def tweak_settings(tweak, saved):
    values = (saved or {}).get("settings") or {}
    return {s["key"]: bool(values.get(s["key"], s["default"])) for s in tweak.get("settings", [])}


def enabled_tweaks():
    saved = config.get("tweaks") or {}
    return [(t, tweak_settings(t, saved.get(t["id"]))) for t in TWEAKS if (saved.get(t["id"]) or {}).get("enabled")]


def signature():
    """Строка для проверки «есть ли неприменённые изменения»."""
    return [f"{t['id']}:{','.join(sorted(k for k, v in s.items() if v))}" for t, s in enabled_tweaks()]


_BLANKS = {}


def blank(ext):
    """Пустышка Minify нужного типа (blank.vpcf_c и т.д.) или None."""
    if ext not in _BLANKS:
        try:
            _BLANKS[ext] = _cached(f"bin/blank-files/blank.{ext}", binary=True, max_age=BLANK_MAX_AGE)
        except Exception:
            _BLANKS[ext] = None
    return _BLANKS[ext]


def add_blanks(sources, paths_to_blank, game_pak):
    """Кладёт пустышки на пути, которые ещё не заняты модами. Возвращает число добавленных."""
    added = 0
    for path in sorted(paths_to_blank):
        if path in sources:
            continue
        data = blank(path.rsplit(".", 1)[-1])
        if data is None:
            continue
        entry = game_pak.entries.get(path)
        sources[path] = (entry.path if entry else path, (lambda data=data: data))
        added += 1
    return added


def apply_tweaks(sources, game_pak):
    """Добавляет файлы оптимизаций в sources (только туда, где моды пользователя ничего не положили).

    Возвращает [(название, число файлов, ошибка)]."""
    report = []
    game_paths = list(game_pak.entries)
    for tweak, settings in enabled_tweaks():
        if tweak.get("kind") == "files":
            added, busy = 0, []
            for rel in tweak["files"]:
                if rel.lower() in sources:
                    busy.append(rel)
                    continue
                try:
                    data = _cached(f"mods/{tweak['mod']}/files/{rel}", binary=True)
                except Exception as e:
                    report.append((tweak["name"], 0, f"не удалось скачать файл Minify: {e}"))
                    break
                sources[rel.lower()] = (rel, (lambda data=data: data))
                added += 1
            else:
                report.append((tweak["name"], added, "файл уже занят модом выше — оставлен его вариант" if busy else None))
            continue
        try:
            text = _cached(f"mods/{tweak['mod']}/blacklist.txt")
        except Exception as e:
            report.append((tweak["name"], 0, f"не удалось скачать список Minify: {e}"))
            continue
        added = add_blanks(sources, resolve_blacklist(parse_blacklist(text, settings), game_paths), game_pak)
        report.append((tweak["name"], added, None))
    return report


def mod_blacklist(folder):
    """blacklist.txt внутри мода (моды Minify и сообщества) с настройками по умолчанию из manifest.json."""
    path = os.path.join(folder, "blacklist.txt")
    if not os.path.isfile(path):
        return None
    settings = {}
    try:
        import json

        with open(os.path.join(folder, "manifest.json"), encoding="utf-8") as f:
            for item in json.load(f).get("settings") or []:
                if isinstance(item, dict) and item.get("key"):
                    settings[item["key"]] = bool(item.get("default"))
    except (OSError, ValueError, AttributeError):
        pass
    with open(path, encoding="utf-8", errors="replace") as f:
        return parse_blacklist(f.read(), settings)


def tweaks_state():
    saved = config.get("tweaks") or {}
    result = []
    for tweak in TWEAKS:
        entry = saved.get(tweak["id"]) or {}
        values = tweak_settings(tweak, entry)
        result.append({
            **{k: v for k, v in tweak.items() if k != "settings"},
            "enabled": bool(entry.get("enabled")),
            "settings": [{**s, "value": values[s["key"]]} for s in tweak.get("settings", [])],
        })
    return result


def set_tweak(tweak_id, enabled=None, settings=None):
    tweak = TWEAKS_BY_ID.get(tweak_id)
    if not tweak:
        raise KeyError(tweak_id)
    saved = config.get("tweaks") or {}
    entry = dict(saved.get(tweak_id) or {})
    if enabled is not None:
        entry["enabled"] = bool(enabled)
    if settings:
        known = {s["key"] for s in tweak.get("settings", [])}
        entry["settings"] = {**(entry.get("settings") or {}), **{k: bool(v) for k, v in settings.items() if k in known}}
    saved[tweak_id] = entry
    config.set("tweaks", saved)


def prefetch(ctx):
    """Скачивает списки включённых оптимизаций заранее (чтобы «Применить» не ждало сеть)."""
    for tweak, _ in enabled_tweaks():
        try:
            if tweak.get("kind") == "files":
                for rel in tweak["files"]:
                    _cached(f"mods/{tweak['mod']}/files/{rel}", binary=True)
            else:
                _cached(f"mods/{tweak['mod']}/blacklist.txt")
        except Exception as e:
            ctx.log(f"Оптимизация «{tweak['name']}»: не удалось скачать список Minify ({e})", "warn")


# --- параметры запуска ---

def _has_tokens(current, tokens):
    words = (current or "").split()
    return any(words[i:i + len(tokens)] == tokens for i in range(len(words)))


def launch_choices(current=None):
    """Выбранные параметры. Пока пользователь ничего не выбирал — берём то, что уже стоит в Steam."""
    saved = config.get("launch_opts") or {}
    choices = {}
    for option in LAUNCH_OPTIONS:
        if option["id"] in saved:
            choices[option["id"]] = bool(saved[option["id"]])
        else:
            choices[option["id"]] = option["default"] or _has_tokens(current, option["tokens"])
    if "renderer" in saved:
        renderer = saved["renderer"]
    else:
        renderer = next((r["id"] for r in RENDERERS if r["id"] and _has_tokens(current, [r["id"]])), "")
    choices["renderer"] = renderer if renderer in {r["id"] for r in RENDERERS} else ""
    return choices


def desired_tokens(language, current=None):
    choices = launch_choices(current)
    tokens = ["-language", language]
    for option in LAUNCH_OPTIONS:
        if choices[option["id"]]:
            tokens += option["tokens"]
    if choices["renderer"]:
        tokens.append(choices["renderer"])
    return tokens


def merge_launch_options(current, desired):
    """Убирает из строки всё, чем управляет DotaCat, и вставляет нужное (после %command%, если есть)."""
    tokens = (current or "").split()
    kept, i = [], 0
    while i < len(tokens):
        token = tokens[i]
        if token in _FLAG_TOKENS:
            i += 1
        elif token in _PAIR_TOKENS:
            has_value = i + 1 < len(tokens) and not tokens[i + 1].startswith(("-", "+", "%"))
            i += 2 if has_value else 1
        else:
            kept.append(token)
            i += 1
    if "%command%" in kept:
        pos = kept.index("%command%") + 1
        kept[pos:pos] = desired
    else:
        kept = list(desired) + kept
    return " ".join(kept)


def set_launch_choices(values, current=None):
    saved = {**launch_choices(current), **(config.get("launch_opts") or {})}
    for option in LAUNCH_OPTIONS:
        if option["id"] in values:
            saved[option["id"]] = bool(values[option["id"]])
    if values.get("renderer") in {r["id"] for r in RENDERERS}:
        saved["renderer"] = values["renderer"]
    config.set("launch_opts", saved)


# --- графика ---

def _cfg_dir():
    root, account = config.get("steam_root"), config.get("steam_account")
    if not (root and account):
        return None
    return os.path.join(root, "userdata", str(account), "570", "local", "cfg")


def _read(path):
    with open(path, "r", encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read()


def _write(path, text):
    with open(path, "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(text)


def _is_true(raw):
    return str(raw).strip().lower() in ("1", "true")


def _encode(definition, value, current):
    kind = definition["type"]
    if kind == "bool":
        on = bool(value) if isinstance(value, bool) else _is_true(value)
        if str(current).lower() in ("true", "false"):
            return "true" if on else "false"
        return "1" if on else "0"
    if kind == "select":
        value = str(value)
        if value not in {opt[0] for opt in definition["options"]}:
            raise ValueError(f"{definition['name']}: недопустимое значение {value}")
        return value
    scale = min(1.0, max(0.3, float(value)))
    return f"{scale:.6f}".rstrip("0").rstrip(".")


def _backup_dir():
    return os.path.join(paths.BACKUP_DIR, "graphics", str(config.get("steam_account")))


def read_graphics():
    folder = _cfg_dir()
    if not folder:
        return {"available": False, "reason": "Выберите аккаунт Steam в Настройках."}
    video_path = os.path.join(folder, "video.txt")
    if not os.path.isfile(video_path):
        return {"available": False, "reason": "С этого аккаунта Dota 2 ещё не запускалась — файла video.txt нет."}
    video = vdf.get(vdf.parse(_read(video_path)), "video.cfg") or {}
    values = {k[len("setting."):]: v for k, v in video.items() if k.startswith("setting.")}
    items = []
    for definition in GRAPHICS:
        if definition["key"] in values:
            raw = values[definition["key"]]
            value = _is_true(raw) if definition["type"] == "bool" else (float(raw) if definition["type"] == "scale" else str(raw))
            items.append({**definition, "value": value})
    convars = {}
    convars_path = os.path.join(folder, "machine_convars.vcfg")
    if os.path.isfile(convars_path):
        convars = vdf.get(vdf.parse(_read(convars_path)), "config", "convars") or {}
    vendor = GPU_VENDORS.get(str(video.get("VendorID", "")))

    def number(key):
        try:
            return round(float(convars.get(key)))
        except (TypeError, ValueError):
            return None

    return {
        "available": True,
        "items": items,
        "fps_max": number("fps_max"),
        "fps_max_ui": number("fps_max_ui"),
        "has_convars": bool(convars),
        "gpu": {"vendor": vendor[0], "driver_url": vendor[1]} if vendor else None,
        "resolution": f"{values.get('defaultres', '?')}×{values.get('defaultresheight', '?')}",
        "refresh": values.get("refreshrate_numerator"),
        "has_backup": os.path.isdir(_backup_dir()),
    }


def _backup_original(path, name):
    folder = _backup_dir()
    os.makedirs(folder, exist_ok=True)
    original = os.path.join(folder, f"{name}.original")
    if not os.path.exists(original):
        shutil.copy2(path, original)
    shutil.copy2(path, os.path.join(folder, f"{name}.last"))


def write_graphics(ctx, changes, fps_max=None, fps_max_ui=None):
    if steam.dota_running():
        raise RuntimeError("Закройте Dota 2: при выходе она перезапишет настройки графики.")
    folder = _cfg_dir()
    video_path = os.path.join(folder or "", "video.txt")
    if not folder or not os.path.isfile(video_path):
        raise RuntimeError("Не найден video.txt — выберите аккаунт Steam, с которого запускали Dota 2.")
    text = _read(video_path)
    current = {k[len("setting."):]: v for k, v in (vdf.get(vdf.parse(text), "video.cfg") or {}).items() if k.startswith("setting.")}
    changed = 0
    for key, value in (changes or {}).items():
        definition = GRAPHICS_BY_KEY.get(key)
        if not definition or key not in current:
            continue
        raw = _encode(definition, value, current[key])
        if raw != current[key]:
            text = vdf.set_value(text, ("video.cfg",), f"setting.{key}", raw)
            changed += 1
    if changed:
        _backup_original(video_path, "video.txt")
        _write(video_path, text)

    convars_path = os.path.join(folder, "machine_convars.vcfg")
    fps_changes = {k: v for k, v in (("fps_max", fps_max), ("fps_max_ui", fps_max_ui)) if v is not None}
    if fps_changes and os.path.isfile(convars_path):
        conv_text = _read(convars_path)
        for key, value in fps_changes.items():
            conv_text = vdf.set_value(conv_text, ("config", "convars"), key, str(max(0, min(1000, int(value)))))
        _backup_original(convars_path, "machine_convars.vcfg")
        _write(convars_path, conv_text)
        changed += len(fps_changes)
    ctx.log(f"Настройки графики сохранены (изменено: {changed}). Запустите Dota 2, чтобы проверить." if changed
            else "Настройки графики уже такие", "done")


def restore_graphics(ctx):
    if steam.dota_running():
        raise RuntimeError("Закройте Dota 2 перед восстановлением настроек.")
    folder, backup = _cfg_dir(), _backup_dir()
    restored = 0
    for name in ("video.txt", "machine_convars.vcfg"):
        original = os.path.join(backup, f"{name}.original")
        if folder and os.path.isfile(original):
            shutil.copy2(original, os.path.join(folder, name))
            restored += 1
    if not restored:
        raise RuntimeError("Резервной копии нет — DotaCat ещё не менял настройки графики этого аккаунта.")
    shutil.rmtree(backup, ignore_errors=True)
    ctx.log("Настройки графики возвращены к тем, что были до DotaCat", "done")


def open_system(target):
    uri = SYSTEM_TARGETS.get(target)
    if not uri:
        raise KeyError(target)
    os.startfile(uri)


def overview(current_launch=None):
    return {
        "groups": GROUPS,
        "tweaks": tweaks_state(),
        "launch": {"options": LAUNCH_OPTIONS, "renderers": RENDERERS, "choices": launch_choices(current_launch),
                   "myths": LAUNCH_MYTHS},
        "graphics": read_graphics(),
        "tips": SYSTEM_TIPS,
        "minify": MINIFY_URL,
    }
