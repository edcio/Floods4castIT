

import io
import zipfile
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd

# gestioen anomalia su jupyterlab
if not hasattr(plt.rcParams, "_get"):
    plt.rcParams._get = plt.rcParams.get

#soglie solo per la stazione di Faenza
SOGLIE = {"soglia_0": 3.5, "soglia_1": 4.5, "soglia_2": 6.0}
COLORI = {"soglia_0": "#e8a33d", "soglia_1": "#d9622b", "soglia_2": "#c0392b"}
BLU = "#1a5490"



def _leggi_csv(contenuto, nome):
    """Elettura csv acquisiti da Dext3r"""
    try:
        testo = contenuto.decode("utf-8-sig", errors="replace")
    except Exception:
        return None, f"{nome}: impossibile decodificare"

    righe = testo.replace("\r\n", "\n").split("\n")

    i0 = next((i for i, r in enumerate(righe)
               if r.startswith("Inizio validità")), None)
    if i0 is None:
        return None, f"{nome}: intestazione non trovata"

    i1 = next((i for i in range(i0 + 1, len(righe))
               if righe[i].strip() == ""), len(righe))
    if i1 - i0 < 2:
        return None, f"{nome}: nessuna riga di dati"

    try:
        tab = pd.read_csv(io.StringIO("\n".join(righe[i0:i1])))
    except Exception as e:
        return None, f"{nome}: {type(e).__name__}"

    if tab.shape[1] < 3:
        return None, f"{nome}: attese 3 colonne, trovate {tab.shape[1]}"

    stazione = righe[2].strip() if len(righe) > 2 and righe[2].strip() else "?"

    out = pd.DataFrame({
        "stazione": stazione,
        "timestamp": pd.to_datetime(tab.iloc[:, 0], utc=True, errors="coerce"),
        "valore": pd.to_numeric(tab.iloc[:, 2], errors="coerce"),
        "file": nome,
    })
    return out, None


def carica(cartella):
    #Legge ricorsivamente tutti zip, che contengono csv, della cartella sorgente
    percorso = Path(cartella)
    if not percorso.exists():
        raise FileNotFoundError(f"cartella non trovata: {percorso.resolve()}")

    pezzi, problemi = [], []

    for f in sorted(percorso.rglob("*")):
        if f.suffix.lower() == ".csv":
            d, err = _leggi_csv(f.read_bytes(), f.name)
            (pezzi if d is not None else problemi).append(d if d is not None else err)
        elif f.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(f) as z:
                    for n in z.namelist():
                        if n.lower().endswith(".csv"):
                            d, err = _leggi_csv(z.read(n), f.name)
                            (pezzi if d is not None else problemi).append(
                                d if d is not None else err)
            except zipfile.BadZipFile:
                problemi.append(f"{f.name}: zip non leggibile")

    if not pezzi:
        raise ValueError(f"nessun file valido in {percorso.resolve()}")

    df = pd.concat(pezzi, ignore_index=True)
    scartati = df.timestamp.isna().sum()
    df = df.dropna(subset=["timestamp"]).reset_index(drop=True)

    print(f"file letti      {len(pezzi)}")
    print(f"righe           {len(df):,}")
    print(f"periodo         {df.timestamp.min():%Y-%m-%d} / {df.timestamp.max():%Y-%m-%d}")
    print(f"stazioni        {', '.join(df.stazione.unique())}")
    if scartati:
        print(f"righe scartate  {scartati:,} (timestamp non valido)")
    for p in problemi:
        print(f"  [!] {p}")
    return df


# campionamento

def _delta_validi(ts):
    #Differenze fra timestamp consecutivi, esclusi i duplicati
    d = ts.sort_values().diff().dropna()
    return d[d > pd.Timedelta(0)]


def passo_per_anno(df):
    #Passo di campionamento dominante, anno per anno
    g = df.sort_values("timestamp")
    d = g.timestamp.diff()
    t = pd.DataFrame({"anno": g.timestamp.dt.year, "delta": d}).dropna()
    t = t[t.delta > pd.Timedelta(0)]
    if t.empty:
        raise ValueError("impossibile calcolare il passo: meno di due timestamp")

    return t.groupby("anno").agg(
        passo=("delta", lambda x: x.mode().iloc[0]),
        quota_pct=("delta", lambda x: round((x == x.mode().iloc[0]).mean() * 100, 1)),
        n_intervalli=("delta", "size"),
    )


def trova_cambio(df):
    #ricava il giorno in cui cambia il passo di campionamento.
    #Restituisce il timestamp di taglio, oppure None se il passo e' costante.
    
    g = df.sort_values("timestamp")
    d = g.timestamp.diff()
    t = pd.DataFrame({"giorno": g.timestamp.dt.date, "delta": d}).dropna()
    t = t[t.delta > pd.Timedelta(0)]
    if t.empty:
        raise ValueError("dati insufficienti per determinare il passo")

    per_giorno = t.groupby("giorno").delta.agg(lambda x: x.mode().iloc[0])
    conteggi = per_giorno.value_counts()

    if len(conteggi) == 1:
        print(f"passo costante: {conteggi.index[0]}")
        return None

    vecchio, nuovo = conteggi.index[0], conteggi.index[1]
    if per_giorno.index[per_giorno == vecchio].min() > per_giorno.index[per_giorno == nuovo].min():
        vecchio, nuovo = nuovo, vecchio

    fine_vecchio = per_giorno.index[per_giorno == vecchio].max()
    inizio_nuovo = per_giorno.index[per_giorno == nuovo].min()
    taglio = pd.Timestamp(inizio_nuovo, tz="UTC")

    print(f"{vecchio}  fino al {fine_vecchio}")
    print(f"{nuovo}  dal {inizio_nuovo}")

    n_regimi = (per_giorno != per_giorno.shift()).sum() - 1
    if n_regimi > 1:
        print(f"[!] il passo cambia {n_regimi} volte: transizione non netta")
    return taglio


def separa(df, taglio):
    #Divide in due periodi. Ogni pezzo porta il proprio passo in .attrs."""
    if taglio is None:
        raise ValueError("taglio non definito: il passo e' costante, "
                         "non serve separare")

    prima = df[df.timestamp < taglio].sort_values("timestamp").reset_index(drop=True)
    dopo = df[df.timestamp >= taglio].sort_values("timestamp").reset_index(drop=True)

    for nome, p in [("prima", prima), ("dopo", dopo)]:
        if len(p) < 2:
            raise ValueError(f"periodo '{nome}' troppo corto ({len(p)} righe)")
        p.attrs["passo"] = _delta_validi(p.timestamp).mode().iloc[0]
        p.attrs["periodo"] = nome
        print(f"{nome:<6} {len(p):>9,} righe   "
              f"{p.timestamp.min():%Y-%m-%d} / {p.timestamp.max():%Y-%m-%d}   "
              f"passo {p.attrs['passo']}")
    return prima, dopo


#Cleaning

def prepara(pezzo, passo=None):
    #"""Rimuove i duplicati e riallinea su griglia temporale regolare.
    #Fra righe con lo stesso timestamp vince quella che ha un valore.
    #I mancanti restano NaN; la colonna `origine` distingue: osservato / vuoto_nel_file / assente_dal_file
    
    passo = passo or pezzo.attrs.get("passo")
    if passo is None:
        raise ValueError("passo non specificato e assente da .attrs")
    nome = pezzo.attrs.get("periodo", "serie")

    n0 = len(pezzo)
    dedup = (pezzo.assign(_pieno=pezzo.valore.notna())
                  .sort_values(["timestamp", "_pieno"], ascending=[True, False])
                  .drop_duplicates("timestamp")
                  .drop(columns="_pieno"))

    idx = pd.date_range(dedup.timestamp.min(), dedup.timestamp.max(),
                        freq=passo, tz="UTC")
    s = dedup.set_index("timestamp").reindex(idx)
    s["origine"] = "assente_dal_file"
    s.loc[idx.isin(dedup.timestamp), "origine"] = "vuoto_nel_file"
    s.loc[s.valore.notna(), "origine"] = "osservato"
    s["stazione"] = dedup.stazione.iloc[0]
    s.index.name = "timestamp"

    s = s.reset_index()[["stazione", "timestamp", "valore", "origine"]]
    s.attrs["passo"] = passo
    s.attrs["periodo"] = nome

    validi = s.valore.notna().sum()
    print(f"{nome:<6} duplicati rimossi {n0 - len(dedup):>5,}   "
          f"griglia {len(s):>9,} punti   "
          f"validi {validi:>9,} ({validi / len(s) * 100:5.2f}%)   "
          f"mancanti {len(s) - validi:>7,}")
    return s


def verifica(serie):
    #Controlla che la griglia sia regolare, continua e senza duplicati
    s = serie.sort_values("timestamp")
    passo = s.attrs.get("passo")
    if passo is None:
        raise ValueError("passo assente da .attrs")

    d = s.timestamp.diff().dropna()
    attesi = len(pd.date_range(s.timestamp.min(), s.timestamp.max(),
                               freq=passo, tz="UTC"))
    n_nan = int(s.valore.isna().sum())
    per_origine = s.origine.value_counts()
    dichiarati = int(per_origine.get("vuoto_nel_file", 0)
                     + per_origine.get("assente_dal_file", 0))

    controlli = {
        "salti diversi dal passo": int((d != passo).sum()),
        "timestamp duplicati": int(s.timestamp.duplicated().sum()),
        "punti saltati nella griglia": attesi - len(s),
        "NaN non dichiarati in origine": n_nan - dichiarati,
    }
    for k, v in controlli.items():
        print(f"{k:<32} {v:>8,}   {'ok' if v == 0 else '<-- DA CONTROLLARE'}")
    return controlli


def valori_anomali(serie, minimo, massimo):
    #Segnala le letture fuori dall'intervallo fisicamente plausibile (è un primo tentativo di valutazione qualità)
    v = serie.valore
    fuori = serie[v.notna() & ((v < minimo) | (v > massimo))]

    print(f"intervallo osservato   {v.min():.2f} / {v.max():.2f} m")
    print(f"intervallo plausibile  {minimo:.2f} / {massimo:.2f} m")
    print(f"valori fuori           {len(fuori):,} "
          f"({len(fuori) / v.notna().sum() * 100:.4f}% dei validi)")

    if len(fuori):
        r = (fuori.assign(giorno=fuori.timestamp.dt.date)
                  .groupby("giorno").valore.agg(n="size", minimo="min", massimo="max"))
        print()
        print(r.head(15).to_string())
        if len(r) > 15:
            print(f"... e altri {len(r) - 15} giorni")
    return fuori


def lacune(serie):
    #Una riga per ogni sequenza continua di valori mancanti
    s = serie.sort_values("timestamp").reset_index(drop=True)
    manca = s.valore.isna()
    if not manca.any():
        print("nessun valore mancante")
        return pd.DataFrame(columns=["inizio", "fine", "n_punti", "durata",
                                     "val_prima", "val_dopo", "salto"])

    out = []
    for _, seg in s[manca].groupby((manca != manca.shift()).cumsum()[manca]):
        i0, i1 = seg.index[0], seg.index[-1]
        i_pr = s.valore[:i0].last_valid_index()
        i_dp = s.valore[i1 + 1:].first_valid_index()
        out.append({
            "inizio": seg.timestamp.iloc[0],
            "fine": seg.timestamp.iloc[-1],
            "n_punti": len(seg),
            "durata": seg.timestamp.iloc[-1] - seg.timestamp.iloc[0],
            "val_prima": s.valore[i_pr] if i_pr is not None else pd.NA,
            "val_dopo": s.valore[i_dp] if i_dp is not None else pd.NA,
        })

    rep = pd.DataFrame(out).sort_values("inizio").reset_index(drop=True)
    rep["salto"] = pd.to_numeric(rep.val_dopo, errors="coerce") - \
                   pd.to_numeric(rep.val_prima, errors="coerce")

    fasce = pd.cut(rep.n_punti, [0, 1, 4, 24, 96, 10 ** 9],
                   labels=["1 punto", "2-4", "5-24", "25-96", "oltre 96"])
    print(f"sequenze mancanti  {len(rep):,}")
    print(f"punti mancanti     {rep.n_punti.sum():,}")
    print(f"sequenza piu' lunga {rep.durata.max()} ({rep.n_punti.max():,} punti)")
    print()
    print(fasce.value_counts().sort_index().rename("sequenze").to_string())
    return rep


#valutazione episodi intesi come eventi estesi nei quali si sonon verificati superamenti

def episodi(serie, soglie=SOGLIE, pausa="6h"):
    #"""Sequenze sopra la soglia minima, classificate sulla soglia piu' alta.
    #pausa: superamenti separati da meno di questo intervallo contano come un 
    #unico episodio, per non spezzare un'onda in molti frammenti.
    
    s = serie.dropna(subset=["valore"]).sort_values("timestamp")
    livelli = sorted(soglie.values())
    sopra = s[s.valore > livelli[0]]

    colonne = ["inizio", "fine", "durata", "picco", "n_campioni", "soglia_max"]
    if sopra.empty:
        print(f"nessun superamento di {livelli[0]} m")
        return pd.DataFrame(columns=colonne)

    gruppi = (sopra.timestamp.diff() > pd.Timedelta(pausa)).cumsum()
    ep = sopra.groupby(gruppi).agg(
        inizio=("timestamp", "min"), fine=("timestamp", "max"),
        picco=("valore", "max"), n_campioni=("valore", "size"))
    ep["durata"] = ep.fine - ep.inizio
    ep["soglia_max"] = pd.cut(ep.picco, livelli + [float("inf")],
                              labels=sorted(soglie, key=soglie.get),
                              right=False)
    return ep.reset_index(drop=True)[colonne]


def riepilogo_episodi(ep):
    #Conteggio degli episodi per soglia massima raggiunta
    if ep.empty:
        print("nessun episodio")
        return pd.DataFrame()

    t = (ep.groupby("soglia_max", observed=False)
           .agg(episodi=("picco", "size"), picco_max=("picco", "max"),
                durata_mediana=("durata", "median"),
                durata_max=("durata", "max")))
    t.insert(1, "quota_pct", (t.episodi / t.episodi.sum() * 100).round(1))
    print(t.to_string())
    print(f"\ntotale episodi: {len(ep)}")
    return t


def distribuzione(serie, soglie=SOGLIE):
    #Ripartizione dei campioni validi fra le fasce di soglia
    v = serie.valore.dropna()
    livelli = sorted(soglie.values())
    nomi = sorted(soglie, key=soglie.get)

    fasce = pd.cut(v, [float("-inf")] + livelli + [float("inf")],
                   labels=["sotto soglia"] + nomi, right=False)
    t = fasce.value_counts().sort_index().rename("campioni").to_frame()
    t["quota_pct"] = (t.campioni / t.campioni.sum() * 100).round(4)

    passo_ore = serie.attrs.get("passo", pd.Timedelta("15min")) / pd.Timedelta("1h")
    t["ore"] = (t.campioni * passo_ore).round(1)
    return t


#grafici

def _disegna_soglie(ax, soglie, limite=None):
    for nome, v in sorted(soglie.items(), key=lambda kv: kv[1]):
        if limite is not None and v > limite:
            continue
        ax.axhline(v, color=COLORI[nome], ls="--", lw=1.1, zorder=1)
        ax.annotate(f"{nome} = {v} m", xy=(1.004, v),
                    xycoords=("axes fraction", "data"),
                    color=COLORI[nome], fontsize=8, va="center",
                    annotation_clip=False)


def grafico_serie(serie, soglie=SOGLIE, titolo=None, limiti_y=None,
                  figsize=(11, 3.4)):
    #Serie completa. I valori mancanti interrompono la linea
    s = serie.sort_values("timestamp")
    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(s.timestamp, s.valore, lw=0.4, color=BLU, zorder=2)
    _disegna_soglie(ax, soglie)

    if limiti_y is not None:
        ax.set_ylim(*limiti_y)
        fuori = int(((s.valore < limiti_y[0]) | (s.valore > limiti_y[1])).sum())
        if fuori:
            ax.annotate(f"{fuori} valori fuori scala non mostrati",
                        xy=(0.005, 0.04), xycoords="axes fraction",
                        fontsize=7.5, color="#888")

    ax.set_ylabel("livello (m)")
    ax.set_title(titolo or f"{s.stazione.iloc[0]} - livello idrometrico, "
                           f"{s.timestamp.min():%Y}-{s.timestamp.max():%Y}",
                 loc="left", fontsize=11)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.margins(x=0.01)
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    return fig


def grafico_finestra(serie, inizio, fine, soglie=SOGLIE, titolo=None,
                     figsize=(11, 3.6)):
    #Zoom su una finestra temporale; le lacune sono evidenziate in rosso
    def _ts(x):
        t = pd.Timestamp(x)
        return t.tz_localize("UTC") if t.tz is None else t.tz_convert("UTC")

    s = serie[(serie.timestamp >= _ts(inizio)) &
              (serie.timestamp <= _ts(fine))].sort_values("timestamp")
    if s.empty:
        raise ValueError(f"nessun dato fra {inizio} e {fine}")

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(s.timestamp, s.valore, lw=1.3, color=BLU, zorder=2)

    manca = s.valore.isna()
    if manca.any():
        for _, seg in s[manca].groupby((manca != manca.shift()).cumsum()[manca]):
            ax.axvspan(seg.timestamp.iloc[0], seg.timestamp.iloc[-1],
                       color=COLORI["soglia_2"], alpha=0.10, zorder=0)

    if s.valore.notna().any():
        vmax = s.valore.max()
        # le soglie si disegnano solo se pertinenti alla scala della finestra
        _disegna_soglie(ax, soglie, limite=vmax * 1.3)
        # il colmo si annota solo se la finestra contiene una piena vera,
        # altrimenti l'etichetta invade il grafico senza aggiungere nulla
        if vmax > min(soglie.values()):
            i = s.valore.idxmax()
            ax.annotate(f"{s.valore[i]:.2f} m   {s.timestamp[i]:%d/%m %H:%M}",
                        xy=(s.timestamp[i], vmax), xytext=(0, 7),
                        textcoords="offset points", fontsize=8, ha="center")
            ax.set_ymargin(0.16)
    else:
        _disegna_soglie(ax, soglie)

    ax.set_ylabel("livello (m)")
    ax.set_title(titolo or f"{s.timestamp.min():%d %b %Y} - {s.timestamp.max():%d %b %Y}",
                 loc="left", fontsize=11)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
    ax.margins(x=0.01)
    ax.grid(alpha=0.25, lw=0.5)
    fig.tight_layout()
    return fig


def grafico_copertura(serie, soglia_pct=90, figsize=(11, 2.5)):
    #Percentuale di dati validi per mese, soglia base a 90%
    s = serie.copy()
    s["mese"] = s.timestamp.dt.tz_localize(None).dt.to_period("M").dt.to_timestamp()
    cop = s.groupby("mese").valore.apply(lambda x: x.notna().mean() * 100)

    fig, ax = plt.subplots(figsize=figsize)
    ax.bar(cop.index, cop.values, width=24,
           color=[COLORI["soglia_2"] if v < soglia_pct else BLU for v in cop.values])
    ax.axhline(soglia_pct, color="#888", ls=":", lw=1)

    ax.set_ylabel("dati validi (%)")
    ax.set_ylim(0, 102)
    ax.set_title(f"Copertura mensile - in rosso i mesi sotto il {soglia_pct}%",
                 loc="left", fontsize=11)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.margins(x=0.01)
    ax.grid(alpha=0.25, lw=0.5, axis="y")
    fig.tight_layout()
    return fig


#Data Quality

def variazioni_brusche(serie, limite_m):
    #Variazioni fra campioni consecutivi superiori a `limite_m` metri
    #valutazioni poteniali spike strumentali per delta importanti tra sequenze di acquisizioni: 
    
    s = serie.sort_values("timestamp").reset_index(drop=True)
    d = s.valore.diff().abs()
    idx = d[d > limite_m].index

    if len(idx) == 0:
        print(f"nessuna variazione superiore a {limite_m} m fra campioni consecutivi")
        return pd.DataFrame()

    out = pd.DataFrame({
        "timestamp": s.timestamp[idx],
        "valore_prec": s.valore[idx - 1].values,
        "valore": s.valore[idx].values,
        "variazione": d[idx].values,
        # il campione precedente era l'ultimo prima di una lacuna?
        "dopo_lacuna": s.valore[idx - 1].isna().values | (idx.to_series().diff() != 1).values,
    }).reset_index(drop=True)

    print(f"variazioni oltre {limite_m} m fra campioni consecutivi: {len(out)}")
    return out


def spike_isolati(serie, limite_m):
    #Campioni che si discostano di oltre `limite_m` sia dal precedente sia
    #dal successivo, nella stessa direzione: valutazione eventuali errori di lettura
    s = serie.sort_values("timestamp").reset_index(drop=True)
    # confronto con l'ultimo valore valido, non con il campione adiacente:
    prec = s.valore.ffill().shift(1)
    succ = s.valore.bfill().shift(-1)
    salita, discesa = s.valore - prec, s.valore - succ

    mask = ((salita > limite_m) & (discesa > limite_m)) | \
           ((salita < -limite_m) & (discesa < -limite_m))
    sp = s[mask].copy()
    sp["valore_prec"] = prec[mask].values
    sp["valore_succ"] = succ[mask].values

    print(f"spike isolati (scostamento > {limite_m} m da entrambi i vicini): {len(sp)}")
    if len(sp):
        sopra = (sp.valore > min(SOGLIE.values())).sum()
        print(f"di cui sopra la soglia minima: {sopra}  "
              f"(genererebbero falsi superamenti)")
    return sp[["timestamp", "valore_prec", "valore", "valore_succ", "origine"]]


def episodi_sospetti(ep, min_campioni=4):
    #intercettare episodi con numero campioni sopra soglia troppo brevi per essere potenzialmente delle piene
    if ep.empty:
        return ep
    brevi = ep[ep.n_campioni < min_campioni]
    print(f"episodi con meno di {min_campioni} campioni: {len(brevi)} su {len(ep)}")
    if len(brevi):
        per_soglia = brevi.soglia_max.value_counts().sort_index()
        print(per_soglia.rename("episodi brevi").to_string())
    return brevi
